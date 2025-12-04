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
    get_configured_apis
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
        current_apis = get_configured_apis()
        api_count = len(current_apis)

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
        print(f"║  ╔═╩╗  ╔╩═╦══╗ ➿ ║ API Integrations: {api_count}")
        print(f"▒  ▒  ▒  ▒  ▒  ▒    ║ {cwd}")
        print("║ ╔╩╗ ╔═╦╩╗ ║ ╔╩╦═╦═╣")
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
                self.env_vars['RAVL_DEFAULT_LLM_PROVIDER'] = provider_id

        self._save_env()

        print(f"✓ {provider_name} configured")
        return True

    def setup_api_integration(self) -> bool:
        """
        Interactive API integration setup.

        Returns True if an API was configured.
        """
        print("\n=== API Integrations ===\n")

        # Show currently configured APIs
        current_apis = get_configured_apis()
        if current_apis:
            print("Currently configured:")
            for i, (api_name, env_key) in enumerate(current_apis.items(), 1):
                print(f"{i}) {api_name} ({env_key})")
            next_option = len(current_apis) + 1
        else:
            print("No APIs configured yet.")
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
                get_preferred_env_var, get_prompt_text, is_api_registered,
                add_api_to_registry, get_additional_vars
            )

            api_name = input("\nEnter the API name (e.g., \"ClickUp\", \"Stripe\", \"GitHub\"): ").strip()

            if not api_name:
                print("No API name provided.")
                return False

            # Check if API is in registry
            if is_api_registered(api_name):
                env_key = get_preferred_env_var(api_name)
                prompt_text = get_prompt_text(api_name)
            else:
                # Not in registry - ask user for env var name
                print(f"\n{api_name} is not in the registry yet.")
                print("What environment variable name should be used?")
                suggested = f"{api_name.upper().replace(' ', '_')}_API_TOKEN"
                print(f"Suggested: {suggested}")
                env_key = input("Environment variable name (or press Enter for suggestion): ").strip()

                if not env_key:
                    env_key = suggested

                prompt_text = f"{api_name} API token"

                # Add to registry for future use
                add_api_to_registry(api_name, [env_key], prompt=prompt_text)
                print(f"✓ Added {api_name} to registry with env var: {env_key}")

            # Prompt for the credential
            api_token = input(f"\nEnter your {prompt_text}: ").strip()

            if not api_token:
                print("No token provided.")
                return False

            # Save to .env
            self.env_vars[env_key] = api_token
            self._save_env()

            # Check for additional required vars (e.g., HIBOB_SERVICE_USER_ID)
            additional_vars = get_additional_vars(api_name)
            for var_info in additional_vars:
                if var_info.get('required', False):
                    var_name = var_info['name']
                    var_prompt = var_info.get('prompt', var_name)
                    var_value = input(f"\nEnter {var_prompt}: ").strip()
                    if var_value:
                        self.env_vars[var_name] = var_value
                        self._save_env()

            print(f"✓ {api_name} configured (saved as {env_key})")
            return True

        # Check if user selected an existing API to reconfigure
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(current_apis):
                api_name = list(current_apis.keys())[choice_num - 1]
                env_key = current_apis[api_name]

                print(f"\n=== Configure {api_name} ===")
                print(f"Current: {env_key}")
                print("\n1) Update token")
                print("2) Remove")
                print("3) Back")

                action = input("\nSelect (1-3): ").strip()

                if action == '1':
                    api_token = input(f"\nEnter new {api_name} API token: ").strip()
                    if api_token:
                        self.env_vars[env_key] = api_token
                        self._save_env()
                        print(f"✓ {api_name} token updated")
                        return True
                elif action == '2':
                    confirm = input(f"\nRemove {api_name}? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        del self.env_vars[env_key]
                        self._save_env()
                        print(f"✓ {api_name} removed")
                        return True
                elif action == '3':
                    return False
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
        print("4) Exit")

        choice = input("\nSelect (1-4): ").strip()

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
