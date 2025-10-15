# Plugin Trivy

The Trivy plugin scans your Terraform/OpenTofu configurations for security misconfigurations
and generates a detailed report with findings categorized by severity.

You can also access the scan data from a plan policy via the
`input.third_party_metadata.custom.trivy` object. An example Plan policy is
included with the plugin.

## Usage

1. Install the plugin in your Spacelift account
2. Attach it to stacks using Terraform/OpenTofu (or use the `autoattach` label)
3. The plugin runs automatically after each plan
4. View results in the Plugins Output tab and/or configure the included policy

## Configuration

Use the "Additional Arguments" parameter to pass extra flags to Trivy, for example:
- `--severity CRITICAL,HIGH` to scan only critical and high severity issues
- `--skip-dirs tests` to exclude specific directories