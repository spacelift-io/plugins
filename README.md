# Spaceforge - Build Spacelift Plugins in Python

Spaceforge is a Python framework that makes it easy to build powerful Spacelift plugins using a declarative, hook-based approach. Define your plugin logic in Python, and spaceforge automatically generates the plugin manifest for Spacelift.

## Installation

Install spaceforge from PyPI:

```bash
pip install spaceforge
```

## Quick Start

### 1. Create Your Plugin

Create a Python file (e.g., `my_plugin.py`) and inherit from `SpaceforgePlugin`:

```python
from spaceforge import SpaceforgePlugin, Parameter, Variable, Context
import os

class MyPlugin(SpaceforgePlugin):
    # Plugin metadata
    __plugin_name__ = "my-awesome-plugin"
    __version__ = "1.0.0"
    __author__ = "Your Name"
    
    # Define plugin parameters
    __parameters__ = [
        Parameter(
            name="api_key",
            description="API key for external service",
            required=True,
            sensitive=True
        ),
        Parameter(
            name="environment",
            description="Target environment",
            required=False,
            default="production"
        )
    ]
    
    # Define Spacelift contexts
    __contexts__ = [
        Context(
            name_prefix="my-plugin",
            description="Main plugin context",
            env=[
                Variable(
                    key="API_KEY",
                    value_from_parameter="api_key",
                    sensitive=True
                ),
                Variable(
                    key="ENVIRONMENT",
                    value_from_parameter="environment"
                )
            ]
        )
    ]
    
    def after_plan(self):
        """Run security checks after Terraform plan"""
        # Run external commands
        return_code, stdout, stderr = self.run_cli("my-security-tool", "--scan", "./", '--api', os.environ["API_KEY"])
        
        if return_code != 0:
            self.logger.error("Security scan failed!")
            exit(1)
            
        self.logger.info("Security scan passed!")
```

### 2. Generate Plugin Manifest

Generate the Spacelift plugin YAML manifest:

```bash
spaceforge generate my_plugin.py
```

This creates `plugin.yaml` that you can upload to Spacelift.

### 3. Test Your Plugin

Test individual hooks locally:

```bash
# Set parameter values
export API_KEY="your-api-key"
export ENVIRONMENT="staging"

# Test the after_plan hook
spaceforge runner after_plan
```

## Available Hooks

Override these methods in your plugin to add custom logic:

- `before_init()` - Before Terraform init
- `after_init()` - After Terraform init  
- `before_plan()` - Before Terraform plan
- `after_plan()` - After Terraform plan
- `before_apply()` - Before Terraform apply
- `after_apply()` - After Terraform apply
- `before_perform()` - Before the run performs
- `after_perform()` - After the run performs
- `before_destroy()` - Before Terraform destroy
- `after_destroy()` - After Terraform destroy
- `after_run()` - After the run completes

## Plugin Components

### Parameters

Define user-configurable parameters:

```python
__parameters__ = [
    Parameter(
        name="database_url",
        description="Database connection URL",
        required=True,
        sensitive=True,
        default="postgresql://localhost:5432/mydb"
    ),
    Parameter(
        name="timeout", 
        description="Timeout in seconds",
        required=False,
        default=30
    )
]
```

### Contexts

Define Spacelift contexts with environment variables and custom hooks:

```python
__contexts__ = [
    Context(
        name_prefix="production",
        description="Production environment context",
        labels={"env": "prod"},
        env=[
            Variable(
                key="DATABASE_URL",
                value_from_parameter="database_url",
                sensitive=True
            ),
            Variable(
                key="API_ENDPOINT", 
                value="https://api.prod.example.com"
            )
        ],
        hooks={
            "before_apply": [
                "echo 'Starting production deployment'",
                "kubectl get pods"
            ]
        }
    )
]
```

### Binaries

Automatically download and install external tools:

```python
__binaries__ = [
    Binary(
        name="kubectl",
        download_urls={
            "amd64": "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl",
            "arm64": "https://dl.k8s.io/release/v1.28.0/bin/linux/arm64/kubectl"
        }
    )
]
```

### Policies

Define OPA policies for your plugin:

```python
__policies__ = [
    Policy(
        name_prefix="security-check",
        type="notification",
        body="""
package spacelift

webhook[{"endpoint_id": "security-alerts"}] {
  input.run_updated.run.marked_unsafe == true
}
        """,
        labels={"type": "security"}
    )
]
```

### Webhooks

Define webhooks to trigger external actions:

