# RAVL Library Loops

Delegatable loops with reusable patterns that can be incorporated into projects.

## Available Loops

### `content_coherence`
Validates and ensures consistency across content sources. Useful for documentation management and content quality assurance.

### `google_docs_fetching`
Production-ready Google Workspace document fetching and processing. Handles authentication, rate limiting, and content extraction.

### `data_ingress`
Complete data ingestion pipeline template with API integration, transformation, and validation patterns. Ideal starting point for building API integrations.

## Usage

These loops can be run directly or cloned into your project:

```bash
# Run directly
ravl ravl.library.content_coherence
ravl ravl.library.google_docs_fetching

# Clone into your project
ravl --clone ravl.library.data_ingress my_api_integration
ravl --clone ravl.library.content_coherence my_content_validator
```

## Purpose

Library loops provide production-ready functionality with proven patterns. They may eventually move to a separate library project but are currently maintained as part of the framework for easy access and testing.
