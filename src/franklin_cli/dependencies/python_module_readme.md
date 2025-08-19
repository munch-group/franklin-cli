# Development Environment Installer Python Module

A comprehensive Python module that automatically detects and installs missing development tools using platform-specific installer scripts. Provides both a command-line interface and a programmatic API for seamless integration into your development workflow.

## Features

🔍 **Smart Detection** - Automatically detects missing development tools  
🚀 **Cross-Platform** - Works on Windows, macOS, and Linux  
📦 **Multiple Tools** - Installs Miniforge, Pixi, Docker Desktop, Chrome, and Franklin  
🛠️ **Platform-Specific** - Uses optimized installer scripts for each platform  
🎯 **Selective Installation** - Install only the tools you need  
🔄 **Force Reinstall** - Option to reinstall even if tools exist  
🐍 **Pure Python** - No external dependencies, uses only standard library  
📋 **Detailed Logging** - Comprehensive logging and progress reporting  
🧪 **Dry Run Mode** - Test what would be installed without making changes  

## Quick Start

### Installation

```bash
# Install from source
pip install -e .

# Or use directly (no installation required)
python dev_env_installer.py --help
```

### Command Line Usage

```bash
# Install all missing development tools
python dev_env_installer.py

# Check what's installed without installing anything
python dev_env_installer.py --check-only

# Install only specific tools
python dev_env_installer.py --tools miniforge pixi

# Force reinstall everything
python dev_env_installer.py --force

# Dry run (see what would be installed)
python dev_env_installer.py --dry-run

# Custom script directory
python dev_env_installer.py --script-dir /path/to/installer/scripts
```

### Python API Usage

```python
from dev_env_installer import DevEnvironmentInstaller

# Basic usage
installer = DevEnvironmentInstaller()
results = installer.run_full_installation()

# Check status only
status = installer.check_all_tools()
print(f"Miniforge installed: {status['miniforge']}")

# Install specific tools
installer = DevEnvironmentInstaller(force=True)
results = installer.install_missing_tools(['miniforge', 'pixi'])
```

## Supported Tools

| Tool | Description | Platforms | Detection Method |
|------|-------------|-----------|------------------|
| **Miniforge** | Conda-based Python distribution | Windows, macOS, Linux | `conda`/`mamba` commands, installation paths |
| **Pixi** | Fast package manager | Windows, macOS, Linux | `pixi` command, binary paths |
| **Docker Desktop** | Containerization platform | Windows, macOS, Linux | `docker` command, installation paths |
| **Google Chrome** | Web browser | Windows, macOS, Linux | Browser executables, app bundles |
| **Franklin** | Static site generator | All (via Pixi) | `franklin` command (installed via pixi) |

## Requirements

### System Requirements
- **Python 3.7+** (no external Python dependencies)
- **Internet connection** for downloading tools
- **Administrator/sudo privileges** for system installations

### Required Installer Scripts
The module requires platform-specific installer scripts in the script directory:

**PowerShell Scripts (Windows):**
- `Install-Miniforge.ps1`
- `Install-Pixi.ps1`
- `Install-Docker-Desktop.ps1`
- `Install-Chrome.ps1`

**Bash Scripts (macOS/Linux):**
- `install-miniforge.sh`
- `install-pixi.sh`
- `install-docker-desktop.sh`
- `install-chrome.sh`

## Detailed Usage

### Command Line Interface

#### Basic Commands

```bash
# Install all missing tools
python dev_env_installer.py

# Show help
python dev_env_installer.py --help

# Check installation status
python dev_env_installer.py --check-only

# Verbose output
python dev_env_installer.py --verbose
```

#### Advanced Options

```bash
# Custom script directory
python dev_env_installer.py --script-dir ~/my-installer-scripts

# Install specific tools only
python dev_env_installer.py --tools miniforge pixi docker

# Force reinstall even if already installed
python dev_env_installer.py --force

# Stop on first error (default: continue)
python dev_env_installer.py --no-continue-on-error

# Skip Franklin installation
python dev_env_installer.py --no-franklin

# Dry run mode (show what would be done)
python dev_env_installer.py --dry-run
```

#### Exit Codes

- `0` - Success (all tools installed successfully)
- `1` - Failure (one or more installations failed)
- `130` - Cancelled by user (Ctrl+C)

### Python API

#### Basic API Usage

```python
from dev_env_installer import DevEnvironmentInstaller, InstallationStatus

# Create installer instance
installer = DevEnvironmentInstaller()

# Check what's installed
status = installer.check_all_tools()
for tool, status in status.items():
    print(f"{tool}: {status.value}")

# Install missing tools
results = installer.run_full_installation()
```

#### Advanced Configuration

```python
from dev_env_installer import DevEnvironmentInstaller

# Custom configuration
installer = DevEnvironmentInstaller(
    script_directory="/path/to/scripts",  # Custom script location
    force=True,                           # Force reinstall
    continue_on_error=True,               # Don't stop on errors
    dry_run=False                         # Actually install
)

# Install specific tools
tools_to_install = ["miniforge", "pixi"]
results = installer.install_missing_tools(tools_to_install)

# Check individual tool
if installer.check_tool_status("pixi") == InstallationStatus.INSTALLED:
    # Install Franklin via pixi
    franklin_success = installer.install_franklin_via_pixi()
```

#### Error Handling

```python
from dev_env_installer import DevEnvironmentInstaller
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

try:
    installer = DevEnvironmentInstaller(continue_on_error=True)
    results = installer.run_full_installation()
    
    # Check results
    failed_tools = [tool for tool, success in results.items() if not success]
    if failed_tools:
        print(f"Failed to install: {failed_tools}")
    
except Exception as e:
    print(f"Installation error: {e}")
```

