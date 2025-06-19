from typing import Dict, List, Literal, Optional

from pydantic import Field
from pydantic.dataclasses import dataclass as pydantic_dataclass

# For truly optional fields without default: null in schema
optional_field = Field(default_factory=lambda: None, exclude=True)

BinaryType = Literal[
    "amd64",
    "arm64",
]


@pydantic_dataclass
class Binary:
    """
    A class to represent a binary file.

    Attributes:
        name (str): The name of the binary file.
        path (str): The path to the binary file.
        sensitive (bool): Whether the binary file is sensitive.
    """

    name: str
    download_urls: Dict[BinaryType, str]


@pydantic_dataclass
class Parameter:
    """
    A class to represent a parameter with a name and value.

    Attributes:
        name (str): The name of the parameter.
        description (str): A description of the parameter.
        sensitive (bool): Whether the parameter contains sensitive information.
        required (bool): Whether the parameter is required.
        default (Optional[str]): The default value of the parameter, if any. (required if sensitive is False)
    """

    name: str
    description: str
    sensitive: bool = False
    required: bool = False
    default: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.required and self.default is None:
            raise ValueError(
                f"Default value for parameter {self.name} should be set if parameter is optional."
            )


@pydantic_dataclass
class Variable:
    """
    A class to represent an environment variable.

    Attributes:
        key (str): The key of the environment variable.
        value (Optional[str]): The value of the environment variable, if set.
        value_from_parameter (Optional[str]): The name of the plugin variable to use as the value.
        sensitive (bool): Whether the environment variable is sensitive.
    """

    key: str
    value: Optional[str] = optional_field
    value_from_parameter: Optional[str] = optional_field
    sensitive: bool = False

    def __post_init__(self) -> None:
        if self.value is None and self.value_from_parameter is None:
            raise ValueError(
                "Either value or value_from_parameter must be set for EnvVariable."
            )


@pydantic_dataclass
class MountedFile:
    """
    A class to represent a mounted file.

    Attributes:
        path (str): The path of the mounted file.
        content (str): The content of the mounted file.
        sensitive (bool): Whether the content of the file is sensitive.
    """

    path: str
    content: str
    sensitive: bool = False


HookType = Literal[
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
]


@pydantic_dataclass
class Context:
    """
    A class to represent a context for a plugin.

    Attributes:
        name_prefix (str): The name of the context, will be appended with a unique ID.
        description (str): A description of the context.
        labels (dict): Labels associated with the context.
        env (list): List of variables associated with the context.
        hooks (dict): Hooks associated with the context.
    """

    name_prefix: str
    description: str
    env: Optional[List[Variable]] = optional_field
    mounted_files: Optional[List[MountedFile]] = optional_field
    hooks: Optional[Dict[HookType, List[str]]] = optional_field
    labels: Optional[Dict[str, str]] = optional_field


@pydantic_dataclass
class Webhook:
    """
    A class to represent a webhook configuration.

    Attributes:
        name_prefix (str): The name of the webhook, will be appended with a unique ID.
        endpoint (str): The URL endpoint for the webhook.
        labels (Optional[dict]): Labels associated with the webhook.
        secrets (Optional[list[Variable]]): List of secrets associated with the webhook.
    """

    name_prefix: str
    endpoint: str
    labels: Optional[Dict[str, str]] = optional_field
    secrets: Optional[List[Variable]] = optional_field


@pydantic_dataclass
class Policy:
    """
    A class to represent a policy configuration.

    Attributes:
        name_prefix (str): The name of the policy, will be appended with a unique ID.
        type (str): The type of the policy (e.g., "terraform", "kubernetes").
        body (str): The body of the policy, typically a configuration or script.
        labels (Optional[dict[str, str]]): Labels associated with the policy.
    """

    name_prefix: str
    type: str
    body: str
    labels: Optional[Dict[str, str]] = optional_field


@pydantic_dataclass
class PluginManifest:
    """
    A class to represent the manifest of a Spacelift plugin.

    Attributes:
        name_prefix (str): The name of the plugin, will be appended with a unique ID.
        description (str): A description of the plugin.
        author (str): The author of the plugin.
        parameters (list[Parameter]): List of parameters for the plugin.
        contexts (list[Context]): List of contexts for the plugin.
        webhooks (list[Webhook]): List of webhooks for the plugin.
        policies (list[Policy]): List of policies for the plugin.
    """

    name_prefix: str
    version: str
    description: str
    author: str
    parameters: Optional[List[Parameter]] = optional_field
    contexts: Optional[List[Context]] = optional_field
    webhooks: Optional[List[Webhook]] = optional_field
    policies: Optional[List[Policy]] = optional_field


if __name__ == "__main__":
    import json

    from pydantic import TypeAdapter

    print(json.dumps(TypeAdapter(PluginManifest).json_schema(), indent=2))
