# Simplified Role-Based Installers

## Overview

We provide role-specific installers that eliminate the need for complex command-line arguments. Each role has its own dedicated installer URL.

## Quick Install Commands

### Student Installation
```bash
# macOS/Linux
curl -fsSL https://franklin.io/installers/student-install.sh | bash

# Windows PowerShell
irm https://franklin.io/installers/student-install.ps1 | iex

# Windows Command Prompt
powershell -Command "irm https://franklin.io/installers/student-install.ps1 | iex"
```

### Educator Installation
```bash
# macOS/Linux
curl -fsSL https://franklin.io/installers/educator-install.sh | bash

# Windows PowerShell
irm https://franklin.io/installers/educator-install.ps1 | iex

# Windows Command Prompt
powershell -Command "irm https://franklin.io/installers/educator-install.ps1 | iex"
```

### Administrator Installation
```bash
# macOS/Linux
curl -fsSL https://franklin.io/installers/administrator-install.sh | bash

# Windows PowerShell
irm https://franklin.io/installers/administrator-install.ps1 | iex

# Windows Command Prompt
powershell -Command "irm https://franklin.io/installers/administrator-install.ps1 | iex"
```

## Why Simplified Installers?

### Before (Complex)
```bash
# macOS/Linux - Had to remember -s -- syntax
curl -fsSL https://franklin.io/install.sh | bash -s -- --role educator

# Windows - Very complex syntax
& ([scriptblock]::Create((irm https://franklin.io/install.ps1))) -Role educator
# OR
iex "& { $(irm https://franklin.io/install.ps1) } -Role educator"
```

### After (Simple)
```bash
# macOS/Linux - Just pipe to bash
curl -fsSL https://franklin.io/educator-install.sh | bash

# Windows - Standard irm | iex
irm https://franklin.io/educator-install.ps1 | iex
```

## Additional Options Still Available

Even with role-specific installers, you can still pass additional options:

### macOS/Linux
```bash
# Educator without Docker
curl -fsSL https://franklin.io/educator-install.sh | bash -s -- --skip-docker

# Administrator with force reinstall
curl -fsSL https://franklin.io/administrator-install.sh | bash -s -- --force
```

### Windows PowerShell
```bash
# Educator without Docker (simple!)
irm https://franklin.io/educator-install.ps1 | iex -SkipDocker

# Administrator with force reinstall
irm https://franklin.io/administrator-install.ps1 | iex -Force
```

## Available Scripts

| Role | Bash/Zsh URL | PowerShell URL |
|------|--------------|----------------|
| **Student** | `/student-install.sh` | `/student-install.ps1` |
| **Educator** | `/educator-install.sh` | `/educator-install.ps1` |
| **Administrator** | `/administrator-install.sh` | `/administrator-install.ps1` |
| **Admin** (alias) | `/admin-install.sh` | `/admin-install.ps1` |

## Interactive Web Pages

Each role also has an interactive web page:
- Student: `https://franklin.io/installers/student-install.html`
- Educator: `https://franklin.io/installers/educator-install.html`
- Administrator: `https://franklin.io/installers/administrator-install.html`

## How It Works

1. **Role-specific scripts** are generated automatically by `build-role-installers.sh`
2. Each script is a thin wrapper that:
   - Downloads the main installer
   - Passes the hardcoded `--role` parameter
   - Forwards any additional user parameters
3. **No complexity** for users - just copy and paste

## For Developers

### Building Role Installers
```bash
# Run the builder script
./src/franklin/dependencies/build-role-installers.sh

# Creates:
#   student-install.sh / .ps1
#   educator-install.sh / .ps1
#   administrator-install.sh / .ps1
#   admin-install.sh / .ps1 (alias)
```

### GitHub Actions
The workflow automatically:
1. Builds native installers
2. Copies web installers
3. **Generates role-specific installers**
4. Deploys everything to GitHub Pages

### Custom Base URL
For testing or forks:
```bash
# macOS/Linux
export FRANKLIN_INSTALLER_URL="https://my-fork.github.io/franklin/installers/install.sh"
curl -fsSL https://my-fork.github.io/franklin/installers/educator-install.sh | bash

# Windows
$env:FRANKLIN_INSTALLER_URL = "https://my-fork.github.io/franklin/installers/install.ps1"
irm https://my-fork.github.io/franklin/installers/educator-install.ps1 | iex
```

## Comparison

| Aspect | Generic Installer | Role-Specific Installer |
|--------|------------------|------------------------|
| **URL Length** | Shorter | Slightly longer (adds role) |
| **Command Complexity** | Complex with parameters | Simple pipe |
| **Flexibility** | Full parameter support | Role fixed, others flexible |
| **User Errors** | Easy to mess up syntax | Hard to get wrong |
| **PowerShell** | Very complex | Standard `irm \| iex` |

## Security

- All installers use HTTPS
- Scripts are served from GitHub Pages (reliable)
- Role-specific scripts are thin wrappers (minimal code)
- Main logic stays in one place (easier to audit)

## Troubleshooting

### "Command not found"
- Check if the URL is correct
- Verify GitHub Pages is deployed
- Try the direct GitHub raw URL as fallback

### Wrong role installed
- Make sure you're using the correct role-specific URL
- Check the banner message shows the expected role

### Additional options not working
- For bash: Remember to use `bash -s --` before options
- For PowerShell: Options go after `iex`

## Summary

Role-specific installers provide:
- ✅ **Simpler commands** - No complex syntax to remember
- ✅ **Fewer user errors** - Hard to get wrong
- ✅ **Better PowerShell UX** - Standard `irm | iex` pattern
- ✅ **Still flexible** - Additional options still work
- ✅ **Self-documenting** - URL indicates the role

Perfect for documentation, tutorials, and quick installations!