### Detection Logic

#### Conda-based Python Detection

The module specifically checks for conda-based Python installations:

1. **Command availability**: `conda` or `mamba` commands
2. **Standard paths**: `~/miniforge3`, `~/anaconda3`, `~/miniconda3`, etc.
3. **Current environment**: Checks if running in a conda environment
4. **conda-meta directory**: Looks for conda package metadata

#### Tool Detection Priority

For each tool, the module checks in this order:

1. **Commands in PATH**: Primary detection method
2. **Standard installation paths**: Platform-specific locations
3. **Application bundles**: macOS .app bundles, Windows Program Files

## Platform Support

### Windows
- **PowerShell scripts** with `-ExecutionPolicy Bypass`
- **Registry integration** for uninstaller
- **Administrator privilege** handling
- **Windows-specific paths** and detection

### macOS
- **Bash scripts** with executable permissions
- **Application bundle** detection (`/Applications/*.app`)
- **Homebrew integration** where applicable
- **macOS-specific paths** and conventions

### Linux
- **Bash scripts** with standard Unix conventions
- **Package manager integration** where applicable
- **Standard Linux paths** (`/usr/bin`, `/usr/local/bin`, etc.)
- **Distribution-agnostic** approach

## Examples

### Example 1: Basic Installation

```python
#!/usr/bin/env python3
from dev_env_installer import DevEnvironmentInstaller

def main():
    # Create installer
    installer = DevEnvironmentInstaller()
    
    # Check current status
    print("Checking development environment...")
    status = installer.check_all_tools()
    
    # Install missing tools
    print("Installing missing tools...")
    results = installer.run_full_installation()
    
    # Show results
    print(f"Installation completed: {results}")

if __name__ == "__main__":
    main()
```

### Example 2: Selective Installation

```python
#!/usr/bin/env python3
from dev_env_installer import DevEnvironmentInstaller, InstallationStatus

def install_python_stack():
    """Install only Python-related tools"""
    installer = DevEnvironmentInstaller()
    
    # Install Python stack
    python_tools = ["miniforge", "pixi"]
    results = installer.install_missing_tools(python_tools)
    
    # Install Franklin if Pixi succeeded
    if results.get("pixi", False):
        franklin_success = installer.install_franklin_via_pixi()
        print(f"Franklin installation: {'success' if franklin_success else 'failed'}")
    
    return results

if __name__ == "__main__":
    results = install_python_stack()
    print(f"Python stack installation: {results}")
```

### Example 3: CI/CD Integration

```python
#!/usr/bin/env python3
"""
CI/CD pipeline integration example
"""
import sys
from dev_env_installer import DevEnvironmentInstaller

def setup_ci_environment():
    """Setup development environment for CI/CD"""
    installer = DevEnvironmentInstaller(
        force=False,  # Don't reinstall if cached
        continue_on_error=True,  # Don't fail entire build
        dry_run=False
    )
    
    # Required tools for CI
    required_tools = ["miniforge", "pixi", "docker"]
    
    print("Setting up CI environment...")
    results = installer.install_missing_tools(required_tools)
    
    # Check if critical tools are available
    critical_failures = []
    for tool in ["miniforge", "pixi"]:
        if not results.get(tool, False):
            critical_failures.append(tool)
    
    if critical_failures:
        print(f"Critical tools failed: {critical_failures}")
        return False
    
    print("CI environment ready!")
    return True

if __name__ == "__main__":
    success = setup_ci_environment()
    sys.exit(0 if success else 1)
```

## Troubleshooting

### Common Issues

**"No module named 'dev_env_installer'"**
- Ensure the module is in your Python path
- Install with `pip install -e .` or run directly with `python dev_env_installer.py`

**"Installer script not found"**
- Check that all required installer scripts are in the script directory
- Use `--script-dir` to specify the correct path
- Verify script names match exactly (case-sensitive)

**"Permission denied" errors**
- Run with administrator/sudo privileges
- Check that installer scripts are executable (`chmod +x *.sh`)

**"PowerShell execution policy" errors**
- The module uses `-ExecutionPolicy Bypass` by default
- Ensure PowerShell is available and not restricted by group policy

### Debugging

Enable verbose logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via command line
python dev_env_installer.py --verbose
```

### Platform-Specific Issues

**Windows:**
- Ensure PowerShell is available
- Run as Administrator for system installations
- Check Windows Defender/antivirus settings

**macOS:**
- Allow unsigned applications if needed
- Check System Preferences → Security & Privacy
- Verify bash is available and scripts are executable

**Linux:**
- Ensure package managers are available
- Check internet connectivity
- Verify sudo privileges for system installations

## Development

### Project Structure

```
dev_env_installer/
├── dev_env_installer.py          # Main module
├── setup.py                      # Package setup
├── example_usage.py              # Usage examples
├── README.md                     # This file
├── requirements.txt              # Dependencies (none for main module)
└── tests/                        # Test suite (future)
    ├── test_detection.py
    ├── test_installation.py
    └── test_platform_support.py
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all platforms are supported
5. Submit a pull request

### Testing

```bash
# Run basic tests
python dev_env_installer.py --check-only --verbose

# Test dry run
python dev_env_installer.py --dry-run

# Run examples
python example_usage.py
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the example usage scripts
3. Enable verbose logging for detailed error information
4. Check that all required installer scripts are present and executable

## Changelog

### v1.0.0
- Initial release
- Cross-platform support (Windows, macOS, Linux)
- Support for Miniforge, Pixi, Docker Desktop, Chrome, Franklin
- Command-line interface and Python API
- Comprehensive detection logic
- Dry run and force installation modes