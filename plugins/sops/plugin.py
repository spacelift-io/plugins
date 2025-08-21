from sopsy import Sops, SopsyError
from pathlib import Path
import yaml

from spaceforge import SpaceforgePlugin, Binary

class SopsPlugin(SpaceforgePlugin):
    """
# Plugin Sops

This adds the `SOPS` plugin to your Spacelift account.
It will decrypt an arbitrary number of files based on config you set.

## Usage

1. Spin up the plugin
2. Add the autoattach label to any stack that has access to your decryption keys.
3. The secrets you define in your `.sops.yaml` will automatically be decrypted with your configured `creation_rules`.

#### .sops.yaml

The `.sops.yaml` file is a configuration file that tells `sops` how to decrypt your files.
It is a YAML file that contains a list of `creation_rules` that define how to decrypt your files.
Read more on sops official repository: https://github.com/getsops/sops

In addition to the sops config, this plugin also uses the `.sops.yaml` file to determine which files to decrypt.
simply add a list of `secrets` to your `.sops.yaml` in your working directory and the plugin will decrypt them.

The following `.sops.yaml` example will decrypt a `test_secret.yaml` file using the defined kms key.
```yaml
creation_rules:
  - kms: arn:aws:kms:us-east-2:694182862388:key/6825a259-28df-43be-80f8-6122eb8a5903

secrets:
  - test_secret.yaml
```
    """

    # Plugin metadata
    __plugin_name__ = "Sops"
    __labels__ = ["secrets management", "encryption"]
    __version__ = "1.0.0"
    __author__ = "Spacelift Team"

    __binaries__ = [
        Binary(
            name="sops",
            download_urls={
                "amd64": "https://github.com/getsops/sops/releases/download/v3.9.1/sops-v3.9.1.linux.amd64",
                "arm64": "https://github.com/getsops/sops/releases/download/v3.9.1/sops-v3.9.1.linux.arm64",
            }
        )
    ]

    def before_init(self):
        if not Path(".sops.yaml").exists():
            self.logger.error("No .sops.yaml file found.")
            return

        secrets = Path(".sops.yaml").read_text()
        try:
            secrets = yaml.safe_load(secrets)
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse .sops.yaml: {e}")
            return

        if "secrets" not in secrets:
            self.logger.error("No secrets key found in .sops.yaml.")
            return
        secrets = secrets["secrets"]

        for secret in secrets:
            if not Path(secret).exists():
                self.logger.error(f"Secret file {secret} does not exist.")
                continue

            try:
                self.logger.log(f"Decrypting secret {secret}.")
                sops = Sops(Path(secret), in_place=True)
                sops.decrypt()
                self.logger.log("Decryption successful.")
            except SopsyError as e:
                self.logger.error(f"Failed to decrypt secret: {e}")
            except Exception as e:
                self.logger.error(f"An unexpected error occurred: {e}")