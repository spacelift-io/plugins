# AWS SAM Plugin

Packages AWS SAM templates into CloudFormation templates for Spacelift's CloudFormation integration.

## Overview

This plugin runs `sam package` before initialization to convert SAM templates to CloudFormation,
enabling you to deploy serverless applications through Spacelift's CloudFormation workflow.

## Prerequisites

- A CloudFormation stack configured in Spacelift
- SAM template in your repository
- S3 bucket for template storage (configured via Spacelift CloudFormation settings)

## Configuration

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| S3 Prefix | S3 prefix for SAM artifacts | `sam-artifacts` |
| Additional Arguments | Extra arguments for `sam package` | (empty) |

### Required Environment Variables

These are automatically set by Spacelift's CloudFormation integration:

- `CF_METADATA_REGION`: AWS region
- `CF_METADATA_TEMPLATE_BUCKET`: S3 bucket for templates
- `CF_METADATA_ENTRY_TEMPLATE_FILE`: Output template path

## Usage

1. Create a CloudFormation stack in Spacelift pointing to your SAM template
2. Install and attach this plugin to the stack
3. The plugin automatically packages your SAM template before each run

## References

- [Spacelift CloudFormation Getting Started](https://docs.spacelift.io/vendors/cloudformation/getting-started)
- [Spacelift CloudFormation Reference](https://docs.spacelift.io/vendors/cloudformation/reference)
- [AWS SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-package.html)
