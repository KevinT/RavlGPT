# RAVL Templates

This parent loop lists all available RAVL templates for cloning.

## Available Templates

Templates provide starting points for new loops:
- **data_ingress_template**: Self-healing data ingestion from Your API
- **empty_loop_template**: Simple loop - change me in ravl.yml
- **strategic_coherence_template**: Generic parent loop for content coherence

## How to Use Templates

Templates are meant to be cloned, not run directly. To clone a template:

```bash
ravl-clone templates.<template_name> <new_loop_name>
```

Example:
```bash
ravl-clone templates.data_ingress_template my_api_loop
```

This will create a new loop in your project based on the template.
