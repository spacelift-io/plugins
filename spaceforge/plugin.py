"""
Base plugin class for Spaceforge framework.
"""

import inspect
import json
import logging
import os
import subprocess
import urllib.request
from abc import ABC
from typing import Any, Dict, List, Optional, Tuple, Union


class SpaceforgePlugin(ABC):
    """
    Base class for Spacelift plugins.

    Inherit from this class and implement hook methods like:
    - after_plan()
    - before_apply()
    - after_apply()
    - before_init()
    - after_init()
    - before_perform()
    - after_perform()
    """

    __plugin_name__ = "SpaceforgePlugin"
    __version__ = "1.0.0"
    __author__ = "Spacelift Team"

    def __init__(self) -> None:
        self.logger = self._setup_logger()

        self._api_token = os.environ.get("SPACELIFT_API_TOKEN", False)
        self._spacelift_domain = os.environ.get(
            "TF_VAR_spacelift_graphql_endpoint", False
        )
        self._api_enabled = self._api_token != False and self._spacelift_domain != False
        self._workspace_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())

        # This should be the last thing we do in the constructor
        # because we set api_enabled to false if the domain is set up incorrectly.
        if self._spacelift_domain and isinstance(self._spacelift_domain, str):
            # this must occur after we check if spacelift domain is false
            # because the domain could be set but not start with https://
            if self._spacelift_domain.startswith("https://"):
                if self._spacelift_domain.endswith("/"):
                    self._spacelift_domain = self._spacelift_domain[:-1]
            else:
                self.logger.warning(
                    "SPACELIFT_DOMAIN does not start with https://, api calls will fail."
                )
                self._api_enabled = False

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the plugin."""

        info_color = "\033[36m"
        debug_color = "\033[35m"
        warn_color = "\033[33m"
        error_color = "\033[31m"
        end_color = "\033[0m"
        run_id = os.environ.get("TF_VAR_spacelift_run_id", "local")
        plugin_name = self.__plugin_name__

        class ColorFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                message = super().format(record)
                if record.levelname == "INFO":
                    return (
                        f"{info_color}[{run_id}]{end_color} ({plugin_name}) {message}"
                    )
                elif record.levelname == "DEBUG":
                    return (
                        f"{debug_color}[{run_id}]{end_color} ({plugin_name}) {message}"
                    )
                elif record.levelname == "WARNING":
                    return (
                        f"{warn_color}[{run_id}]{end_color} ({plugin_name}) {message}"
                    )
                elif record.levelname == "ERROR":
                    return (
                        f"{error_color}[{run_id}]{end_color} ({plugin_name}) {message}"
                    )
                return message

        logger = logging.getLogger(f"spaceforge.{self.__class__.__name__}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            logger.addHandler(handler)
            handler.setFormatter(ColorFormatter())

        # Always check for debug mode spacelift variable
        if os.environ.get("SPACELIFT_DEBUG"):
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        return logger

    def get_available_hooks(self) -> List[str]:
        """
        Get list of hook methods available in this plugin.

        Returns:
            List of hook method names that are implemented
        """
        hook_methods = []
        for method_name in dir(self):
            if not method_name.startswith("_") and method_name != "get_available_hooks":
                method = getattr(self, method_name)
                if callable(method) and not inspect.isbuiltin(method):
                    # Check if it's a hook method (not inherited from base class)
                    if method_name in [
                        "before_init",
                        "after_init",
                        "before_plan",
                        "after_plan",
                        "before_apply",
                        "after_apply",
                        "before_perform",
                        "after_perform",
                        "before_destroy",
                        "after_destroy",
                        "after_run",
                    ]:
                        hook_methods.append(method_name)
        return hook_methods

    def run_cli(
        self, *command: str, expect_code: int = 0, print_output: bool = True
    ) -> Tuple[int, List[str], List[str]]:
        """
        Run a CLI command with the given arguments.

        Args:
            command: The command to run
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command
            expect_code: Expected return code
            print_output: Whether to print the output to the logger
        """
        self.logger.debug(f"Running CLI command: {' '.join(map(str, command))}")

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        stdout, stderr = process.communicate()

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        if stdout is not None:
            stdout_lines = stdout.decode("utf-8").splitlines()
        if stderr is not None:
            stderr_lines = stderr.decode("utf-8").splitlines()

        if process.returncode != expect_code:
            self.logger.error(f"Command failed with return code {process.returncode}")
            if print_output:
                for line in stdout_lines:
                    self.logger.info(line)
                for err in stderr_lines:
                    self.logger.error(err)
        else:
            if print_output:
                for line in stdout_lines:
                    self.logger.info(line)

        return process.returncode, stdout_lines, stderr_lines

    def query_api(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self._api_enabled:
            self.logger.error(
                'API is not enabled, please export "SPACELIFT_API_TOKEN" and "SPACELIFT_DOMAIN".'
            )
            exit(1)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_token}",
        }

        data: Dict[str, Any] = {
            "query": query,
        }

        if variables is not None:
            data["variables"] = variables

        req = urllib.request.Request(
            f"{self._spacelift_domain}/graphql",
            json.dumps(data).encode("utf-8"),
            headers,
        )
        with urllib.request.urlopen(req) as response:
            resp: Dict[str, Any] = json.loads(response.read().decode("utf-8"))

        if "errors" in resp:
            self.logger.error(f"Error: {resp['errors']}")
            return resp
        else:
            return resp

    def get_plan_json(self) -> Optional[Dict[str, Any]]:
        plan_json = f"{self._workspace_root}/spacelift.plan.json"
        if not os.path.exists(plan_json):
            self.logger.error("spacelift.plan.json does not exist.")
            return None

        with open(plan_json) as f:
            data: Dict[str, Any] = json.load(f)
            return data

    def get_state_before_json(self) -> Optional[Dict[str, Any]]:
        plan_json = f"{self._workspace_root}/spacelift.state.before.json"
        if not os.path.exists(plan_json):
            self.logger.error("spacelift.state.before.json does not exist.")
            return None

        with open(plan_json) as f:
            data: Dict[str, Any] = json.load(f)
            return data

    def send_markdown(self, markdown: str) -> None:
        # TODO
        print(markdown)

    # Hook methods - override these in your plugin
    def before_init(self) -> None:
        """Override this method to run code before Terraform init."""
        pass

    def after_init(self) -> None:
        """Override this method to run code after Terraform init."""
        pass

    def before_plan(self) -> None:
        """Override this method to run code before Terraform plan."""
        pass

    def after_plan(self) -> None:
        """Override this method to run code after Terraform plan."""
        pass

    def before_apply(self) -> None:
        """Override this method to run code before Terraform apply."""
        pass

    def after_apply(self) -> None:
        """Override this method to run code after Terraform apply."""
        pass

    def before_perform(self) -> None:
        """Override this method to run code before the run performs."""
        pass

    def after_perform(self) -> None:
        """Override this method to run code after the run performs."""
        pass

    def before_destroy(self) -> None:
        """Override this method to run code before Terraform destroy."""
        pass

    def after_destroy(self) -> None:
        """Override this method to run code after Terraform destroy."""
        pass

    def after_run(self) -> None:
        """Override this method to run code after the run completes."""
        pass
