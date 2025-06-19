# Spacelift Plugins

A monorepo for Spacelift plugins built with the **spaceforge** framework.

## Overview

This repository contains:
- **spaceforge/** - The core Python framework for building Spacelift plugins
- **plugins/wiz/** - Wiz security scanning plugin  
- Plugin management and generation tools

## Quick Start

### Installation

```bash
# Install the spaceforge framework
pip install -e .
```

### Creating a Plugin

1. Create a new directory for your plugin
2. Implement your plugin by inheriting from `SpacepyPlugin`:

```python
from spaceforge import SpaceforgePlugin, Parameter, Variable, Context

class MyPlugin(SpaceforgePlugin):
    __plugin_name__ = "my-plugin"
    __version__ = "1.0.0" 
    __author__ = "Your Name"
    
    # Define parameters using pydantic dataclasses
    __parameters__ = [
        Parameter(
            name="api_key",
            description="API key for authentication",
            required=True,
            sensitive=True
        )
    ]
    
    # Define contexts using pydantic dataclasses
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
            ]
        )
    ]
    
    def after_plan(self):
        self.logger.info("Running after plan hook")
```

3. Generate the plugin YAML:

```bash
python -m spaceforge generate my_plugin.py
```

### Testing Plugins

```bash
# Set plugin parameters
export SPACEFORGE_PARAM_NAME="value"

# Test specific hooks
python -m spaceforge runner after_plan
```

## Architecture

The spaceforge framework uses a hook-based architecture where plugins:
- Inherit from `SpaceforgePlugin` base class
- Override hook methods (`after_plan`, `before_apply`, etc.)  
- Define parameters, contexts, webhooks, and policies using pydantic dataclasses
- Include automatic validation of data structures (e.g., Variables must have either `value` or `value_from_parameter`)
- Are automatically converted to Spacelift plugin YAML format with JSON schema validation

## Available Plugins

- **wiz** - Security scanning plugin for infrastructure as code

## Development

### Commands

```bash
# Generate plugin YAML
python -m spaceforge generate [plugin_file.py] [-o output.yaml]

# Test plugin execution
python -m spaceforge runner [--plugin-file plugin.py] hook_name

# Get help
python -m spaceforge --help
```

### Framework Documentation

See [spaceforge/README.md](spaceforge/README.md) for detailed framework documentation.

## Contributing

1. Create your plugin in a new directory
2. Follow the plugin development patterns shown in existing plugins
3. Generate and test your plugin YAML
4. Submit a pull request

## License

MIT License