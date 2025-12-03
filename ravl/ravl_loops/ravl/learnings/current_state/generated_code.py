#!/usr/bin/env python3
"""
RAVL Loop: Display available namespaces and their descriptions
Domain: Show user the four main namespace categories with usage examples
"""

print("""
# RAVL Namespaces

RAVL organizes loops into four main namespace categories:

## ravl.framework
**Description:** Core framework loops for RAVL development and maintenance
- Internal framework testing and validation
- Framework feature development loops
- System health monitoring

## ravl.library
**Description:** Reusable loop components and utilities
- Common patterns and building blocks
- Shared utilities for domain-specific tasks
- Pre-built integrations with external services

## ravl.templates
**Description:** Template loops for quick project bootstrapping
- Starter templates for common use cases
- Example implementations of RAVL patterns
- Copy-and-customize foundations

## ravl.examples
**Description:** Example loops demonstrating RAVL capabilities
- Learning resources and tutorials
- Reference implementations
- Best practice demonstrations

## Usage

To run a loop from any namespace, use the qualified name:

```bash
# Run a framework loop
ravl ravl.framework.some-loop

# Run a library component
ravl ravl.library.some-utility

# Bootstrap from a template
ravl ravl.templates.starter-template

# Explore an example
ravl ravl.examples.demo-loop
```

To list all available loops in a namespace:

```bash
# List all loops (shows namespace organization)
ravl --list

# Filter by namespace prefix
ravl --list | grep "ravl.framework"
ravl --list | grep "ravl.library"
ravl --list | grep "ravl.templates"
ravl --list | grep "ravl.examples"
```
""")