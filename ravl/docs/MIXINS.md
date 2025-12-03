# RAVL Mixins Guide

Mixins extend RAVL loops with optional functionality through multiple inheritance.

## Philosophy

**Core principle:** Keep `BaseRAVLLoop` minimal. Add functionality through composable mixins.

**Benefits:**
- Agents only include what they need
- Clear separation of concerns
- Framework vs project-specific code separation
- Easy to test and maintain
- Reusable across projects

## Mixin Types

### Framework Mixins (`.ravl/ravl/common/mixins/`)

Generic, reusable functionality that any RAVL agent might need.

**When to add framework mixins:**
- Used by multiple agents across different projects
- Generic external service integrations (APIs, databases)
- Common utilities (caching, rate limiting, etc.)

### Project Mixins (`ravl_loops/agent_name/mixins/`)

Project-specific functionality for a family of related agents.

**When to add project mixins:**
- Used by multiple agents within same project
- Domain-specific logic (gap management, HR integrations)
- Custom business logic

## Available Framework Mixins

### LLMMixin

**Purpose:** LLM provider detection and JSON extraction utilities

**Location:** `.ravl/ravl/common/mixins/llm_mixin.py`

**Methods:**
- `detect_llm_provider()` - Auto-detect provider from environment
- `extract_json(response_text)` - Extract JSON from LLM responses

**Usage:**
```python
from ravl_base import BaseRAVLLoop
from llm.llm_mixin import LLMMixin

class MyLoop(BaseRAVLLoop, LLMMixin):
    def act(self, reflection):
        provider = self.detect_llm_provider()
        response = provider.generate(prompt, max_tokens=2000)
        data = self.extract_json(response)
        return {'results': data}
```

**Supports:**
- Anthropic Claude
- OpenAI GPT
- Google Gemini
- Ollama (local models)

---

### GoogleAPIsMixin

**Purpose:** Google API integrations

**Location:** `.ravl/ravl/common/mixins/google_apis_mixin.py`

**Services:**
- Google Docs
- Google Slides
- Google Sheets
- Google Workspace Admin SDK

**Methods:**
- `init_google_docs_service()` - Initialize Docs API
- `fetch_google_doc(url)` - Fetch document content
- `init_google_workspace_service()` - Initialize Workspace Admin
- `fetch_workspace_users(...)` - Fetch user directory
- And more...

**Usage:**
```python
from ravl_base import BaseRAVLLoop
from integrations.google_apis_mixin import GoogleAPIsMixin

class MyLoop(BaseRAVLLoop, GoogleAPIsMixin):
    def act(self, reflection):
        self.init_google_docs_service()
        content = self.fetch_google_doc(doc_url)
        return {'content': content}
```

**Lazy Initialization:**
- Services initialized on first use via properties
- No __init__ required
- Credentials from environment (`GOOGLE_APPLICATION_CREDENTIALS`)

---

## Creating New Mixins

### Framework Mixin Template

```python
# .ravl/ravl/common/mixins/my_mixin.py
"""
MyMixin - Brief description

Provides functionality for...
"""

class MyMixin:
    """
    Mixin for...

    Usage:
        class MyLoop(BaseRAVLLoop, MyMixin):
            def act(self, reflection):
                result = self.my_method()
    """

    def my_method(self):
        """Do something useful"""
        pass
```

**Guidelines:**
1. No `__init__` (use lazy properties if needed)
2. Prefix private methods with `_`
3. Include docstrings with usage examples
4. Handle errors gracefully
5. Document environment variables required

---

### Project Mixin Template

```python
# ravl_loops/my_agent/mixins/my_mixin.py
"""
MyMixin - Project-specific functionality

Provides domain-specific logic for...
"""

class MyMixin:
    """
    Project-specific mixin for...

    Usage:
        class MyLoop(BaseRAVLLoop, MyMixin):
            pass
    """

    def project_specific_method(self):
        """Do something specific to this project"""
        pass
```

---

## Multiple Inheritance

### Basic Pattern

```python
class MyLoop(BaseRAVLLoop, LLMMixin, GoogleAPIsMixin):
    """Loop using multiple mixins"""
    pass
```

### Mixin Order

**Always put BaseRAVLLoop first:**
```python
# ✅ Correct
class MyLoop(BaseRAVLLoop, Mixin1, Mixin2):
    pass

# ❌ Wrong
class MyLoop(Mixin1, BaseRAVLLoop, Mixin2):
    pass
```

**Rationale:** Python's Method Resolution Order (MRO) searches left-to-right.

---

## Best Practices

### 1. Keep Mixins Focused

Each mixin should have a single, clear purpose.

**Good:**
```python
class LLMMixin:
    """LLM integrations only"""

class GoogleAPIsMixin:
    """Google APIs only"""
```

**Bad:**
```python
class UtilsMixin:
    """Everything but the kitchen sink"""
```

### 2. Avoid State in Mixins

Use lazy properties for services, avoid instance variables in `__init__`.

