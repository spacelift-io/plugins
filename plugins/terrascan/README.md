# Plugin Terrascan

The Terrascan plugin scans your Infrastructure as Code for security and compliance
violations and generates a detailed report with findings categorized by severity.

Supports Terraform, CloudFormation, Kubernetes, and Helm.

You can also access the scan data from a plan policy via the
`input.third_party_metadata.custom.terrascan` object. An example Plan policy is
included with the plugin.

## Usage

1. Install the plugin in your Spacelift account
2. Attach it to your stacks (or use the `autoattach` label)
3. The plugin runs automatically after each plan
4. View results in the Plugins Output tab and/or configure the included policy

## Configuration

The plugin supports these parameters:

- **Additional Arguments**: Pass extra flags to Terrascan

Examples:
- Filter by severity: `--severity HIGH,MEDIUM`
- Skip specific rules: `--skip-rules AC_AWS_0058,AC_AWS_0053`
- Combined: `--severity HIGH --skip-rules AC_AWS_0001`

## Policy Integration

Example policy to block runs with HIGH severity violations:

```rego
package spacelift

import rego.v1

terrascan_data := input.third_party_metadata.custom.terrascan
summary := terrascan_data.summary

deny contains sprintf("Found %d HIGH severity security issues", [summary.high]) if {
    summary.high > 0
}
```

## More Information

- [Terrascan Documentation](https://runterrascan.io/docs/)
- [Terrascan GitHub Repository](https://github.com/tenable/terrascan)
