# TruffleHog Secret Scanner Plugin

This plugin runs TruffleHog secret scanning on the filesystem during the
before_plan hook and reports findings organized by verification status.

## Features

- Scans filesystem for 800+ types of secrets including AWS keys, API tokens,
  and database credentials
- Detects and reports both verified (confirmed active) and unverified secrets
- Generates detailed Markdown reports organized by verification status
- Reports file locations and line numbers for each finding
- Includes rotation guide URLs for remediation
- Fails the run when secrets are detected
- Never logs or displays actual secret values

## Configuration

### Parameters

- **Results Filter**: Controls which finding types to report. Options include:
  - `verified` - Only confirmed active secrets
  - `unknown` - Only unverified patterns
  - `verified,unknown` - Both types (default)

- **Additional Arguments**: Optional command-line arguments to pass to TruffleHog
  for advanced customization

## Usage

The plugin automatically runs before the plan phase and:

1. Scans your filesystem with TruffleHog
2. Reports verified secrets and unverified patterns
3. Organizes findings by verification status
4. Provides detector descriptions, file locations, and rotation guides
5. Fails the run when secrets are detected

## Security Note

This plugin NEVER logs or displays actual secret values. Only metadata about detected
secrets is reported.
