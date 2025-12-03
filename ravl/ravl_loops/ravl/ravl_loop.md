# RAVL Framework Namespace

The `ravl.*` namespace contains all framework-provided loops organized by purpose:

## Categories

### `ravl.framework`
Core framework diagnostic and health check tools. These loops are executed as part of framework commands and provide essential system monitoring capabilities.

### `ravl.library`
Delegatable loops with reusable patterns that can be incorporated into projects. These loops provide production-ready functionality and may eventually move to a separate library project.

### `ravl.templates`
Empty starting point templates for cloning new loops. These provide scaffolding for common patterns and help bootstrap new loop development.

### `ravl.examples`
Working demonstration loops that showcase RAVL capabilities. These run out of the box and serve as learning resources and reference implementations.

## Usage

Run framework loops using dot notation:
```bash
# Health checks
ravl ravl.framework.health_checks.execution_health_check
ravl ravl.framework.health_checks.loop_health_check

# Clone from templates or library
ravl --clone ravl.templates.empty_loop my_new_loop
ravl --clone ravl.library.data_ingress my_api_integration

# Run examples
ravl ravl.examples.example_1_single_loop
```