```python
__webhooks__ = [
    Webhook(
        name_prefix="security-alerts",
        description="Send security alerts to external service",
        endpoint="https://alerts.example.com/webhook",
        secrets=[
            Variable(key="amazing", value="secret-value", sensitive=True)
        ],
    )
]
```

## Plugin Features

### Logging

Built-in structured logging with run context:

```python
def after_plan(self):
    self.logger.info("Starting security scan")
    self.logger.debug("Debug info (only shown when SPACELIFT_DEBUG=true)")  
    self.logger.warning("Warning message")
    self.logger.error("Error occurred")
```

### CLI Execution

Run external commands with automatic logging:

```python
def before_apply(self):
    # Run command with automatic output capture
    return_code, stdout, stderr = self.run_cli("terraform", "validate")
    
    if return_code != 0:
        self.logger.error("Terraform validation failed")
        exit(1)
```

### Spacelift API Integration

Query the Spacelift GraphQL API (requires `SPACELIFT_API_TOKEN` and `SPACELIFT_DOMAIN`):

```python
def after_plan(self):
    result = self.query_api("""
        query {
            stack(id: "my-stack-id") {
                name
                state
                latestRun {
                    id
                    state
                }
            }
        }
    """)
    
    self.logger.info(f"Stack state: {result['stack']['state']}")
```

### Access Plan and State

Access Terraform plan and state data:

```python
def after_plan(self):
    # Get the current plan
    plan = self.get_plan_json()
    
    # Get the state before changes
    state = self.get_state_before_json()
    
    # Analyze planned changes
    resource_count = len(plan.get('planned_values', {}).get('root_module', {}).get('resources', []))
    self.logger.info(f"Planning to manage {resource_count} resources")
```

### Send Rich Output

Send formatted markdown to the Spacelift UI:

```python
def after_plan(self):
    markdown = """
    # Security Scan Results
    
    ✅ **Passed:** 45 checks
    ⚠️ **Warnings:** 3 issues  
    ❌ **Failed:** 0 critical issues
    
    [View detailed report](https://security.example.com/reports/123)
    """
    
    self.send_markdown(markdown)
```

### Append to Policy Input

Append custom data to the OPA policy input:

The following example will create input available via `input.third_party_metadata.custom.my_custom_data` in your OPA policies:
```python
def after_plan(self):
    self.append_policy_input("my_custom_data", {
        "scan_results": {
            "passed": True,
            "issues": []
        }
    })
```

## CLI Commands

### Generate Plugin Manifest

```bash
# Generate from plugin.py (default filename)
spaceforge generate

# Generate from specific file  
spaceforge generate my_plugin.py

# Specify output file
spaceforge generate my_plugin.py -o custom-output.yaml

# Get help
spaceforge generate --help
```

### Test Plugin Hooks

```bash
# Set parameters via environment variables
export SPACEFORGE_PARAM_API_KEY="test-key" 
export SPACEFORGE_PARAM_TIMEOUT="60"

# Test specific hook
spaceforge runner after_plan

# Test with specific plugin file
spaceforge runner --plugin-file my_plugin.py before_apply

# Get help
spaceforge runner --help
```

## Plugin Development Tips

### 1. Handle Dependencies

If your plugin needs Python packages, create a `requirements.txt` file. Spaceforge automatically adds a `before_init` hook to install them:

```txt
requests>=2.28.0
pydantic>=1.10.0
```

### 2. Environment Variables

Access Spacelift environment variables in your hooks:

```python
def after_plan(self):
    run_id = os.environ.get('SPACELIFT_RUN_ID')
    stack_id = os.environ.get('SPACELIFT_STACK_ID')
    self.logger.info(f"Processing run {run_id} for stack {stack_id}")
```

### 3. Error Handling

Always handle errors gracefully:

```python
def after_plan(self):
    try:
        # Your plugin logic here
        result = self.run_external_service()
        
    except Exception as e:
        self.logger.error(f"Plugin failed: {str(e)}")
        # Exit with non-zero code to fail the run
        exit(1)
```

### 4. Testing and Debugging

- Set `SPACELIFT_DEBUG=true` to enable debug logging
- Use the runner command to test hooks during development
- Test with different parameter combinations
- Validate your generated YAML before uploading to Spacelift

## Example: Security Scanning Plugin

Here's a complete example of a security scanning plugin:

