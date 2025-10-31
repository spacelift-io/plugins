import json
import os

from spaceforge import SpaceforgePlugin, Parameter, Variable, Context, Policy, Binary


class HelmPlugin(SpaceforgePlugin):
    """
# Plugin Helm

This plugin integrates Helm into Spacelift, allowing users to manage Kubernetes applications using Helm charts.

## Usage

1. Spin up the plugin
2. Add the autoattach label to any kubernetes stack that you intened to use helm with
3. Configure the following environment variables in your stack:
    - `REPO_NAME`: The name of the Helm repository to add.
    - `REPO_URL`: The URL of the Helm repository to add.
    - `RELEASE_NAME`: The name of the Helm release.
    - `PATH_TO_CHART`: The path to the Helm chart.
    - `HELM_VALUES`: The path to the values file for the Helm chart.
    """

    # Plugin metadata
    __plugin_name__ = "Helm"
    __labels__ = ["helm", "kubernetes"]
    __version__ = "1.0.0"
    __author__ = "Spacelift Team"

    __binaries__ = [
        Binary(
            name="helm",
            download_urls={
                "amd64": "https://binhub.dev/h/helm/3.18.6/linux-amd64/helm",
                "arm64": "https://binhub.dev//h/helm/3.18.6/linux-arm64/helm"
            }
        )
    ]

    # Plugin contexts
    __contexts__ = [
        Context(
            priority=1,
            name_prefix="helm",
            description="helm plugin that allows you to use helm charts in your kubernetes spacelift stacks",
            hooks={
                "before_init": [
                    'export PATH="/mnt/workspace/plugins/plugin_binaries:$PATH"',
                    'helm repo add $REPO_NAME $REPO_URL',
                    'helm template $RELEASE_NAME $PATH_TO_CHART --values $HELM_VALUES > deployment.yaml',
                    'rm $HELM_VALUES'
                ]
            }
        )
    ]

    def __init__(self):
        super().__init__()
        self.logger.info("Initializing Helm Plugin")
