# Web Installer Usage Guide

## Basic Usage

### Default Installation (Student)
```bash
# macOS/Linux
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash

# Windows PowerShell
irm https://[org].github.io/franklin/installers/install.ps1 | iex
```

## Passing Arguments

### macOS/Linux (bash)

Use `bash -s --` to pass arguments to the piped script:

```bash
# Specify role
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --role educator
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --role administrator

# Skip components
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --skip-docker
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --skip-chrome --skip-docker

# Force reinstall
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --force

# Multiple options
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --role educator --skip-docker --force

# Get help
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --help
```

### Windows PowerShell

PowerShell requires different syntax for passing parameters:

```powershell
# Method 1: Using scriptblock (recommended)
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) -Role educator
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) -Role administrator -SkipDocker

# Method 2: Using Invoke-Expression with parameters
iex "& { $(irm https://[org].github.io/franklin/installers/install.ps1) } -Role educator"
iex "& { $(irm https://[org].github.io/franklin/installers/install.ps1) } -Role administrator -SkipDocker -SkipChrome"

# Multiple parameters
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) `
    -Role educator `
    -SkipDocker `
    -SkipChrome `
    -Force

# Get help
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) -Help
```

## All Available Options

### Unix/Linux/macOS Options

| Option | Description | Example |
|--------|-------------|---------|
| `--role ROLE` | Set user role: student, educator, administrator | `--role educator` |
| `--skip-miniforge` | Skip Miniforge installation | `--skip-miniforge` |
| `--skip-pixi` | Skip Pixi installation | `--skip-pixi` |
| `--skip-docker` | Skip Docker Desktop installation | `--skip-docker` |
| `--skip-chrome` | Skip Chrome installation | `--skip-chrome` |
| `--skip-franklin` | Skip Franklin installation | `--skip-franklin` |
| `--force` | Force reinstall all components | `--force` |
| `--force-miniforge` | Force reinstall Miniforge only | `--force-miniforge` |
| `--force-pixi` | Force reinstall Pixi only | `--force-pixi` |
| `--force-docker` | Force reinstall Docker only | `--force-docker` |
| `--force-chrome` | Force reinstall Chrome only | `--force-chrome` |
| `--force-franklin` | Force reinstall Franklin only | `--force-franklin` |
| `--dry-run` | Show what would be installed without doing it | `--dry-run` |
| `--help` | Show help message | `--help` |

### Windows PowerShell Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `-Role` | Set user role: student, educator, administrator | `-Role educator` |
| `-SkipMiniforge` | Skip Miniforge installation | `-SkipMiniforge` |
| `-SkipPixi` | Skip Pixi installation | `-SkipPixi` |
| `-SkipDocker` | Skip Docker Desktop installation | `-SkipDocker` |
| `-SkipChrome` | Skip Chrome installation | `-SkipChrome` |
| `-SkipFranklin` | Skip Franklin installation | `-SkipFranklin` |
| `-Force` | Force reinstall all components | `-Force` |
| `-DryRun` | Show what would be installed without doing it | `-DryRun` |
| `-Help` | Show help message | `-Help` |

## Common Use Cases

### 1. Educator Installation (Skip Docker)
Many educators don't need Docker for teaching:

**macOS/Linux:**
```bash
curl -fsSL https://[org].github.io/franklin/installers/install.sh | \
    bash -s -- --role educator --skip-docker
```

**Windows:**
```powershell
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) `
    -Role educator -SkipDocker
```

### 2. Administrator Full Installation
Administrators need everything:

**macOS/Linux:**
```bash
curl -fsSL https://[org].github.io/franklin/installers/install.sh | \
    bash -s -- --role administrator
```

**Windows:**
```powershell
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) `
    -Role administrator
```

### 3. Minimal Installation (Franklin Only)
Just Franklin, no other components:

**macOS/Linux:**
```bash
curl -fsSL https://[org].github.io/franklin/installers/install.sh | \
    bash -s -- --skip-docker --skip-chrome
```

**Windows:**
```powershell
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) `
    -SkipDocker -SkipChrome
```

### 4. Reinstall Specific Component
Force reinstall just Pixi:

**macOS/Linux:**
```bash
curl -fsSL https://[org].github.io/franklin/installers/install.sh | \
    bash -s -- --force-pixi
```

**Windows:**
```powershell
# Note: Component-specific force not yet implemented in PowerShell version
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) -Force
```

### 5. Dry Run (Preview)
See what would be installed without actually installing:

**macOS/Linux:**
```bash
curl -fsSL https://[org].github.io/franklin/installers/install.sh | \
    bash -s -- --dry-run --role educator
```

**Windows:**
```powershell
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) `
    -DryRun -Role educator
```

## Environment Variables

You can also control behavior with environment variables:

### macOS/Linux
```bash
# Use different repository
export FRANKLIN_REPO_ORG="my-fork"
export FRANKLIN_REPO_NAME="franklin"
export FRANKLIN_REPO_BRANCH="dev"
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash

# Non-interactive mode (no prompts)
export FRANKLIN_NONINTERACTIVE=1
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash

# Custom install directory
export FRANKLIN_INSTALL_DIR="$HOME/custom-dir"
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash
```

### Windows PowerShell
```powershell
# Use different repository
$env:FRANKLIN_REPO_ORG = "my-fork"
$env:FRANKLIN_REPO_NAME = "franklin"
$env:FRANKLIN_REPO_BRANCH = "dev"
irm https://[org].github.io/franklin/installers/install.ps1 | iex

# Non-interactive mode
$env:FRANKLIN_NONINTERACTIVE = "1"
irm https://[org].github.io/franklin/installers/install.ps1 | iex
```

## Quick Reference Card

### Student (Default)
```bash
# macOS/Linux
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash

# Windows
irm https://[org].github.io/franklin/installers/install.ps1 | iex
```

### Educator
```bash
# macOS/Linux
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --role educator

# Windows
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) -Role educator
```

### Administrator
```bash
# macOS/Linux
curl -fsSL https://[org].github.io/franklin/installers/install.sh | bash -s -- --role administrator

# Windows
& ([scriptblock]::Create((irm https://[org].github.io/franklin/installers/install.ps1))) -Role administrator
```

## Troubleshooting

### "bash: --: invalid option"
You forgot the `-s` flag. Use `bash -s --` not just `bash --`.

### PowerShell "The term is not recognized"
Make sure you're using the correct syntax with scriptblock or Invoke-Expression.

### "Permission denied"
Some components (Docker, Chrome) may require administrator/sudo privileges.

### Script not found
Check if GitHub Pages is deployed. Try the raw GitHub URL instead:
```bash
curl -fsSL https://raw.githubusercontent.com/[org]/franklin/main/src/franklin_cli/dependencies/web-install.sh | bash
```