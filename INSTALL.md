# RAVL Installation Guide

Get RAVL running in 2 minutes.

## Recommended: UV Install

**[UV](https://docs.astral.sh/uv/)** is a fast Python package manager that makes RAVL installation simple and fast.

### 1. Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install RAVL Globally

```bash
uv tool install ravl-framework --from git+https://github.com/KevinT/RavlGPT
```

This installs all RAVL commands (`ravl`, `ravl-list`, `ravl-health`, etc.) globally on your system.

## Alternative: Project Specific Install

From your project root directory:

```bash
curl -sSL https://raw.githubusercontent.com/KevinT/RavlGPT/main/install.sh | bash
```

This command will:
- ✅ Add RAVL as a git submodule
- ✅ Set up CLI tools
- ✅ Check prerequisites
- ✅ Verify your environment

## Set Up API Key

RAVL markdown loops require an LLM API key. Choose your preferred provider:

### Option 1: Anthropic Claude

```bash
# Get your key from: https://console.anthropic.com/
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Make it permanent (choose your shell):
# For zsh (macOS default):
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-..."' >> ~/.zshrc
source ~/.zshrc

# For bash:
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-..."' >> ~/.bashrc
source ~/.bashrc
```

### Option 2: OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

### Option 3: Google Gemini

```bash
export GOOGLE_API_KEY="..."
```

### Option 4: Ollama (Local, No API Key)

No setup needed - runs locally. (UNTESTED!)

## Run Your First Loop

```bash
# Run the rugby tips example
$ ravl example_3_analysis_loop

# List all available loops
$ ravl --list

# Clone and customize an example
$ ravl --clone example_3_analysis_loop my_tips
$ ravl my_tips
```

## Prerequisites

RAVL automatically checks these, but if you need to install:

### Python 3.9-3.13

```bash
# Check your version
python3 --version

# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12 python3.12-venv

# Windows
# Download from python.org
```

### Git

```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt install git
```

## Troubleshooting

### "Not in a git repository"

Initialize git in your project:
```bash
git init
```

### "Python 3.9-3.13 required"

Install a compatible Python version:
```bash
# macOS
brew install python@3.12

# Check available versions
python3 --version
python3.11 --version
python3.12 --version
```

### "ANTHROPIC_API_KEY not found"

Make sure you've exported it:
```bash
echo $ANTHROPIC_API_KEY  # Should print your key

# If empty, export it:
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Permission denied" errors

Make CLI tools executable manually:
```bash
chmod +x .ravl/bin/*
chmod +x ./ravl
```

### "python3-venv not found"

Install venv support:
```bash
# Ubuntu/Debian
sudo apt install python3.12-venv

# macOS (usually included)
brew install python@3.12
```

### Venv creation fails

The framework creates a virtual environment on first run. If it fails:
```bash
# Remove and let it recreate
rm -rf .ravl/venv
$ ravl --list
```

**With UV (recommended):** UV automatically manages Python versions and creates venvs 200x faster. If you're experiencing venv issues, try installing UV:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Framework will automatically detect and use UV
```

## Manual Installation

If you prefer not to use the install script:

```bash
# 1. Add submodule
git submodule add https://github.com/KevinT/RavlGPT .ravl

# 2. Make tools executable
chmod +x .ravl/bin/*

# 3. Create wrapper
ln -s .ravl/bin/ravl-wrapper ./ravl

# 4. Test
$ ravl --list
```

## Installing in Existing Projects

If cloning a project that already has RAVL:

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/your-org/your-project.git
cd your-project

# Or initialize submodules after cloning
git submodule update --init --recursive

# Make tools executable
chmod +x .ravl/bin/*

# Run
$ ravl --list
```

## Updating RAVL

To update to the latest RAVL version:

```bash
cd .ravl
git pull origin main
cd ..
git add .ravl
git commit -m "Update RAVL framework"
```

## Optional Enhancements

### Add to PATH

Use `ravl` commands from anywhere in your project:

```bash
# For zsh (macOS):
echo 'export PATH="$PATH:$(git rev-parse --show-toplevel 2>/dev/null)/.ravl/bin"' >> ~/.zshrc
source ~/.zshrc

# For bash:
echo 'export PATH="$PATH:$(git rev-parse --show-toplevel 2>/dev/null)/.ravl/bin"' >> ~/.bashrc
source ~/.bashrc

# Then you can use:
cd anywhere/in/project
ravl --list  # No need for ./ravl
```

### Shell Completion

Add command completion (future enhancement).

## Next Steps

- **Learn**: Read [RAVL Protocol](ravl/docs/RAVL_PROTOCOL.md)
- **Explore**: Browse [Examples](ravl/ravl_loops/examples/)
- **Create**: Clone a template with `./ravl-clone`
- **Customize**: Edit loop configurations

## Getting Help

- **Documentation**: See [docs/](ravl/docs/)
- **Examples**: See [examples/](ravl/ravl_loops/examples/)
- **Issues**: Report at https://github.com/KevinT/RavlGPT/issues

## Uninstalling

To remove RAVL from your project:

```bash
# Remove submodule
git submodule deinit -f .ravl
git rm -f .ravl
rm -rf .git/modules/.ravl

# Remove wrapper
rm -f ./ravl

# Commit the change
git commit -m "Remove RAVL framework"
```
