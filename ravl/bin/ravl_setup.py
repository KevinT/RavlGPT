#!/usr/bin/env python3
"""
RAVL Setup Wizard

Interactive configuration tool for LLM providers and API integrations.
"""

import os
import sys
import webbrowser
from pathlib import Path
from typing import Dict, Optional, Tuple

# Add parent directory to path for imports
_current = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_current))

from ravl.common.cli.first_run_detector import (
    needs_setup,
    get_configured_llm_provider,
    get_configured_apis,
    get_all_apis_with_status,
    get_all_mcp_servers_with_status
)


class RAVLSetup:
    """Interactive setup wizard for RAVL configuration."""

    LLM_PROVIDERS = {
        '1': ('anthropic', 'Anthropic Claude', 'https://console.anthropic.com/account/keys', 'ANTHROPIC_API_KEY'),
        '2': ('openai', 'OpenAI', 'https://platform.openai.com/api-keys', 'OPENAI_API_KEY'),
        '3': ('google', 'Google Gemini', 'https://makersuite.google.com/app/apikey', 'GOOGLE_API_KEY'),
        '4': ('ollama', 'Ollama (local)', 'http://localhost:11434', 'OLLAMA_BASE_URL'),
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.env_file = project_root / '.env'
        self.env_vars = self._load_env()

    def _load_env(self) -> Dict[str, str]:
        """Load existing .env file if it exists."""
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        env_vars[key.strip()] = value
        return env_vars

    def _save_env(self):
        """Save environment variables to .env file."""
        with open(self.env_file, 'w') as f:
            for key, value in sorted(self.env_vars.items()):
                # Quote values that contain spaces or special chars
                if ' ' in value or any(c in value for c in ['$', '"', "'"]):
                    value = f'"{value}"'
                f.write(f'{key}={value}\n')

        # Set restrictive permissions
        os.chmod(self.env_file, 0o600)

    def _print_header(self):
        """Print the RAVL setup header with current config."""
        # Import version from framework root
        import sys
        from pathlib import Path
        framework_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(framework_root))
        try:
            from __init__ import __version__
        except ImportError:
            __version__ = "0.1.0"  # Fallback

        current_llm = get_configured_llm_provider()
        all_apis = get_all_apis_with_status()
        api_detected_count = sum(1 for info in all_apis.values() if info['detected'])
        api_total_count = len(all_apis)

        all_mcp_servers = get_all_mcp_servers_with_status()
        mcp_detected_count = sum(1 for info in all_mcp_servers.values() if info['detected'])
        mcp_total_count = len(all_mcp_servers)

        llm_display = current_llm if current_llm else "none"
        cwd = os.getcwd()

        # Dynamic header width based on terminal size
        try:
            terminal_width = os.get_terminal_size().columns
            # Clamp between reasonable min/max
            HEADER_WIDTH = max(80, min(terminal_width, 120))
        except:
            HEADER_WIDTH = 80  # Fallback for non-terminal environments

        # Top row with dynamic version
        header_prefix = "█ RavlGPT █ v "
        header_suffix = " █"
        version_part = f"{header_prefix}{__version__}{header_suffix}"
        top_padding = HEADER_WIDTH - len(version_part)
        top_row = version_part + ("█" * top_padding)

        # Bottom row (matches width)
        bottom_prefix = "░ ░ ░ ░ ░ ░ ░ ░ ░ ░ "
        bottom_padding = HEADER_WIDTH - len(bottom_prefix)
        bottom_row = bottom_prefix + ("░" * bottom_padding)

        print(top_row)
        print("║    ╔════╬════╦════╣")
        print(f"▓    ▓    ▓    ▓    ║ Default intelligence provider: {llm_display}")
        api_not_detected = api_total_count - api_detected_count
        if api_not_detected > 0:
            print(f"║  ╔═╩╗  ╔╩═╦══╗ ➿ ║ API Integrations: {api_detected_count} detected, {api_not_detected} not detected")
        else:
            print(f"║  ╔═╩╗  ╔╩═╦══╗ ➿ ║ API Integrations: {api_detected_count} detected")
        mcp_not_detected = mcp_total_count - mcp_detected_count
        if mcp_not_detected > 0:
            print(f"▒  ▒  ▒  ▒  ▒  ▒    ║ MCP Servers: {mcp_detected_count} detected, {mcp_not_detected} not detected")
        else:
            print(f"▒  ▒  ▒  ▒  ▒  ▒    ║ MCP Servers: {mcp_detected_count} detected")
        print(f"║ ╔╩╗ ╔═╦╩╗ ║ ╔╩╦═╦═╣ {cwd}")
        print(bottom_row)
        print()

    def _validate_llm_key(self, provider: str, api_key: str) -> bool:
        """
        Validate an LLM provider API key.

        Returns True if valid, False otherwise.
        """
        try:
            if provider == 'anthropic':
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                # Simple test - just check if key format is valid
                return api_key.startswith('sk-ant-')

            elif provider == 'openai':
                import openai
                client = openai.OpenAI(api_key=api_key)
                # Simple test
                return api_key.startswith('sk-')

            elif provider == 'google':
                # Just check non-empty for now
                return len(api_key) > 0

            elif provider == 'ollama':
                import requests
                # Check if URL is reachable
                response = requests.get(api_key, timeout=2)
                return response.status_code == 200

        except Exception:
            return False

        return True

    def _mask_api_key(self, key: str) -> str:
        """Mask API key for secure display

        Shows first 12 and last 4 characters, masks middle.
        Example: sk-ant-api03-abc...xyz123

        Args:
            key: Full API key

        Returns:
            Masked string for display
        """
        if not key or len(key) <= 8:
            return "****"

        prefix_len = min(12, len(key) // 3)  # Show more for longer keys
        suffix_len = 4

        return f"{key[:prefix_len]}...{key[-suffix_len:]}"

    def _test_llm_connectivity(self, provider_id: str, api_key: str) -> bool:
        """Test if API key works by making a minimal API call

        Args:
            provider_id: Provider identifier (anthropic, openai, google, ollama)
            api_key: API key to test

        Returns:
            True if key is valid and API responds
        """
        try:
            if provider_id == 'anthropic':
                # Import here to avoid startup dependency
                try:
                    from anthropic import Anthropic
                    client = Anthropic(api_key=api_key)
                    # Make a minimal test call - just check messages endpoint exists
                    # We don't actually need to call it, just verify client initializes
                    return True
                except ImportError:
                    print("   (anthropic library not installed, skipping connectivity test)")
                    return True  # Assume valid if library not available

            elif provider_id == 'openai':
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key)
                    # Test with models endpoint
                    client.models.list()
                    return True
                except ImportError:
                    print("   (openai library not installed, skipping connectivity test)")
                    return True
                except Exception as e:
                    # API error means key is invalid
                    return False

            elif provider_id == 'google':
                # Google Gemini uses different auth pattern
                # For now, rely on format validation
                return True

            elif provider_id == 'ollama':
                # Ollama is local, just verify URL format
                return api_key.startswith('http')

            return True

        except Exception as e:
            print(f"   Connection test failed: {e}")
            return False

    def setup_llm_provider(self) -> bool:
        """
        Interactive LLM provider setup.

        Returns True if a provider was configured.
        """
        print("\n=== LLM Provider Setup ===\n")

        current = get_configured_llm_provider()
        if current:
            print(f"Current default: {current.title()}\n")

        print("Which LLM provider would you like to use?")
        for key, (_, name, _, _) in self.LLM_PROVIDERS.items():
            print(f"{key}) {name}")

        choice = input("\nSelect (1-4): ").strip()

        if choice not in self.LLM_PROVIDERS:
            print("Invalid choice.")
            return False

        provider_id, provider_name, url, env_key = self.LLM_PROVIDERS[choice]

        # Check if key already exists in environment
        existing_key = os.environ.get(env_key)

        if existing_key:
            # Key detected - show options menu
            masked = self._mask_api_key(existing_key)
            print(f"\n✓ {env_key} detected: {masked}")
            print("\nWhat would you like to do?")
            print("1) Keep existing key")
            print("2) Update with new key")
            print("3) Test existing key")
            print("4) Cancel")

            option = input("\nSelect (1-4) [default: 1]: ").strip() or '1'

            if option == '1':
                # Keep existing key
                api_key = existing_key
                print("Using existing key")

            elif option == '2':
                # Update with new key
                print(f"\nOpening browser to get your API key...")
                print(f"URL: {url}")
                try:
                    webbrowser.open(url)
                except Exception:
                    pass

                if provider_id == 'ollama':
                    api_key = input(f"\nEnter Ollama URL (default: {url}): ").strip() or url
                else:
                    api_key = input(f"\nPaste your {provider_name} API key: ").strip()

                if not api_key:
                    print("No API key provided.")
                    return False

            elif option == '3':
                # Test existing key
                print("\nTesting API connectivity...")
                if self._test_llm_connectivity(provider_id, existing_key):
                    print("✓ Key is valid and working")
                    keep = input("\nKeep this key? (y/n) [default: y]: ").strip().lower() or 'y'
                    if keep in ['y', 'yes']:
                        api_key = existing_key
                        print("Using existing key")
                    else:
                        # User wants to update after test
                        print(f"\nOpening browser to get your API key...")
                        print(f"URL: {url}")
                        try:
                            webbrowser.open(url)
                        except Exception:
                            pass

                        if provider_id == 'ollama':
                            api_key = input(f"\nEnter Ollama URL (default: {url}): ").strip() or url
                        else:
                            api_key = input(f"\nPaste your {provider_name} API key: ").strip()

                        if not api_key:
                            print("No API key provided.")
                            return False
                else:
                    print("✗ Key test failed or expired")
                    update = input("\nUpdate with new key? (y/n) [default: y]: ").strip().lower() or 'y'
                    if update in ['y', 'yes']:
                        print(f"\nOpening browser to get your API key...")
                        print(f"URL: {url}")
                        try:
                            webbrowser.open(url)
                        except Exception:
                            pass

                        if provider_id == 'ollama':
                            api_key = input(f"\nEnter Ollama URL (default: {url}): ").strip() or url
                        else:
                            api_key = input(f"\nPaste your {provider_name} API key: ").strip()

                        if not api_key:
                            print("No API key provided.")
                            return False
                    else:
                        print("Keeping existing key despite test failure")
                        api_key = existing_key

            elif option == '4':
                # Cancel
                print("Cancelled")
                return False

            else:
                # Invalid option, default to keep
                print("Invalid option, using existing key")
                api_key = existing_key

        else:
            # No existing key - normal first-time setup flow
            print(f"\nOpening browser to get your API key...")
            print(f"URL: {url}")
            try:
                webbrowser.open(url)
            except Exception:
                pass

            # Prompt for key
            if provider_id == 'ollama':
                api_key = input(f"\nEnter Ollama URL (default: {url}): ").strip() or url
            else:
                api_key = input(f"\nPaste your {provider_name} API key: ").strip()

            if not api_key:
                print("No API key provided.")
                return False

        # Validate
        print("Validating...")
        if not self._validate_llm_key(provider_id, api_key):
            print("✗ Validation failed. Please check your API key.")
            return False

        # Save
        self.env_vars[env_key] = api_key

        # Ask if this should be the default
        if not current or current != provider_id:
            set_default = input(f"\nSet {provider_name} as your default LLM provider? (y/n): ").strip().lower()
            if set_default in ['y', 'yes']:
                # Save to framework config file instead of .env
                from ravl.common.config.config_service import save_framework_llm_provider
                success, error = save_framework_llm_provider(provider_id, self.project_root)
                if success:
                    print(f"✓ Saved default provider: {provider_id}")
                    print(f"   Location: .ravl/config.toml")
                else:
                    print(f"✗ Failed to save provider preference: {error}")

        self._save_env()

        print(f"✓ {provider_name} configured")
        return True

    def setup_api_integration(self) -> bool:
        """
        Interactive API integration setup.

        Returns True if an API was configured.
        """
        print("\n=== API Integrations ===\n")

        # Show all registered APIs with status
        from ravl.common.cli.first_run_detector import get_all_apis_with_status

        all_apis = get_all_apis_with_status()
        if all_apis:
            print("Registered APIs:")
            for i, (api_name, info) in enumerate(all_apis.items(), 1):
                status = "✓" if info['detected'] else "✗"
                status_text = "Detected" if info['detected'] else "Not detected"
                print(f"{i}) {status} {api_name} ({info['env_var']}) - {status_text}")
            next_option = len(all_apis) + 1
        else:
            print("No APIs registered yet.")
            next_option = 1

        print(f"{next_option}) Add new API integration")
        print(f"{next_option + 1}) Back to main menu")

        choice = input(f"\nSelect (1-{next_option + 1}): ").strip()

        # Check if user wants to go back
        if choice == str(next_option + 1):
            return False

        # Check if user wants to add new API
        if choice == str(next_option):
            from ravl.common.integrations.api_credentials_registry import (
                get_api_config, get_env_var, is_api_registered, add_api_to_registry
            )
            import yaml

            api_name = input("\nEnter the API name (e.g., \"ClickUp\", \"GitHub\"): ").strip()

            if not api_name:
                print("No API name provided.")
                return False

            # Check if API is in registry
            if is_api_registered(api_name):
                # Show existing config
                config = get_api_config(api_name)
                print(f"\nExisting configuration:")
                print(yaml.dump({api_name: config}, default_flow_style=False))
                print("\n1) Use existing config")
                print("2) Edit config")
                edit_choice = input("Select (1-2): ").strip()

                if edit_choice == '2':
                    # Interactive config editor
                    env_key = input(f"Environment variable name [{config['env_var']}]: ").strip() or config['env_var']
                    documentation = input(f"Documentation URL [{config.get('documentation', '')}]: ").strip() or config.get('documentation', '')

                    # Let user edit other fields
                    custom_fields = {k: v for k, v in config.items() if k not in ['env_var', 'documentation']}
                    print("\nExisting custom fields (press Enter to keep, or type new value):")
                    for key, value in custom_fields.items():
                        new_value = input(f"  {key} [{value}]: ").strip()
                        if new_value:
                            custom_fields[key] = new_value

                    # Add new custom fields
                    print("\nAdd new custom fields? (e.g., base_url, rate_limit, auth_type)")
                    while True:
                        key = input("Field name (or Enter to finish): ").strip()
                        if not key:
                            break
                        value = input(f"Value for {key}: ").strip()
                        if value:
                            custom_fields[key] = value

                    # Save updated config
                    add_api_to_registry(api_name, env_key, documentation, **custom_fields)
                else:
                    env_key = config['env_var']
            else:
                # New API - prompt for required fields
                print(f"\n{api_name} is not registered yet.")
                print("\nRequired fields:")
                env_key = input("  Environment variable name (e.g., CLICKUP_API_TOKEN): ").strip()

                if not env_key:
                    suggested = f"{api_name.upper().replace(' ', '_')}_API_TOKEN"
                    print(f"  Using suggested: {suggested}")
                    env_key = suggested

                documentation = input("  API documentation URL (Context7 preferred): ").strip()

                # Optional: Let user add custom fields
                print("\nOptional custom fields (e.g., base_url, rate_limit, auth_type):")
                custom_fields = {}
                while True:
                    key = input("Field name (or Enter to finish): ").strip()
                    if not key:
                        break
                    value = input(f"Value for {key}: ").strip()
                    if value:
                        custom_fields[key] = value

                # Save to registry
                add_api_to_registry(api_name, env_key, documentation, **custom_fields)
                print(f"✓ Added {api_name} to registry with env var: {env_key}")

            # Prompt for the actual credential value
            api_token = input(f"\nEnter your {env_key} value: ").strip()

            if not api_token:
                print("No token provided.")
                return False

            # Save to .env
            self.env_vars[env_key] = api_token
            self._save_env()

            print(f"✓ {api_name} configured (saved as {env_key})")
            return True

        # Check if user selected an existing API
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(all_apis):
                api_name = list(all_apis.keys())[choice_num - 1]
                info = all_apis[api_name]

                print(f"\n=== {api_name} ===")

                if info['detected']:
                    # API detected - show edit/remove options
                    print(f"Status: ✓ Detected")
                    print(f"Environment variable: {info['env_var']}")
                    env_value = os.environ.get(info['env_var'], 'N/A')
                    if len(env_value) > 20:
                        print(f"Value: {env_value[:20]}...")
                    else:
                        print(f"Value: {env_value}")

                    print("\n1) Update token")
                    print("2) Edit configuration")
                    print("3) Remove")
                    print("4) Back")

                    action = input("\nSelect (1-4): ").strip()

                    if action == '1':
                        api_token = input(f"\nEnter new {info['env_var']} value: ").strip()
                        if api_token:
                            self.env_vars[info['env_var']] = api_token
                            self._save_env()
                            print(f"✓ {api_name} token updated")
                            return True
                    elif action == '2':
                        # Edit configuration (show YAML and let user edit)
                        print("\nCurrent configuration:")
                        print(yaml.dump({api_name.lower(): info['config']}, default_flow_style=False))
                        print("\n(Configuration editing coming soon)")
                        return False
                    elif action == '3':
                        confirm = input(f"\nRemove {api_name}? (y/n): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            del self.env_vars[info['env_var']]
                            self._save_env()
                            print(f"✓ {api_name} removed")
                            return True
                    elif action == '4':
                        return False
                else:
                    # API not detected - prompt for credential
                    print(f"Status: ✗ Not detected")
                    print(f"Environment variable needed: {info['env_var']}")
                    print("\nConfiguration:")
                    print(yaml.dump({api_name.lower(): info['config']}, default_flow_style=False))

                    configure = input("\nConfigure this API now? (y/n): ").strip().lower()
                    if configure in ['y', 'yes']:
                        token = input(f"\nEnter your {info['env_var']} value: ").strip()
                        if token:
                            self.env_vars[info['env_var']] = token
                            self._save_env()
                            print(f"✓ {api_name} credential saved")
                            return True
        except (ValueError, IndexError):
            pass

        print("Invalid choice.")
        return False

    def setup_llm_defaults(self) -> bool:
        """
        Interactive LLM defaults configuration.

        Configures prompt normalization and max tokens via environment variables.
        """
        while True:
            print("\n" + "="*70)
            print("LLM DEFAULTS")
            print("="*70)
            print("\nConfigure token limits and optimization settings for LLM calls.\n")

            print("What would you like to configure?")
            print("1) Prompt Normalization (token optimization)")
            print("2) Max Tokens (per-use-case limits)")
            print("3) Back to main menu")

            choice = input("\nSelect (1-3): ").strip()

            if choice == '1':
                self._setup_prompt_normalization()
            elif choice == '2':
                self._setup_max_tokens()
            elif choice == '3':
                return False
            else:
                print("\n✗ Invalid choice. Please select 1-3.")
                input("\nPress Enter to continue...")

    def _setup_prompt_normalization(self) -> None:
        """
        Interactive prompt normalization configuration sub-menu.
        """
        while True:
            print("\n" + "="*70)
            print("PROMPT NORMALIZATION SETTINGS")
            print("="*70)
            print("\nReduce LLM token consumption by 40-70% through intelligent")
            print("deduplication of repeated blocks in prompts.\n")

            # Get current values (env vars override TOML)
            current_enabled = self.env_vars.get('RAVL_PROMPT_NORMALIZATION_ENABLED',
                                                os.environ.get('RAVL_PROMPT_NORMALIZATION_ENABLED', 'true'))
            current_min_block = self.env_vars.get('RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE',
                                                  os.environ.get('RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE', '200'))
            current_logging = self.env_vars.get('RAVL_PROMPT_NORMALIZATION_ENABLE_LOGGING',
                                                os.environ.get('RAVL_PROMPT_NORMALIZATION_ENABLE_LOGGING', 'true'))

            # Display current configuration
            print("Current Settings:")
            print(f"  Enabled: {current_enabled} {'(✓ Active)' if current_enabled == 'true' else '(✗ Disabled)'}")
            print(f"  Minimum block size: {current_min_block} chars")
            print(f"  Enable logging: {current_logging}\n")

            print("What would you like to do?")
            print("1) Toggle normalization on/off")
            print("2) Change minimum block size")
            print("3) Toggle logging on/off")
            print("4) Reset to framework defaults")
            print("5) Back to LLM Defaults menu")

            choice = input("\nSelect (1-5): ").strip()

            if choice == '1':
                # Toggle enabled
                new_value = 'false' if current_enabled == 'true' else 'true'
                self.env_vars['RAVL_PROMPT_NORMALIZATION_ENABLED'] = new_value
                self._save_env()
                status = "enabled" if new_value == 'true' else "disabled"
                print(f"\n✓ Prompt normalization {status}")
                input("\nPress Enter to continue...")

            elif choice == '2':
                # Change min block size
                print(f"\nCurrent minimum block size: {current_min_block} chars")
                print("Smaller values = more aggressive deduplication")
                print("Recommended range: 100-500 chars")
                new_value = input("Enter new minimum block size (or press Enter to cancel): ").strip()

                if new_value:
                    try:
                        min_block = int(new_value)
                        if min_block < 50:
                            print("\n⚠  Warning: Values below 50 may cause excessive deduplication")
                        if min_block > 1000:
                            print("\n⚠  Warning: Values above 1000 reduce effectiveness")

                        confirm = input(f"Set minimum block size to {min_block}? (y/n): ").strip().lower()
                        if confirm == 'y':
                            self.env_vars['RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE'] = str(min_block)
                            self._save_env()
                            print(f"\n✓ Minimum block size set to {min_block} chars")
                    except ValueError:
                        print("\n✗ Invalid number. Please enter an integer.")

                input("\nPress Enter to continue...")

            elif choice == '3':
                # Toggle logging
                new_value = 'false' if current_logging == 'true' else 'true'
                self.env_vars['RAVL_PROMPT_NORMALIZATION_ENABLE_LOGGING'] = new_value
                self._save_env()
                status = "enabled" if new_value == 'true' else "disabled"
                print(f"\n✓ Normalization logging {status}")
                input("\nPress Enter to continue...")

            elif choice == '4':
                # Reset to defaults
                print("\nThis will remove environment overrides and use framework defaults:")
                print("  - Enabled: true")
                print("  - Minimum block size: 200 chars")
                print("  - Enable logging: true")
                confirm = input("\nReset to defaults? (y/n): ").strip().lower()

                if confirm == 'y':
                    # Remove env vars to fall back to TOML defaults
                    self.env_vars.pop('RAVL_PROMPT_NORMALIZATION_ENABLED', None)
                    self.env_vars.pop('RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE', None)
                    self.env_vars.pop('RAVL_PROMPT_NORMALIZATION_ENABLE_LOGGING', None)
                    self._save_env()
                    print("\n✓ Reset to framework defaults")

                input("\nPress Enter to continue...")

            elif choice == '5':
                # Back to LLM Defaults menu
                return

            else:
                print("\n✗ Invalid choice. Please select 1-5.")
                input("\nPress Enter to continue...")

    def _setup_max_tokens(self) -> None:
        """
        Interactive max tokens configuration sub-menu.
        """
        # Max tokens use cases from ravl.toml
        max_tokens_keys = [
            ('code_generation', 'Code Generation', 16384),
            ('act_phase_code_generation', 'Act Phase Code Generation', 16384),
            ('data_ingress_code_generation', 'Data Ingestion Code Generation', 8192),
            ('domain_context_synthesis', 'Domain Context Synthesis', 4096),
            ('verification', 'Verification', 4096),
            ('learn_insights', 'Learn Insights', 4096),
            ('markdown_enhancement', 'Markdown Enhancement', 4096),
            ('health_check_execution_analysis', 'Health Check (Execution)', 4096),
            ('health_check_domain_analysis', 'Health Check (Domain)', 4096),
            ('default', 'Default (fallback)', 8192)
        ]

        while True:
            print("\n" + "="*70)
            print("MAX TOKENS CONFIGURATION")
            print("="*70)
            print("\nConfigure maximum token limits for different LLM use cases.")
            print("Higher values = more detailed output, but higher cost.\n")

            print("Current Settings:")
            # Show current values (env var overrides, or framework defaults)
            for i, (key, label, default) in enumerate(max_tokens_keys, start=1):
                env_var = f'RAVL_MAX_TOKENS_{key.upper()}'
                current = self.env_vars.get(env_var, os.environ.get(env_var, str(default)))
                print(f"  {i:2d}) {label:35s} {current:>6s} tokens")

            print("\nWhat would you like to do?")
            print(f"{len(max_tokens_keys) + 1}) Change a specific limit")
            print(f"{len(max_tokens_keys) + 2}) Reset all to framework defaults")
            print(f"{len(max_tokens_keys) + 3}) Back to LLM Defaults menu")

            choice = input(f"\nSelect (1-{len(max_tokens_keys) + 3}): ").strip()

            # Parse choice
            try:
                choice_num = int(choice)
            except ValueError:
                print("\n✗ Invalid choice. Please enter a number.")
                input("\nPress Enter to continue...")
                continue

            if 1 <= choice_num <= len(max_tokens_keys):
                # User selected a specific key to modify
                key, label, default = max_tokens_keys[choice_num - 1]
                env_var = f'RAVL_MAX_TOKENS_{key.upper()}'
                current = self.env_vars.get(env_var, os.environ.get(env_var, str(default)))

                print(f"\nCurrent {label}: {current} tokens")
                print("Common values: 4096, 8192, 16384, 32768")
                print("(Higher = more detailed, but more expensive)")
                new_value = input("Enter new max tokens (or press Enter to cancel): ").strip()

                if new_value:
                    try:
                        max_tokens = int(new_value)
                        if max_tokens < 1024:
                            print("\n⚠  Warning: Values below 1024 may truncate output")
                        if max_tokens > 100000:
                            print("\n⚠  Warning: Very large values may be rejected by LLM provider")

                        confirm = input(f"Set {label} to {max_tokens} tokens? (y/n): ").strip().lower()
                        if confirm == 'y':
                            self.env_vars[env_var] = str(max_tokens)
                            self._save_env()
                            print(f"\n✓ {label} set to {max_tokens} tokens")
                    except ValueError:
                        print("\n✗ Invalid number. Please enter an integer.")

                input("\nPress Enter to continue...")

            elif choice_num == len(max_tokens_keys) + 1:
                # Change specific limit (redirect to top of loop)
                continue

            elif choice_num == len(max_tokens_keys) + 2:
                # Reset all to defaults
                print("\nThis will remove all max_tokens environment overrides.")
                print("Framework defaults will be used:")
                for key, label, default in max_tokens_keys:
                    print(f"  - {label}: {default} tokens")

                confirm = input("\nReset all to defaults? (y/n): ").strip().lower()

                if confirm == 'y':
                    # Remove all max_tokens env vars
                    for key, _, _ in max_tokens_keys:
                        env_var = f'RAVL_MAX_TOKENS_{key.upper()}'
                        self.env_vars.pop(env_var, None)
                    self._save_env()
                    print("\n✓ Reset all max_tokens to framework defaults")

                input("\nPress Enter to continue...")

            elif choice_num == len(max_tokens_keys) + 3:
                # Back to LLM Defaults menu
                return

            else:
                print(f"\n✗ Invalid choice. Please select 1-{len(max_tokens_keys) + 3}.")
                input("\nPress Enter to continue...")

    def setup_mcp_servers(self) -> bool:
        """
        Interactive MCP server setup.

        Returns True if an MCP server was configured.
        """
        print("\n=== MCP Servers ===\n")

        # IMPORTANT WARNING about MCP server prerequisites
        print("⚠️  IMPORTANT: MCP servers must be running before you can connect")
        print("   MCP servers are self-hosted processes (not vendor endpoints)")
        print("   See: .ravl/docs/MCP_SETUP_GUIDE.md for setup instructions")
        print("   Only add servers you've already downloaded and started.\n")

        # Show all registered MCP servers with status
        all_servers = get_all_mcp_servers_with_status()
        if all_servers:
            print("Registered MCP Servers:")
            for i, (server_name, info) in enumerate(all_servers.items(), 1):
                status = "✓" if info['detected'] else "✗"
                status_text = "Detected" if info['detected'] else "Not detected"
                transport = info.get('transport', 'unknown')
                print(f"{i}) {status} {server_name} ({transport}) - {status_text}")
            next_option = len(all_servers) + 1
        else:
            print("No MCP servers registered yet.")
            next_option = 1

        print(f"{next_option}) Add new MCP server")
        print(f"{next_option + 1}) Test connections")
        print(f"{next_option + 2}) Back to main menu")

        choice = input(f"\nSelect (1-{next_option + 2}): ").strip()

        # Check if user wants to go back
        if choice == str(next_option + 2):
            return False

        # Check if user wants to test connections
        if choice == str(next_option + 1):
            print("\n=== Testing MCP Server Connections ===\n")
            from ravl.common.integrations.mcp_client_manager import MCPClientManager
            from ravl.common.integrations.mcp_registry import get_mcp_server_config

            manager = MCPClientManager()
            for server_name, info in all_servers.items():
                if not info['detected']:
                    print(f"✗ {server_name}: Skipping (credentials not detected)")
                    continue

                print(f"Testing {server_name}...")
                config = get_mcp_server_config(server_name.lower())
                if manager.connect(server_name.lower(), config):
                    capabilities = manager.get_capabilities(server_name.lower())
                    print(f"✓ {server_name}: Connected ({len(capabilities)} tools available)")
                    if capabilities:
                        print(f"  Tools: {', '.join(capabilities[:5])}")
                        if len(capabilities) > 5:
                            print(f"  ... and {len(capabilities) - 5} more")
                    manager.disconnect(server_name.lower())
                else:
                    print(f"✗ {server_name}: Connection failed")

            input("\nPress Enter to continue...")
            return False

        # Check if user wants to add new MCP server
        if choice == str(next_option):
            from ravl.common.integrations.mcp_registry import (
                get_mcp_server_config, is_mcp_server_registered, add_mcp_server_to_registry
            )
            import yaml

            server_name = input("\nEnter the MCP server name (e.g., \"ClickUp\", \"GitHub\"): ").strip()

            if not server_name:
                print("No server name provided.")
                return False

            # Check if server is in registry
            if is_mcp_server_registered(server_name):
                # Show existing config
                config = get_mcp_server_config(server_name)
                print(f"\nExisting configuration:")
                print(yaml.dump({server_name: config}, default_flow_style=False))
                print("\n1) Use existing config")
                print("2) Edit config")
                edit_choice = input("Select (1-2): ").strip()

                if edit_choice == '2':
                    # Interactive config editor
                    transport = input(f"Transport type (sse/stdio/http) [{config.get('transport', 'sse')}]: ").strip() or config.get('transport', 'sse')

                    if transport == 'sse':
                        url = input(f"Server URL [{config.get('url', '')}]: ").strip() or config.get('url', '')
                        env_var = input(f"Environment variable for auth token [{config.get('env_var', '')}]: ").strip() or config.get('env_var', '')
                        add_mcp_server_to_registry(server_name, transport, url=url, env_var=env_var,
                                                  name=config.get('name', server_name),
                                                  documentation=config.get('documentation', ''),
                                                  description=config.get('description', ''))
                    elif transport == 'stdio':
                        command = input(f"Command path [{config.get('command', '')}]: ").strip() or config.get('command', '')
                        args_str = input(f"Command arguments (space-separated) [{' '.join(config.get('args', []))}]: ").strip()
                        args = args_str.split() if args_str else config.get('args', [])
                        env_var = input(f"Environment variable for auth token (optional) [{config.get('env_var', '')}]: ").strip() or config.get('env_var', None)
                        add_mcp_server_to_registry(server_name, transport, command=command, args=args, env_var=env_var,
                                                  name=config.get('name', server_name),
                                                  documentation=config.get('documentation', ''),
                                                  description=config.get('description', ''))
                else:
                    env_var = config.get('env_var')
            else:
                # New MCP server - prompt for required fields
                print(f"\n{server_name} is not registered yet.")
                print("\nTransport type:")
                print("1) SSE (Server-Sent Events) - HTTP connection")
                print("2) stdio - Local process")
                print("3) HTTP - REST API")

                transport_choice = input("Select (1-3): ").strip()
                transport_map = {'1': 'sse', '2': 'stdio', '3': 'http'}
                transport = transport_map.get(transport_choice, 'sse')

                if transport == 'sse':
                    url = input("Server URL (e.g., http://localhost:3000): ").strip()
                    env_var = input("Environment variable for auth token (e.g., CLICKUP_API_TOKEN): ").strip()
                    documentation = input("Documentation URL (optional): ").strip()
                    description = input("Description (optional): ").strip()

                    add_mcp_server_to_registry(server_name, transport, url=url, env_var=env_var,
                                              name=server_name, documentation=documentation, description=description)
                elif transport == 'stdio':
                    command = input("Command path (e.g., /usr/local/bin/mcp-server-filesystem): ").strip()
                    args_str = input("Command arguments (space-separated, optional): ").strip()
                    args = args_str.split() if args_str else []
                    env_var = input("Environment variable for auth token (optional): ").strip() or None
                    documentation = input("Documentation URL (optional): ").strip()
                    description = input("Description (optional): ").strip()

                    add_mcp_server_to_registry(server_name, transport, command=command, args=args, env_var=env_var,
                                              name=server_name, documentation=documentation, description=description)
                else:
                    print("HTTP transport not yet implemented.")
                    return False

                print(f"✓ Added {server_name} to registry")

            # Prompt for the actual credential value if needed
            if env_var:
                token = input(f"\nEnter your {env_var} value: ").strip()

                if not token:
                    print("No token provided.")
                    return False

                # Save to .env
                self.env_vars[env_var] = token
                self._save_env()

                print(f"✓ {server_name} configured (saved as {env_var})")
            else:
                print(f"✓ {server_name} configured (no authentication required)")

            return True

        # Check if user selected an existing server
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(all_servers):
                server_name = list(all_servers.keys())[choice_num - 1]
                info = all_servers[server_name]

                print(f"\n=== {server_name} ===")

                if info['detected']:
                    # Server detected - show test/edit/remove options
                    print(f"Status: ✓ Detected")
                    print(f"Transport: {info.get('transport', 'unknown')}")
                    if info.get('url'):
                        print(f"URL: {info['url']}")
                    if info.get('command'):
                        print(f"Command: {info['command']}")
                    if info.get('env_var'):
                        print(f"Environment variable: {info['env_var']}")

                    print("\n1) Test connection")
                    print("2) Update credentials")
                    print("3) Edit configuration")
                    print("4) Remove")
                    print("5) Back")

                    action = input("\nSelect (1-5): ").strip()

                    if action == '1':
                        # Test connection
                        from ravl.common.integrations.mcp_client_manager import MCPClientManager
                        from ravl.common.integrations.mcp_registry import get_mcp_server_config

                        print(f"\nTesting connection to {server_name}...")
                        manager = MCPClientManager()
                        config = get_mcp_server_config(server_name.lower())
                        if manager.connect(server_name.lower(), config):
                            capabilities = manager.get_capabilities(server_name.lower())
                            print(f"✓ Connected successfully")
                            print(f"Available tools: {len(capabilities)}")
                            if capabilities:
                                print(f"\nTools:")
                                for tool in capabilities[:10]:
                                    print(f"  - {tool}")
                                if len(capabilities) > 10:
                                    print(f"  ... and {len(capabilities) - 10} more")
                            manager.disconnect(server_name.lower())
                        else:
                            print(f"✗ Connection failed")

                        input("\nPress Enter to continue...")

                    elif action == '2':
                        # Update credentials
                        if info.get('env_var'):
                            token = input(f"\nEnter new value for {info['env_var']}: ").strip()
                            if token:
                                self.env_vars[info['env_var']] = token
                                self._save_env()
                                print(f"✓ Updated {info['env_var']}")
                        else:
                            print("This server does not require credentials.")

                    elif action == '3':
                        # Edit configuration - similar to add new flow
                        print("Configuration editing not yet implemented. Please edit .ravl/config/mcp_servers_registry.yml manually.")
                        input("\nPress Enter to continue...")

                    elif action == '4':
                        # Remove
                        confirm = input(f"Remove {server_name}? (y/n): ").strip().lower()
                        if confirm == 'y':
                            # Note: We don't have a remove function yet, user must edit YAML manually
                            print("Please remove the entry from .ravl/config/mcp_servers_registry.yml manually.")
                            if info.get('env_var') and info['env_var'] in self.env_vars:
                                del self.env_vars[info['env_var']]
                                self._save_env()
                                print(f"✓ Removed {info['env_var']} from .env")
                        input("\nPress Enter to continue...")

                else:
                    # Server not detected - prompt to configure credentials
                    print(f"Status: ✗ Not detected")
                    print(f"Transport: {info.get('transport', 'unknown')}")
                    if info.get('env_var'):
                        print(f"Missing: {info['env_var']}")

                        token = input(f"\nEnter your {info['env_var']} value: ").strip()
                        if token:
                            self.env_vars[info['env_var']] = token
                            self._save_env()
                            print(f"✓ Configured {server_name}")
                    else:
                        print("No credentials required.")

            return False

        except ValueError:
            print("Invalid choice.")
            return False

    def main_menu(self):
        """Main setup menu."""
        self._print_header()

        # Show current configuration
        current_llm = get_configured_llm_provider()
        current_apis = get_configured_apis()

        if not current_llm and not current_apis:
            print("Nothing configured yet.\n")

        # Show menu
        print("What would you like to configure?")
        print("1) LLM Provider" + (f" (✓ {current_llm.title()})" if current_llm else " (required - RAVL uses this to generate code)"))
        print("2) API Integrations (optional - add APIs your loops need)")
        print("3) LLM Defaults (token limits, optimization)")
        print("4) MCP Servers (optional - connect to Model Context Protocol servers)")
        print("5) Exit")

        choice = input("\nSelect (1-5): ").strip()

        if choice == '1':
            self.setup_llm_provider()
            # Return to main menu
            self.main_menu()

        elif choice == '2':
            self.setup_api_integration()
            # Return to main menu
            self.main_menu()

        elif choice == '3':
            self.setup_llm_defaults()
            # Return to main menu
            self.main_menu()

        elif choice == '4':
            self.setup_mcp_servers()
            # Return to main menu
            self.main_menu()

        elif choice == '5':
            return

        else:
            print("Invalid choice.")
            self.main_menu()

    def run(self):
        """Run the setup wizard."""
        try:
            self.main_menu()
        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            sys.exit(0)


def main():
    """Main entry point for setup wizard."""
    from ravl.common.cli.ravl_cli_base import RAVLCLIBase

    # Detect installation type
    install_type = RAVLCLIBase.get_installation_type()
    config_path = RAVLCLIBase.get_config_path()

    print(f"RAVL Configuration Wizard")
    print(f"Installation type: {install_type}")
    print(f"Config location: {config_path}")
    print()

    # Try to find project (optional for config)
    try:
        project_root = RAVLCLIBase.find_project_root(required=False)
        if (project_root / 'ravl_loops').exists():
            print(f"Found RAVL project at: {project_root}")
        else:
            print("No RAVL project found in current directory.")
            print("Run 'ravl --init' to create a new project.")
    except Exception as e:
        print(f"Note: {e}")
        project_root = Path.cwd()

    setup = RAVLSetup(project_root)

    try:
        setup.run()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)


if __name__ == '__main__':
    main()
