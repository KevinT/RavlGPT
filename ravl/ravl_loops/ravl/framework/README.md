# RAVL Framework Tools

Core framework diagnostic and health check utilities.

## Loops

### `health_checks`
Health monitoring system for RAVL loops with two specialized checkers:
- `execution_health_check` - Analyzes code generation, DSL stability, and execution patterns
- `loop_health_check` - Analyzes domain learning, model evolution, and verification quality

## Usage

Run health checks via framework commands:
```bash
# Check execution infrastructure
ravl --execution-health <target_loop>

# Check domain learning quality
ravl --loop-health <target_loop>

# Or run directly
ravl ravl.framework.health_checks.execution_health_check
ravl ravl.framework.health_checks.loop_health_check
```

These loops are executed as part of framework operations and provide essential diagnostic capabilities for maintaining loop health.
