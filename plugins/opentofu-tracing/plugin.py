import os
import signal
import subprocess
import time
from typing import Optional

from spaceforge import Binary, Context, Parameter, SpaceforgePlugin, Variable


class OpenTofuTracingPlugin(SpaceforgePlugin):
    """
    # OpenTofu Tracing Plugin

    This plugin enables OpenTelemetry tracing for OpenTofu operations in Spacelift using Tracedown.

    ## Overview

    This plugin automatically runs Tracedown (a lightweight OpenTelemetry trace collector) to capture
    OpenTofu traces and generates markdown reports that are uploaded to Spacelift.

    ## How It Works

    1. Before the OpenTofu operation starts, the plugin launches Tracedown in the background
    2. OpenTofu sends traces to Tracedown during the operation
    3. After the operation completes, Tracedown generates a markdown report
    4. The report is automatically uploaded to Spacelift for viewing

    ## Usage

    1. Attach the plugin to your stack using labels
    2. The plugin automatically downloads and installs tracedown
    3. Optionally configure the output file path and tracedown options

    ## Parameters

    - **Output File**: Path where the markdown report will be generated (defaults to 'traces.md')
    - **Max Traces**: Maximum number of trace batches to store (defaults to 10000)
    - **Max Memory MB**: Memory limit in MB (defaults to 500)
    - **Summary Mode**: Enable summary mode for large traces (defaults to false)
    - **gRPC Port**: Port for gRPC endpoint (defaults to 4317)
    - **HTTP Port**: Port for HTTP endpoint (defaults to 4318)

    ## Learn More

    - OpenTofu tracing: https://opentofu.org/docs/internals/tracing/
    - Tracedown: https://github.com/spacelift-solutions/tracedown
    """

    # Plugin metadata
    __plugin_name__ = "OpenTofu Tracing"
    __labels__ = ["opentofu", "observability", "tracing"]
    __version__ = "2.0.1"
    __author__ = "Spacelift Team"

    __binaries__ = [
        Binary(
            name="tracedown",
            download_urls={
                "amd64": "https://github.com/spacelift-solutions/tracedown/releases/download/v0.0.3/tracedown_0.0.3_linux_x86_64.tar.gz",
                "arm64": "https://github.com/spacelift-solutions/tracedown/releases/download/v0.0.3/tracedown_0.0.3_linux_arm64.tar.gz",
            },
        )
    ]

    __parameters__ = [
        Parameter(
            name="Output File (str: traces.md)",
            id="output_file",
            description="Path where the markdown report will be generated",
            required=True,
            sensitive=False,
        ),
        Parameter(
            name="Max Traces (int: 10000)",
            id="max_traces",
            description="Maximum number of trace batches to store",
            required=True,
            sensitive=False,
        ),
        Parameter(
            name="Max Memory MB (int: 500)",
            id="max_memory_mb",
            description="Memory limit in MB",
            required=True,
            sensitive=False,
        ),
        Parameter(
            name="Summary Mode (bool: false)",
            id="summary_mode",
            description="Enable summary mode for large traces (set to 'true' to enable)",
            required=True,
            sensitive=False,
        ),
    ]

    __contexts__ = [
        Context(
            name_prefix="opentofu-tracing",
            description="OpenTofu Tracing Plugin - Configures OpenTelemetry tracing with Tracedown",
            env=[
                Variable(
                    key="OUTPUT_FILE",
                    value_from_parameter="output_file",
                    sensitive=False,
                ),
                Variable(
                    key="MAX_TRACES",
                    value_from_parameter="max_traces",
                    sensitive=False,
                ),
                Variable(
                    key="MAX_MEMORY_MB",
                    value_from_parameter="max_memory_mb",
                    sensitive=False,
                ),
                Variable(
                    key="SUMMARY_MODE",
                    value_from_parameter="summary_mode",
                    sensitive=False,
                ),
                Variable(
                    key="OTEL_EXPORTER_OTLP_ENDPOINT",
                    value="http://localhost:4317",
                    sensitive=False,
                ),
                Variable(
                    key="OTEL_EXPORTER_OTLP_INSECURE", value="true", sensitive=False
                ),
                Variable(key="OTEL_TRACES_EXPORTER", value="otlp", sensitive=False),
            ],
            hooks={
                "before_init": ["export OTEL_SERVICE_NAME='opentofu-init'"],
                "before_plan": ["export OTEL_SERVICE_NAME='opentofu-plan'"],
                "before_apply": ["export OTEL_SERVICE_NAME='opentofu-apply'"],
            },
        )
    ]

    def __init__(self) -> None:
        super().__init__()
        self._tracedown_process: Optional[subprocess.Popen] = None
        self._tracedown_binary = "tracedown"
        self._output_file = os.environ.get("OUTPUT_FILE", "traces.md")
        self._max_traces = os.environ.get("MAX_TRACES", "1000")
        self._max_memory_mb = os.environ.get("MAX_MEMORY_MB", "500")
        self._summary_mode = os.environ.get("SUMMARY_MODE", "false").lower() == "true"
        self._grpc_port = os.environ.get("GRPC_PORT", "4317")
        self._http_port = os.environ.get("HTTP_PORT", "4318")
        self._pid_file = "/mnt/workspace/plugins/opentofu-tracing/tracedown.pid"
        self._plugin_dir = "/mnt/workspace/plugins/opentofu-tracing"

    def _start_tracedown(self) -> bool:
        """
        Start the tracedown process in the background and save its PID to a file.

        Returns:
            bool: True if started successfully, False otherwise
        """
        # Check if tracedown is already running from a previous hook
        if os.path.exists(self._pid_file):
            try:
                with open(self._pid_file, "r") as f:
                    pid = int(f.read().strip())
                # Check if process is still running using signal 0 (doesn't actually send a signal)
                os.kill(pid, 0)
                self.logger.info(f"Tracedown is already running (PID: {pid})")
                return True
            except (OSError, ValueError):
                # Process is not running or PID file is corrupt, continue with startup
                self.logger.debug(
                    "Stale PID file found, will start new tracedown process"
                )
                os.remove(self._pid_file)

        try:
            # Ensure directory exists
            os.makedirs(self._plugin_dir, exist_ok=True)
            self.logger.debug(f"Created/verified plugin directory: {self._plugin_dir}")

            # Use the configured output file path
            output_file = os.path.join(self._plugin_dir, self._output_file)
            self.logger.debug(f"Tracedown will write to: {output_file}")

            # Build the command
            cmd = [
                self._tracedown_binary,
                "-grpc-port",
                self._grpc_port,
                "-http-port",
                self._http_port,
                "-max-traces",
                self._max_traces,
                "-max-memory-mb",
                self._max_memory_mb,
                "-output",
                output_file,
            ]

            if self._summary_mode:
                cmd.append("-summary")

            self.logger.debug(f"Starting tracedown: {' '.join(cmd)}")

            # Start tracedown in the background as a detached process
            # Using start_new_session=True to create a new process group
            # Redirect stdout/stderr to files for debugging
            stdout_file = os.path.join(self._plugin_dir, "tracedown.stdout")
            stderr_file = os.path.join(self._plugin_dir, "tracedown.stderr")

            with open(stdout_file, "w") as stdout_f, open(stderr_file, "w") as stderr_f:
                self._tracedown_process = subprocess.Popen(
                    cmd, stdout=stdout_f, stderr=stderr_f, start_new_session=True
                )

            pid = self._tracedown_process.pid

            # Check if it's still running
            if self._tracedown_process.poll() is not None:
                self.logger.error("Tracedown failed to start")
                # Read the output files
                if os.path.exists(stdout_file):
                    with open(stdout_file, "r") as f:
                        stdout_content = f.read()
                        if stdout_content:
                            self.logger.error(f"stdout: {stdout_content}")
                if os.path.exists(stderr_file):
                    with open(stderr_file, "r") as f:
                        stderr_content = f.read()
                        if stderr_content:
                            self.logger.error(f"stderr: {stderr_content}")
                return False

            # Log the startup output for debugging
            self.logger.debug(f"Tracedown stdout: {stdout_file}")
            self.logger.debug(f"Tracedown stderr: {stderr_file}")

            # Save PID to file for later use in after_run hook
            with open(self._pid_file, "w") as f:
                f.write(str(pid))

            self.logger.info(
                f"Tracedown started successfully (PID: {pid}, output: {output_file})"
            )
            self.logger.debug(f"PID saved to {self._pid_file}")
            return True

        except FileNotFoundError:
            self.logger.error(f"Tracedown binary not found: {self._tracedown_binary}")
            self.logger.error(
                "The plugin should have automatically installed tracedown. Please check if the binary installation hook ran successfully."
            )
            return False
        except Exception as e:
            self.logger.error(f"Failed to start tracedown: {e}")
            return False

    def _stop_tracedown(self) -> bool:
        """
        Stop the tracedown process by reading its PID from file and sending SIGTERM.

        Returns:
            bool: True if stopped successfully and markdown was generated, False otherwise
        """
        if not os.path.exists(self._pid_file):
            self.logger.warning(
                "Tracedown PID file not found - tracedown may not be running"
            )
            return False

        try:
            # Read PID from file
            with open(self._pid_file, "r") as f:
                pid = int(f.read().strip())

            self.logger.info(
                f"Stopping tracedown (PID: {pid}) and generating markdown report..."
            )

            # Check if process is still running using signal 0 (doesn't kill the process)
            try:
                os.kill(pid, 0)
            except OSError:
                self.logger.warning(f"Tracedown process {pid} is not running")
                # Clean up PID file
                os.remove(self._pid_file)
                return False

            # Send SIGTERM to gracefully shut down tracedown
            # This triggers markdown generation
            os.kill(pid, signal.SIGTERM)
            self.logger.debug(f"Sent SIGTERM to process {pid}")

            # Wait for process to finish (with timeout)
            max_wait = 30.0
            wait_interval = 0.5
            elapsed = 0.0

            while elapsed < max_wait:
                try:
                    # Check if process is still running
                    os.kill(pid, 0)
                    time.sleep(wait_interval)
                    elapsed += wait_interval
                except OSError:
                    # Process has exited
                    self.logger.info("Tracedown stopped successfully")
                    break
            else:
                # Timeout reached, force kill
                self.logger.error(
                    "Tracedown did not shut down gracefully, forcing termination"
                )
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
                return False

            # Give the file system a moment to flush/sync the markdown file
            # Tracedown writes the file on shutdown, so we need to wait for it to be fully written
            self.logger.debug("Waiting for markdown file to be written to disk...")
            time.sleep(3)

            # Check if tracedown logged any errors during shutdown
            stderr_file = os.path.join(self._plugin_dir, "tracedown.stderr")
            try:
                if os.path.exists(stderr_file) and os.path.getsize(stderr_file) > 0:
                    with open(stderr_file, "r") as f:
                        stderr_content = f.read()
                        if stderr_content.strip():
                            self.logger.warning(f"Tracedown stderr:")
                            self.logger.warning(stderr_content)
            except Exception as e:
                self.logger.debug(f"Could not check tracedown stderr: {e}")

            # Clean up PID file
            if os.path.exists(self._pid_file):
                os.remove(self._pid_file)
                self.logger.debug(f"Removed PID file {self._pid_file}")

            return True

        except ValueError:
            self.logger.error(f"Invalid PID in file {self._pid_file}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to stop tracedown: {e}")
            return False

    def _upload_trace(self, phase_label: str = "Unknown") -> bool:
        """
        Read the trace markdown file and upload it to Spacelift with a phase-specific plugin name.

        Returns:
            bool: True if uploaded successfully, False otherwise
        """
        output_file = os.path.join(self._plugin_dir, self._output_file)

        # Check if trace file exists
        if not os.path.exists(output_file):
            self.logger.warning(f"Trace file does not exist: {output_file}")
            return False

        try:
            # Read the markdown content
            with open(output_file, "r") as f:
                markdown_content = f.read()

            if not markdown_content.strip():
                self.logger.warning("Trace file is empty")
                return False

            # Temporarily modify the plugin name to include the phase
            original_plugin_name = self.__plugin_name__
            self.__plugin_name__ = f"{original_plugin_name} - {phase_label}"
            try:
                self.logger.info(
                    f"Uploading traces markdown for {phase_label} ({len(markdown_content)} bytes)"
                )
                result = self.send_markdown(markdown_content)
                return result
            finally:
                # Restore the original plugin name
                self.__plugin_name__ = original_plugin_name

        except Exception as e:
            self.logger.error(f"Failed to upload trace: {e}")
            return False

    def before_init(self) -> None:
        """Start tracedown before Terraform init."""
        self.logger.info("Starting tracedown collector for plan phase")
        if not self._start_tracedown():
            self.logger.error(
                "Failed to start tracedown - traces will not be collected"
            )

    def after_plan(self) -> None:
        """
        Stop tracedown after plan phase, then upload the traces immediately.
        """
        self.logger.info("Stopping tracedown after plan phase")
        if self._stop_tracedown():
            self.logger.info("Plan phase traces captured successfully")
            # Upload the traces immediately
            if self._upload_trace(phase_label="Init and Plan"):
                self.logger.info("Plan phase traces uploaded successfully")
            else:
                self.logger.error("Failed to upload plan phase traces")
        else:
            self.logger.warning(
                "Failed to stop tracedown after plan - traces may be incomplete"
            )

    def before_apply(self) -> None:
        """
        Start tracedown before apply phase.

        This ensures we capture apply traces regardless of whether the container
        was restarted between plan and apply.
        """
        self.logger.info("Starting tracedown collector for apply phase")
        if not self._start_tracedown():
            self.logger.error(
                "Failed to start tracedown - apply traces will not be collected"
            )

    def after_apply(self) -> None:
        """
        Stop tracedown after apply phase, then upload the traces immediately.
        """
        self.logger.info("Stopping tracedown after apply phase")
        if self._stop_tracedown():
            self.logger.info("Apply phase traces captured successfully")
            # Upload the traces immediately
            if self._upload_trace(phase_label="Apply"):
                self.logger.info("Apply phase traces uploaded successfully")
            else:
                self.logger.error("Failed to upload apply phase traces")
        else:
            self.logger.warning(
                "Failed to stop tracedown after apply - traces may be incomplete"
            )
