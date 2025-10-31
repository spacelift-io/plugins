# Checkov Security Scanner Plugin

This plugin runs Checkov security scanning on Terraform/OpenTofu configurations
during the after_plan hook and reports findings with detailed resource-level
information.

## Features

- Executes Checkov against Terraform/OpenTofu configurations
- Parses and categorizes security findings by severity (when available)
- Generates detailed Markdown reports organized by severity level
- Adds scan results to policy input for OPA policy enforcement
- Supports configurable additional arguments for filtering and customization

## Configuration

### Parameters

- **Additional Arguments**: Optional command-line arguments to pass to Checkov
  (e.g., `--check HIGH,CRITICAL` or `--skip-check CKV_AWS_123`)

### Severity Support

Severity levels (CRITICAL, HIGH, MEDIUM, LOW) are available when using Checkov
with a Bridgecrew/Prisma Cloud API key. To enable severity data:

```
--bc-api-key YOUR_API_KEY
```

Without an API key, the plugin still works but findings are not categorized by
severity in the report.

## Usage

The plugin automatically runs after the plan phase and:

1. Scans your Terraform/OpenTofu code with Checkov
2. Reports failed security checks in a formatted Markdown report
3. Organizes findings by severity level (CRITICAL, HIGH, MEDIUM, LOW) when available
4. Provides check details, resource names, file locations, and remediation links
5. Adds comprehensive scan data to policy input for OPA evaluation

## Example OPA Policy

An example Plan policy is included that denies runs based on severity thresholds.
You can customize the max_critical, max_high, max_medium, and max_low values:

```rego
package spacelift

import rego.v1

# Configure maximum allowed findings by severity
max_critical := 0
max_high := 0
max_medium := 100
max_low := 100

checkov_data := input.third_party_metadata.custom.checkov

deny contains sprintf("Found %d CRITICAL severity Checkov security checks", [checkov_data.summary.critical]) if {
    checkov_data.summary.critical > max_critical
}

deny contains sprintf("Found %d HIGH severity Checkov security checks", [checkov_data.summary.high]) if {
    checkov_data.summary.high > max_high
}
```
