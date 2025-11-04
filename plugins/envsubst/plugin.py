from spaceforge import SpaceforgePlugin, Context, Binary


class EnvsubstPlugin(SpaceforgePlugin):
    """
# Plugin Envsubst
This plugin allows the use of environment variables in Kubernetes manifests.

## Usage
You can define your parameterized Kubernetes manifest as seen below:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: my-container
    image: my-image
    env:
    - name: MY_ENV_VAR
      value: ${MY_ENV_VAR}
```
This expects the environment variable `MY_ENV_VAR` to be defined in the Kubernetes Spacelift stack.
    """

    # Plugin metadata
    __plugin_name__ = "Envsubst"
    __labels__ = ["kubernetes", "environment"]
    __version__ = "1.0.1"
    __author__ = "Spacelift Team"

    __binaries__ = [
        Binary(
            name="envsubst",
            download_urls={
                "amd64": "https://binhub.dev/e/envsubst/1.4.3/linux-amd64/envsubst",
                "arm64": "https://binhub.dev/e/envsubst/1.4.3/linux-arm64/envsubst"
            }
        )
    ]

    # Plugin contexts
    __contexts__ = [
        Context(
            priority=1,
            name_prefix="kubernetes",
            description="envsubst plugin that allows the use of environment variables in kubernetes manifests",
            hooks={
                "before_init": [
                    'export PATH="/mnt/workspace/plugins/plugin_binaries:$PATH"',
                    'for file in *; do envsubst < "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"; done'
                ]
            }
        )
    ]

    def __init__(self):
        super().__init__()
