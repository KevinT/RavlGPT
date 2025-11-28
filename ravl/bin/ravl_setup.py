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

        # Fixed configuration display width
        HEADER_WIDTH = 80

        # Top row with dynamic version
        header_prefix = "█ RavlGPT █ v "
        header_suffix = " █"
        version_part = f"{header_prefix}{__version__}{header_suffix}"
        top_padding = HEADER_WIDTH - len(version_part)
        top_row = version_part + ("█" * top_padding)

        # Bottom row (matches width)
        bottom_prefix = "░ ░ ░ ░ ░ ░ ░ ║ "
        bottom_padding = HEADER_WIDTH - len(bottom_prefix)
        bottom_row = bottom_prefix + ("░" * bottom_padding)

        print(top_row)
        print("║    ╔════╬═══╗")
        print(f"▓    ▓    ▓   ║ Default intelligence provider: {llm_display}")
        print(f"║  ╔═╩╗  ╔╩═╦═║ API Integrations: {api_count}")
        print(f"▒  ▒  ▒  ▒  ▒ ║ {cwd}")
        print("║ ╔╩╗ ╔═╦╩╗ ║ ║")
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
            api_name = input("\nEnter the API name (e.g., \"ClickUp\", \"Stripe\", \"GitHub\"): ").strip()

            if not api_name:
                print("No API name provided.")
                return False

            # Convert to env var format: ClickUp -> CLICKUP_API_TOKEN
            env_key = f"{api_name.upper().replace(' ', '_')}_API_TOKEN"

            api_token = input(f"\nEnter your {api_name} API token: ").strip()

            if not api_token:
                print("No API token provided.")
                return False

            # Save
            self.env_vars[env_key] = api_token
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
        print("3) Exit")

        choice = input("\nSelect (1-3): ").strip()

        if choice == '1':
            self.setup_llm_provider()
            # Return to main menu
            self.main_menu()

        elif choice == '2':
            self.setup_api_integration()
            # Return to main menu
            self.main_menu()

        elif choice == '3':
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
    # Find project root
    project_root = Path.cwd()
    while project_root != project_root.parent:
        if (project_root / '.ravl').exists():
            break
        project_root = project_root.parent

    if not (project_root / '.ravl').exists():
        print("Error: Could not find RAVL project root (.ravl directory not found)")
        sys.exit(1)

    setup = RAVLSetup(project_root)

    try:
        setup.run()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)


if __name__ == '__main__':
    main()
