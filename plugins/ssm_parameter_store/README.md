# SSM Parameter Store Plugin

This plugin fetches secrets from AWS Systems Manager Parameter Store based on stack labels and makes them available as environment variables throughout your Spacelift runs.

## Features

- **Label-based configuration**: Define SSM parameter paths using stack labels
- **Automatic environment injection**: Fetched secrets are available as TF variables in all hooks
- **Multiple secrets support**: Add multiple `secret:` labels to fetch multiple parameters
- **Secure persistence**: Uses shell script sourcing with restrictive permissions for secure variable persistence
- **Auto-attachment**: Supports the `autoattach` label for easy deployment

## Usage

### 1. Deploy the Plugin

Upload this plugin to your Spacelift account using TF/OpenTofu or the Spacelift UI.

### 2. Configure AWS Credentials

Ensure your stack has AWS credentials configured. You can use:
- **AWS integration** (recommended) - Configure via Spacelift's AWS integration
- **Environment variables** - Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- **IAM roles** - If running on AWS infrastructure with appropriate IAM roles

### 3. Add Labels to Your Stack

Add labels to your Spacelift stack in the format `secret:/path/to/parameter`:

**Via Spacelift UI:**
1. Navigate to your stack
2. Go to Settings → Labels
3. Add labels like `secret:/prod/db/password`

**Via TF:**
```hcl
resource "spacelift_stack" "example" {
  name   = "my-stack"
  # ... other configuration ...

  labels = [
    "secret:/prod/db/password",
    "secret:/prod/api/key",
    "secret:/prod/db-connection-string"
  ]
}
```

### 4. Attach the Plugin

Attach the plugin to your stack using the stack label:

```hcl
resource "spacelift_stack" "example" {
  # ... configuration ...

  labels = [
    "ssm-parameter-store",
    "secret:/prod/db/password"
  ]
}
```

## Label Format

Labels must follow this pattern:
```
secret:/path/to/parameter
```

Where `/path/to/parameter` is the full path to your SSM parameter.

## Environment Variable Naming

The plugin converts SSM parameter paths to TF variable names:

| SSM Parameter Path | Environment Variable |
|-------------------|---------------------|
| `/prod/db/password` | `TF_VAR_SSM_PROD_DB_PASSWORD` |
| `/prod/api/key` | `TF_VAR_SSM_PROD_API_KEY` |
| `/prod/db-connection-string` | `TF_VAR_SSM_PROD_DB_CONNECTION_STRING` |
| `/app/config/oauth_client_id` | `TF_VAR_SSM_APP_CONFIG_OAUTH_CLIENT_ID` |

**Naming Rules:**
- Prefix: `TF_VAR_SSM_`
- Leading slash removed
- Forward slashes (`/`) replaced with underscores (`_`)
- Hyphens (`-`) replaced with underscores (`_`)
- All characters uppercased
- Other special characters replaced with underscores

## Configuration

### Plugin Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `aws_region` | AWS region for SSM Parameter Store | No | `us-east-1` |

Set parameters when attaching the plugin or in the plugin configuration.

## Example Workflow

### 1. Create SSM Parameters in AWS

```bash
aws ssm put-parameter \
  --name "/prod/db/password" \
  --value "my-secure-password" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/prod/api/key" \
  --value "api-key-value" \
  --type "SecureString"
```

### 2. Configure Spacelift Stack

```hcl
resource "spacelift_stack" "prod_app" {
  name        = "prod-app"
  repository  = "my-org/my-app"
  branch      = "main"

  labels = [
    "ssm-parameter-store",
    "secret:/prod/db/password",
    "secret:/prod/api/key"
  ]
}

resource "spacelift_aws_integration_attachment" "prod_app" {
  stack_id            = spacelift_stack.prod_app.id
  integration_id      = spacelift_aws_integration.main.id
  read                = true
  write               = false
}
```

### 3. Use in TF

```hcl
# The secrets are automatically available as TF variables
variable "SSM_PROD_DB_PASSWORD" {
  type    = string
  sensitive = true
}

resource "aws_db_instance" "main" {
  # ... other configuration ...
  password = var.SSM_PROD_DB_PASSWORD
}
```

Or use them directly in hooks:

```bash
# In a before_apply hook
echo "Connecting to database with password: $TF_VAR_SSM_PROD_DB_PASSWORD"
```

## Security Considerations

- **Encryption**: The plugin uses `WithDecryption=True` to automatically decrypt SecureString parameters
- **Permissions**: Ensure your AWS credentials have `ssm:GetParameter` permission for the paths you're accessing
- **File Permissions**: The `/tmp/ssm_exports.sh` script is created with `0600` permissions (owner read/write only)
- **Workspace Isolation**: Secrets are only accessible within the specific run's workspace
- **No Disk Persistence**: The `/tmp/ssm_exports.sh` file is ephemeral and removed after the run completes

### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter"
      ],
      "Resource": [
        "arn:aws:ssm:us-east-1:123456789012:parameter/prod/*"
      ]
    }
  ]
}
```

## Troubleshooting

### Parameter Not Found

**Error**: `Parameter not found: /prod/db/password`

**Solutions**:
- Verify the parameter exists in AWS SSM
- Check the parameter path is correct (including leading slash)
- Verify the AWS region is correct
- Ensure your AWS credentials have access to the parameter

### AWS Credentials Not Configured

**Error**: `Failed to create SSM client`

**Solutions**:
- Ensure AWS integration is attached to the stack
- Verify AWS environment variables are set (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- Check IAM role configuration if using role-based authentication

### Environment Variables Not Available

**Issue**: Secrets fetched but not available in TF

**Solutions**:
- Verify the plugin contexts are properly defined and hooks are executing
- Check that `/tmp/ssm_exports.sh` exists and contains your export statements
- Ensure no other hooks or plugins are clearing environment variables
- Verify you're accessing the correct variable name in TF (lowercase, without `TF_VAR_` prefix in `.tf` files)
- Check the plugin logs for successful execution

## How It Works

1. **Label Parsing**: The plugin reads `TF_VAR_spacelift_stack_labels` environment variable
2. **Secret Discovery**: Extracts all labels starting with `secret:`
3. **AWS Connection**: Connects to AWS SSM using boto3 with provided credentials
4. **Parameter Fetching**: Retrieves each parameter with automatic decryption
5. **Export Script Creation**: Writes parameters to `/tmp/ssm_exports.sh` as export statements
6. **Hook Sourcing**: Plugin contexts define hooks that source `/tmp/ssm_exports.sh` in:
   - `before_init`
   - `before_plan`
   - `before_apply`
   - `before_perform`
7. **Variable Availability**: Once sourced, variables are available as `TF_VAR_*` environment variables for TF

The plugin creates a shell script with export statements that gets sourced at the beginning of each major hook phase, ensuring your secrets are available as TF variables throughout the entire run lifecycle.

## Development

### Testing Locally

```bash
# Set required environment variables
export TF_VAR_spacelift_stack_labels="secret:/test/param1,secret:/test/param2"
export SPACEFORGE_PARAM_aws_region="us-west-2"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# Install dependencies
pip install -e .
pip install -r plugins/ssm_parameter_store/requirements.txt

# Run the plugin
cd plugins/ssm_parameter_store
python -m spaceforge run --plugin-file plugin.py before_init
```

### Regenerating plugin.yaml

```bash
cd plugins/ssm_parameter_store
python -m spaceforge generate plugin.py
```

## License

This plugin is part of the Spacelift plugins repository and follows the same license terms.

## Support

For issues, questions, or contributions, please visit the [Spacelift plugins repository](https://github.com/spacelift-io/plugins).