**Good:**
```python
class MyMixin:
    @property
    def my_service(self):
        if not hasattr(self, '_my_service'):
            self._my_service = self._init_service()
        return self._my_service
```

**Bad:**
```python
class MyMixin:
    def __init__(self):
        self.my_service = self._init_service()
```

### 3. Document Dependencies

Clearly document required environment variables and packages.

```python
class MyMixin:
    """
    Mixin for X service

    Requirements:
        - Environment: X_API_KEY
        - Package: pip install x-client
    """
```

### 4. Test Independently

Each mixin should be testable without full RAVL loop.

```python
# test_my_mixin.py
from mixins.my_mixin import MyMixin

class TestMyMixin(MyMixin):
    """Test mixin methods independently"""
    pass
```

### 5. Consider Composition Over Inheritance

If mixin becomes too complex, consider extracting to a separate service class.

**When to extract:**
- Mixin > 200 lines
- Complex state management
- Needs independent testing
- Multiple responsibilities

---

## Importing Mixins

### Framework Mixins

```python
import sys
from pathlib import Path

# Find project root
_current = Path(__file__).resolve().parent
while not (_current / '.ravl').exists():
    _current = _current.parent

# Import framework mixins
sys.path.insert(0, str(_current / '.ravl' / 'ravl' / 'common' / 'mixins'))
from llm_mixin import LLMMixin
from google_apis_mixin import GoogleAPIsMixin
```

### Project Mixins

```python
# Import from parent agent's mixins directory
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(parent_dir / 'mixins'))
from my_project_mixin import MyProjectMixin
```

---

## Example: Complete Agent with Mixins

```python
#!/usr/bin/env python3
"""
Example agent using multiple mixins
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Bootstrap: Find .ravl framework
_current = Path(__file__).resolve().parent
while not (_current / '.ravl').exists():
    _current = _current.parent
sys.path.insert(0, str(_current / '.ravl' / 'ravl' / 'common'))

from ravl_base import BaseRAVLLoop

# Import framework mixins
sys.path.insert(0, str(_current / '.ravl' / 'ravl' / 'common' / 'mixins'))
from llm_mixin import LLMMixin
from google_apis_mixin import GoogleAPIsMixin

# Import project mixins
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'mixins'))
from my_project_mixin import MyProjectMixin


class MyAgentLoop(BaseRAVLLoop, LLMMixin, GoogleAPIsMixin, MyProjectMixin):
    """
    Example RAVL loop using multiple mixins
    """

    def __init__(self, model_path: str):
        super().__init__(Path(model_path), loop_name="My Agent")
        self.model = self.load_model_with_timestamp(self._get_default_model)

    def _get_default_model(self) -> Dict[str, Any]:
        return {'version': '1.0', 'learning': {}}

    def reflect(self) -> Dict[str, Any]:
        # Use learned patterns
        return {'timestamp': datetime.now().isoformat()}

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        # Use LLMMixin
        provider = self.detect_llm_provider()
        response = provider.generate("Analyze this...")

        # Use GoogleAPIsMixin
        self.init_google_docs_service()
        doc = self.fetch_google_doc(url)

        # Use ProjectMixin
        result = self.project_specific_method(doc)

        return {'results': result}

    def verify(self, previous, reflection) -> Dict[str, Any]:
        return {'quality_score': 0.9}

    def learn(self, verification, action_result):
        # Update model
        self.save_model_with_timestamp(self.model)
```

---

## Migration Guide

### From ravl_base.py to Mixins

If you're refactoring an agent that used old `ravl_base.py`:

**Before:**
```python
class MyLoop(BaseRAVLLoop):
    def act(self, reflection):
        # ravl_base.py had detect_llm_provider built-in
        provider = self.detect_llm_provider()
```

**After:**
```python
class MyLoop(BaseRAVLLoop, LLMMixin):
    def act(self, reflection):
        # Now from LLMMixin
        provider = self.detect_llm_provider()
```

---

## Troubleshooting

### "Module not found: mixins"

**Problem:** Import path not set up correctly

**Solution:** Add sys.path entry before import:
```python
sys.path.insert(0, str(_current / '.ravl' / 'ravl' / 'common' / 'mixins'))
from llm_mixin import LLMMixin
```

### "AttributeError: 'MyLoop' object has no attribute 'X'"

**Problem:** Service not initialized

**Solution:** Use lazy properties or call init method:
```python
self.init_google_docs_service()
doc = self.fetch_google_doc(url)
```

### "Mixin conflicts"

**Problem:** Multiple mixins define same method

**Solution:** Be explicit about which to use:
```python
class MyLoop(BaseRAVLLoop, Mixin1, Mixin2):
    def method(self):
        # Explicitly call mixin method
        return Mixin1.method(self)
```

---

## See Also

- [RAVL_PROTOCOL.md](RAVL_PROTOCOL.md) - Core RAVL specification
- [README.md](README.md) - Framework overview
- [llm/README.md](llm/README.md) - LLM infrastructure
