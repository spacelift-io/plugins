# Spaceforge Framework

A Python framework for building Spacelift plugins with hook-based functionality.

## Overview

Spaceforge provides a simple, declarative way to create Spacelift plugins by inheriting from the `SpaceforgePlugin` base class and implementing hook methods. The framework automatically handles parameter loading, logging, and YAML generation.

## Architecture

### Core Components

- **SpaceforgePlugin** (`plugin.py`) - Base class with hook methods and utilities
- **PluginRunner** (`runner.py`) - Executes hook methods, loads parameters from environment
- **PluginGenerator** (`generator.py`) - Analyzes Python plugins and generates `plugin.yaml`
- **CLI Interface** (`__main__.py`) - Click-based CLI with `generate` and `runner` subcommands
- **Pydantic Dataclasses** (`cls.py`) - Type-safe data structures with validation

### Data Validation

The framework uses pydantic dataclasses for all plugin definitions, providing:
- **Type safety**: All plugin components are strongly typed
- **Automatic validation**: Data structures are validated during object creation
- **JSON schema generation**: Plugin manifests include JSON schema for validation
- **Runtime checks**: For example, Variables must have either `value` or `value_from_parameter`

### Plugin Structure

```python
from spaceforge import SpaceforgePlugin, Parameter, Variable, Context, Webhook, Policy, MountedFile

class MyPlugin(SpaceforgePlugin):
    # Plugin metadata
    __plugin_name__ = "my-plugin"
    __version__ = "1.0.0"
    __author__ = "Your Name"
    
    # Parameter definitions using pydantic dataclasses
    __parameters__ = [
        Parameter(
            name="api_key",
            description="API key for authentication",
            required=True,
            sensitive=True
        )
    ]
    
    # Context definitions using pydantic dataclasses
    __contexts__ = [
        Context(
            name="main",
            description="Main plugin context",
            env=[
                Variable(
                    key="API_KEY",
                    value_from_parameter="api_key",
                    sensitive=True
                )
            ],
            hooks={
                "after_plan": ["echo 'Custom command here'"]
            },
            mounted_files=[
                MountedFile(
                    path="config.yaml",
                    content="key: value",
                    sensitive=False
                )
            ]
        )
    ]
    
    # Webhook definitions using pydantic dataclasses
    __webhooks__ = [
        Webhook(
            name="my_webhook",
            endpoint="https://example.com/webhook",
            secrets=[
                Variable(
                    key="WEBHOOK_SECRET",
                    value_from_parameter="api_key"
                )
            ]
        )
    ]
    
    # Policy definitions using pydantic dataclasses  
    __policies__ = [
        Policy(
            name="my_policy",
            type="notification",
            body="package spacelift\n# Policy content here",
            labels={"type": "security"}
        )
    ]
    
    def after_plan(self):
        self.logger.info("Running after plan")
        # Your plugin logic here
```

## Available Hooks

Override these methods in your plugin:

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

## Plugin Features

### Logging

Built-in colored logging with run ID and plugin name:

```python
self.logger.info("Information message")
self.logger.debug("Debug message")  # Only shown when SPACELIFT_DEBUG=true
self.logger.warning("Warning message")
self.logger.error("Error message")
```

### CLI Execution

Run external commands with logging:

```python
self.run_cli("terraform", "plan", "-out=tfplan")
```

### Spacelift API Integration

Query the Spacelift GraphQL API:

```python
# Requires SPACELIFT_API_TOKEN and SPACELIFT_DOMAIN environment variables
result = self.query_api("""
    query {
        stack(id: "stack-id") {
            name
            state
        }
    }
""")
```

### Plan and State Access

Access Terraform plan and state data:

```python
plan = self.get_plan_json()  # Returns parsed spacelift.plan.json
state = self.get_state_before_json()  # Returns parsed spacelift.state.before.json
```

## Parameter System

Parameters are defined using the `Parameter` pydantic dataclass and automatically loaded from environment variables:

```python
from spaceforge import Parameter

__parameters__ = [
    Parameter(
        name="database_url",
        description="Database connection URL",
        required=True,
        sensitive=True,
        default="postgresql://localhost:5432/mydb"
    )
]
```

Parameters are interpolated by spacelift at install time, allowing you to reference them in contexts and hooks using `${param.name}` syntax.

## Context System

Contexts define Spacelift environments using the `Context` pydantic dataclass:

```python
from spaceforge import Context, Variable, MountedFile

__contexts__ = [
    Context(
        name="production",
        description="Production environment",
        labels={
            "environment": "production"
        },
        env=[
            Variable(
                key="DATABASE_URL",
                value_from_parameter="database_url",
                sensitive=True
            )
        ],
        hooks={
            "after_plan": [
                "echo 'Running production validation'"
            ]
        },
        mounted_files=[
            MountedFile(
                path="app.conf",
                content="production config",
                sensitive=False
            )
        ]
    )
]
```

**Important**: Variables must have either a `value` or `value_from_parameter` field. The framework automatically validates this during plugin generation.

## CLI Usage

### Generate Plugin YAML

```bash
# Generate from plugin.py (default)
python -m spaceforge generate

# Generate from specific file
python -m spaceforge generate my_plugin.py

# Specify output file
python -m spaceforge generate my_plugin.py -o my_plugin.yaml
```

### Test Plugin Hooks

```bash
# Set plugin parameters
export API_KEY="your-key"

# Run specific hook
python -m spaceforge runner after_plan

# Run with specific plugin file
python -m spaceforge runner --plugin-file my_plugin.py before_apply
```

### Get Help

```bash
python -m spaceforge --help
python -m spaceforge generate --help
python -m spaceforge runner --help
```

## Generated YAML Structure

The framework automatically generates standard Spacelift plugin YAML:

## Development Tips

1. **Requirements**: If your plugin has dependencies, create a `requirements.txt` file. The generator will automatically add a `before_init` hook to install them.

2. **Testing**: Use the runner command to test individual hooks during development.

3. **Debugging**: Set `SPACELIFT_DEBUG=true` to enable debug logging.

4. **API Access**: Export `SPACELIFT_API_TOKEN` and `SPACELIFT_DOMAIN` to enable Spacelift API queries.

## Error Handling

The framework provides built-in error handling:
- Failed CLI commands are logged with return codes
- API errors are logged and returned in the response
- Missing files and import errors are handled gracefully
- Hook execution errors are caught and re-raised with context