```python
import os
import json
from spaceforge import SpaceforgePlugin, Parameter, Variable, Context, Binary

class SecurityScannerPlugin(SpaceforgePlugin):
    __plugin_name__ = "security-scanner"
    __version__ = "1.0.0"
    __author__ = "Security Team"
    
    __binaries__ = [
        Binary(
            name="security-cli",
            download_urls={
                "amd64": "https://releases.example.com/security-cli-linux-amd64",
                "arm64": "https://releases.example.com/security-cli-linux-arm64"
            }
        )
    ]
    
    __parameters__ = [
        Parameter(
            name="api_token",
            description="Security service API token",
            required=True,
            sensitive=True
        ),
        Parameter(
            name="severity_threshold", 
            description="Minimum severity level to report",
            required=False,
            default="medium"
        )
    ]
    
    __contexts__ = [
        Context(
            name_prefix="security-scanner",
            description="Security scanning context",
            env=[
                Variable(
                    key="SECURITY_API_TOKEN",
                    value_from_parameter="api_token",
                    sensitive=True
                ),
                Variable(
                    key="SEVERITY_THRESHOLD",
                    value_from_parameter="severity_threshold"
                )
            ]
        )
    ]
    
    def after_plan(self):
        """Run security scan after Terraform plan"""
        self.logger.info("Starting security scan of Terraform plan")
        
        # Authenticate with security service
        return_code, stdout, stderr = self.run_cli(
            "security-cli", "auth", 
            "--token", os.environ["SECURITY_API_TOKEN"]
        )
        
        if return_code != 0:
            self.logger.error("Failed to authenticate with security service")
            exit(1)
        
        # Scan the Terraform plan
        return_code, stdout, stderr = self.run_cli(
            "security-cli", "scan", "terraform", 
            "--plan-file", "spacelift.plan.json",
            "--format", "json",
            "--severity", os.environ.get("SEVERITY_THRESHOLD", "medium"),
            print_output=False
        )
        
        if return_code != 0:
            self.logger.error("Security scan failed")
            for line in stderr:
                self.logger.error(line)
            exit(1)
        
        # Parse scan results
        try:
            results = json.loads('\n'.join(stdout))
            
            # Generate markdown report
            markdown = self._generate_report(results)
            self.send_markdown(markdown)
            
            # Fail run if critical issues found
            if results.get('critical_count', 0) > 0:
                self.logger.error(f"Found {results['critical_count']} critical security issues")
                exit(1)
                
            self.logger.info("Security scan completed successfully")
            
        except json.JSONDecodeError:
            self.logger.error("Failed to parse scan results")
            exit(1)
    
    def _generate_report(self, results):
        """Generate markdown report from scan results"""
        report = "# Security Scan Results\n\n"
        
        if results.get('total_issues', 0) == 0:
            report += "✅ **No security issues found!**\n"
        else:
            report += f"Found {results['total_issues']} security issues:\n\n"
            
            for severity in ['critical', 'high', 'medium', 'low']:
                count = results.get(f'{severity}_count', 0)
                if count > 0:
                    emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[severity]
                    report += f"- {emoji} **{severity.upper()}:** {count}\n"
        
        if results.get('report_url'):
            report += f"\n[View detailed report]({results['report_url']})\n"
            
        return report
```

Generate and test this plugin:

```bash
# Generate the manifest
spaceforge generate security_scanner.py

# Test locally
export SPACEFORGE_PARAM_API_TOKEN="your-token"
export SPACEFORGE_PARAM_SEVERITY_THRESHOLD="high"
spaceforge runner after_plan
```

## Speeding up plugin execution

There are a few things you can do to speed up plugin execution.

1. Ensure your runner has `spaceforge` preinstalled. This will avoid the overhead of installing it during the run. (15-30 seconds)
2. If youre using binaries, we will only install the binary if its not found. You can gain a few seconds by ensuring its already on the runner.
3. If your plugin has a lot of dependencies, consider using a prebuilt runner image with your plugin and its dependencies installed. This avoids the overhead of installing them during each run.
4. Ensure your runner has enough core resources (CPU, memory) to handle the plugin execution efficiently. If your plugin is resource-intensive, consider using a more powerful runner.

## Next Steps

1. **Install spaceforge:** `pip install spaceforge`
2. **Create your plugin:** Start with the quick start example
3. **Test locally:** Use the runner command to test your hooks
4. **Generate manifest:** Use the generate command to create plugin.yaml
5. **Upload to Spacelift:** Add your plugin manifest to your Spacelift account

For more advanced examples, see the [plugins](plugins/) directory in this repository.
