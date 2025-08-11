# Franklin Installer Cheat Sheet

## Web Installers (No Security Warnings) 🚀

### By Role

#### Student (Default)
```bash
# macOS/Linux
curl -fsSL https://franklin.io/install | bash

# Windows PowerShell
irm https://franklin.io/install.ps1 | iex

# Windows CMD
powershell -Command "irm https://franklin.io/install.ps1 | iex"
```

#### Educator
```bash
# macOS/Linux
curl -fsSL https://franklin.io/install | bash -s -- --role educator

# Windows PowerShell (Short)
iex "& { $(irm https://franklin.io/install.ps1) } -Role educator"

# Windows PowerShell (Long)
& ([scriptblock]::Create((irm https://franklin.io/install.ps1))) -Role educator
```

#### Administrator
```bash
# macOS/Linux
curl -fsSL https://franklin.io/install | bash -s -- --role administrator

# Windows PowerShell
& ([scriptblock]::Create((irm https://franklin.io/install.ps1))) -Role administrator
```

## Common Scenarios

### Minimal Install (No Docker/Chrome)
```bash
# macOS/Linux
curl -fsSL https://franklin.io/install | bash -s -- --skip-docker --skip-chrome

# Windows
& ([scriptblock]::Create((irm https://franklin.io/install.ps1))) -SkipDocker -SkipChrome
```

### Force Reinstall Everything
```bash
# macOS/Linux
curl -fsSL https://franklin.io/install | bash -s -- --force

# Windows
& ([scriptblock]::Create((irm https://franklin.io/install.ps1))) -Force
```

### Educator Without Docker
```bash
# macOS/Linux
curl -fsSL https://franklin.io/install | bash -s -- --role educator --skip-docker

# Windows
& ([scriptblock]::Create((irm https://franklin.io/install.ps1))) -Role educator -SkipDocker
```

## The `-s --` Magic Explained

For `curl | bash`, arguments work like this:

```bash
curl -fsSL [URL] | bash -s -- [arguments]
         ↑                ↑  ↑      ↑
         |                |  |      |
    Silent+Follow    Read stdin |   Your arguments
     redirects       as script  |
                            Stop parsing
                            bash options
```

**Why `-s --`?**
- `-s`: Read script from stdin (the piped content)
- `--`: Stop parsing options for bash, pass rest to script

**Examples:**
```bash
# ❌ Wrong (bash tries to parse --role)
curl -fsSL url | bash --role educator

# ✅ Correct (--role passed to script)
curl -fsSL url | bash -s -- --role educator
```

## PowerShell Syntax Explained

PowerShell needs special handling:

```powershell
# Method 1: ScriptBlock (Recommended)
& ([scriptblock]::Create((irm [URL]))) -Param value
   ↑            ↑         ↑           ↑
   |            |         |           |
Execute   Create block  Download   Script params
          from string    content

# Method 2: Invoke-Expression
iex "& { $(irm [URL]) } -Param value"
 ↑    ↑   ↑           ↑
 |    |   |           |
Execute  Download  Script params
string   content
```

## Quick Options Reference

| What You Want | macOS/Linux | Windows PowerShell |
|--------------|-------------|-------------------|
| **Help** | `\| bash -s -- --help` | `-Help` |
| **Dry Run** | `\| bash -s -- --dry-run` | `-DryRun` |
| **Skip Docker** | `\| bash -s -- --skip-docker` | `-SkipDocker` |
| **Skip Chrome** | `\| bash -s -- --skip-chrome` | `-SkipChrome` |
| **Force Reinstall** | `\| bash -s -- --force` | `-Force` |
| **Force Pixi Only** | `\| bash -s -- --force-pixi` | N/A |
| **Student** | (default) | (default) |
| **Educator** | `\| bash -s -- --role educator` | `-Role educator` |
| **Admin** | `\| bash -s -- --role administrator` | `-Role administrator` |

## Multiple Options

### macOS/Linux
```bash
curl -fsSL https://franklin.io/install | bash -s -- \
    --role educator \
    --skip-docker \
    --skip-chrome \
    --force-pixi
```

### Windows PowerShell
```powershell
& ([scriptblock]::Create((irm https://franklin.io/install.ps1))) `
    -Role educator `
    -SkipDocker `
    -SkipChrome `
    -Force
```

## Non-Interactive Mode

### macOS/Linux
```bash
# No prompts, accept all defaults
export FRANKLIN_NONINTERACTIVE=1
curl -fsSL https://franklin.io/install | bash
```

### Windows
```powershell
$env:FRANKLIN_NONINTERACTIVE = "1"
irm https://franklin.io/install.ps1 | iex
```

## Inspection Before Running

### macOS/Linux
```bash
# Download and review
curl -fsSL https://franklin.io/install -o install.sh
less install.sh
bash install.sh --role educator
```

### Windows
```powershell
# Download and review
Invoke-WebRequest https://franklin.io/install.ps1 -OutFile install.ps1
notepad install.ps1
.\install.ps1 -Role educator
```

## Platform Detection

Not sure which command to use? Visit:
```
https://franklin.io/installers/
```
The page auto-detects your OS and shows the right command!

## Remember

- **macOS/Linux**: Use `bash -s --` for arguments
- **Windows**: Use scriptblock or `iex "& { }"`
- **No warnings**: Web installers bypass OS security prompts
- **Inspect first**: Download separately if you want to review
- **Get help**: Add `--help` (Unix) or `-Help` (Windows)