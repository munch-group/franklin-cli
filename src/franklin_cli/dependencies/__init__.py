#!/usr/bin/env python3
"""
Development Environment Installer Python Module

A comprehensive Python module that automatically detects and installs missing development tools:
- Miniforge (if no conda-based Python is found)
- Pixi package manager
- Docker Desktop
- Google Chrome

Uses platform-specific installer scripts for reliable cross-platform installation.
"""

import os
import sys
import subprocess
import platform
import shutil
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class Platform(Enum):
    """Supported platforms"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


class InstallationStatus(Enum):
    """Installation status indicators"""
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"
    FAILED = "failed"


@dataclass
class ToolInfo:
    """Information about a development tool"""
    name: str
    display_name: str
    check_commands: List[str]
    check_paths: List[str]
    installer_scripts: Dict[Platform, str]
    required: bool = True


class DevEnvironmentInstaller:
    """
    Main installer class for development environment tools.
    
    Detects missing tools and installs them using platform-specific scripts.
    """
    
    def __init__(self, script_directory: Optional[str] = None, force: bool = False, 
                 continue_on_error: bool = True, dry_run: bool = False):
        """
        Initialize the installer.
        
        Args:
            script_directory: Directory containing installer scripts (default: current directory)
            force: Force reinstallation even if tools are already installed
            continue_on_error: Continue installing other tools if one fails
            dry_run: Only check what would be installed without actually installing
        """
        self.script_directory = Path(script_directory) if script_directory else Path.cwd()
        self.force = force
        self.continue_on_error = continue_on_error
        self.dry_run = dry_run
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Detect platform
        self.platform = self._detect_platform()
        self.logger.info(f"Detected platform: {self.platform.value}")
        
        # Define tools to manage
        self.tools = self._define_tools()
        
        # Track installation results
        self.installation_results: Dict[str, InstallationStatus] = {}
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('dev_env_installer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _detect_platform(self) -> Platform:
        """Detect the current platform"""
        system = platform.system().lower()
        
        if system == "windows":
            return Platform.WINDOWS
        elif system == "darwin":
            return Platform.MACOS
        elif system == "linux":
            return Platform.LINUX
        else:
            raise ValueError(f"Unsupported platform: {system}")
    
    def _define_tools(self) -> Dict[str, ToolInfo]:
        """Define the tools to be managed"""
        return {
            "miniforge": ToolInfo(
                name="miniforge",
                display_name="Miniforge (Conda-based Python)",
                check_commands=["conda", "mamba"],
                check_paths=[
                    "~/miniforge3/bin/conda",
                    "~/anaconda3/bin/conda",
                    "~/miniconda3/bin/conda",
                    "/opt/miniconda3/bin/conda",
                    "/opt/anaconda3/bin/conda"
                ],
                installer_scripts={
                    Platform.WINDOWS: "Install-Miniforge.ps1",
                    Platform.MACOS: "install-miniforge.sh",
                    Platform.LINUX: "install-miniforge.sh"
                }
            ),
            "pixi": ToolInfo(
                name="pixi",
                display_name="Pixi Package Manager",
                check_commands=["pixi"],
                check_paths=[
                    "~/.local/bin/pixi",
                    "~/.pixi/bin/pixi"
                ],
                installer_scripts={
                    Platform.WINDOWS: "Install-Pixi.ps1",
                    Platform.MACOS: "install-pixi.sh",
                    Platform.LINUX: "install-pixi.sh"
                }
            ),
            "docker": ToolInfo(
                name="docker",
                display_name="Docker Desktop",
                check_commands=["docker"],
                check_paths=[
                    "/usr/local/bin/docker",
                    "/usr/bin/docker",
                    "/Applications/Docker.app/Contents/Resources/bin/docker"
                ],
                installer_scripts={
                    Platform.WINDOWS: "Install-Docker-Desktop.ps1",
                    Platform.MACOS: "install-docker-desktop.sh",
                    Platform.LINUX: "install-docker-desktop.sh"
                }
            ),
            "chrome": ToolInfo(
                name="chrome",
                display_name="Google Chrome",
                check_commands=["google-chrome", "chrome"],
                check_paths=[
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/usr/bin/google-chrome",
                    "/opt/google/chrome/chrome",
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                ],
                installer_scripts={
                    Platform.WINDOWS: "Install-Chrome.ps1",
                    Platform.MACOS: "install-chrome.sh",
                    Platform.LINUX: "install-chrome.sh"
                }
            )
        }
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        return shutil.which(command) is not None
    
    def _path_exists(self, path: str) -> bool:
        """Check if a path exists, expanding user directory"""
        expanded_path = Path(path).expanduser()
        return expanded_path.exists()
    
    def _check_conda_python(self) -> bool:
        """Specifically check for conda-based Python installation"""
        # Check for conda command
        if self._command_exists("conda"):
            try:
                result = subprocess.run(
                    ["conda", "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    self.logger.info("Found conda installation")
                    return True
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
        
        # Check for mamba command (miniforge includes mamba)
        if self._command_exists("mamba"):
            try:
                result = subprocess.run(
                    ["mamba", "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    self.logger.info("Found mamba installation")
                    return True
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
        
        # Check common conda installation paths
        conda_paths = [
            "~/miniforge3/bin/conda",
            "~/anaconda3/bin/conda", 
            "~/miniconda3/bin/conda",
            "/opt/miniconda3/bin/conda",
            "/opt/anaconda3/bin/conda"
        ]
        
        for path in conda_paths:
            if self._path_exists(path):
                self.logger.info(f"Found conda at {path}")
                return True
        
        # Check if current Python is in a conda environment
        try:
            import sys
            if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
                # We're in a virtual environment, check if it's conda
                conda_meta = Path(sys.prefix) / "conda-meta"
                if conda_meta.exists():
                    self.logger.info("Running in conda environment")
                    return True
        except Exception:
            pass
        
        return False
    
    def check_tool_status(self, tool_name: str) -> InstallationStatus:
        """
        Check if a specific tool is installed.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            InstallationStatus indicating if the tool is installed
        """
        if tool_name not in self.tools:
            return InstallationStatus.UNKNOWN
        
        tool = self.tools[tool_name]
        
        # Special handling for miniforge (check for any conda-based Python)
        if tool_name == "miniforge":
            return InstallationStatus.INSTALLED if self._check_conda_python() else InstallationStatus.NOT_INSTALLED
        
        # Check commands in PATH
        for command in tool.check_commands:
            if self._command_exists(command):
                self.logger.debug(f"Found {tool.display_name} via command: {command}")
                return InstallationStatus.INSTALLED
        
        # Check specific paths
        for path in tool.check_paths:
            if self._path_exists(path):
                self.logger.debug(f"Found {tool.display_name} at path: {path}")
                return InstallationStatus.INSTALLED
        
        return InstallationStatus.NOT_INSTALLED
    
    def check_all_tools(self) -> Dict[str, InstallationStatus]:
        """
        Check the installation status of all tools.
        
        Returns:
            Dictionary mapping tool names to their installation status
        """
        status = {}
        for tool_name in self.tools:
            status[tool_name] = self.check_tool_status(tool_name)
            self.logger.info(f"{self.tools[tool_name].display_name}: {status[tool_name].value}")
        
        return status
    
    def _get_installer_script_path(self, tool_name: str) -> Optional[Path]:
        """Get the path to the installer script for a tool"""
        if tool_name not in self.tools:
            return None
        
        tool = self.tools[tool_name]
        script_name = tool.installer_scripts.get(self.platform)
        
        if not script_name:
            self.logger.error(f"No installer script defined for {tool.display_name} on {self.platform.value}")
            return None
        
        script_path = self.script_directory / script_name
        
        if not script_path.exists():
            self.logger.error(f"Installer script not found: {script_path}")
            return None
        
        return script_path
    
    def _run_installer_script(self, tool_name: str) -> bool:
        """
        Run the installer script for a tool.
        
        Args:
            tool_name: Name of the tool to install
            
        Returns:
            True if installation succeeded, False otherwise
        """
        script_path = self._get_installer_script_path(tool_name)
        if not script_path:
            return False
        
        tool = self.tools[tool_name]
        self.logger.info(f"Installing {tool.display_name}...")
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would run: {script_path}")
            return True
        
        try:
            # Build command based on platform and script type
            if self.platform == Platform.WINDOWS and script_path.suffix == ".ps1":
                # PowerShell script
                cmd = [
                    "powershell.exe", 
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(script_path)
                ]
                
                # Add arguments based on installer type
                if tool_name == "pixi":
                    cmd.extend(["-Command", "Install"])
                
                if self.force:
                    cmd.append("-Force")
                
            else:
                # Bash script
                cmd = ["bash", str(script_path)]
                
                # Add arguments for bash scripts
                if tool_name != "miniforge":  # miniforge script handles 'install' differently
                    cmd.append("install")
                
                if self.force:
                    cmd.append("--force")
            
            # Make script executable on Unix systems
            if self.platform != Platform.WINDOWS:
                os.chmod(script_path, 0o755)
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run the installer script
            result = subprocess.run(
                cmd,
                cwd=self.script_directory,
                capture_output=False,  # Let output go to terminal
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"✓ {tool.display_name} installation completed successfully")
                return True
            else:
                self.logger.error(f"✗ {tool.display_name} installation failed with exit code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"✗ {tool.display_name} installation timed out")
            return False
        except subprocess.SubprocessError as e:
            self.logger.error(f"✗ {tool.display_name} installation failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"✗ {tool.display_name} installation failed with unexpected error: {e}")
            return False
    
    def install_tool(self, tool_name: str) -> bool:
        """
        Install a specific tool if it's not already installed.
        
        Args:
            tool_name: Name of the tool to install
            
        Returns:
            True if tool is installed (was already installed or installation succeeded)
        """
        if tool_name not in self.tools:
            self.logger.error(f"Unknown tool: {tool_name}")
            return False
        
        tool = self.tools[tool_name]
        status = self.check_tool_status(tool_name)
        
        if status == InstallationStatus.INSTALLED and not self.force:
            self.logger.info(f"✓ {tool.display_name} is already installed")
            self.installation_results[tool_name] = InstallationStatus.INSTALLED
            return True
        
        if status == InstallationStatus.INSTALLED and self.force:
            self.logger.info(f"🔄 {tool.display_name} is installed but force flag is set, reinstalling...")
        
        # Run installation
        success = self._run_installer_script(tool_name)
        
        if success:
            # Verify installation
            new_status = self.check_tool_status(tool_name)
            if new_status == InstallationStatus.INSTALLED:
                self.installation_results[tool_name] = InstallationStatus.INSTALLED
                return True
            else:
                self.logger.warning(f"⚠️ {tool.display_name} installation script succeeded but tool not detected")
                self.installation_results[tool_name] = InstallationStatus.FAILED
                return False
        else:
            self.installation_results[tool_name] = InstallationStatus.FAILED
            return False
    
    def install_missing_tools(self, tools_to_check: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Install all missing tools or a subset of tools.
        
        Args:
            tools_to_check: List of tool names to check and install (default: all tools)
            
        Returns:
            Dictionary mapping tool names to installation success status
        """
        if tools_to_check is None:
            tools_to_check = list(self.tools.keys())
        
        results = {}
        
        self.logger.info("🔍 Checking development environment...")
        
        for tool_name in tools_to_check:
            if tool_name not in self.tools:
                self.logger.warning(f"Unknown tool: {tool_name}")
                continue
            
            try:
                success = self.install_tool(tool_name)
                results[tool_name] = success
                
                if not success and not self.continue_on_error:
                    self.logger.error(f"Installation failed for {tool_name} and continue_on_error is False. Stopping.")
                    break
                    
            except Exception as e:
                self.logger.error(f"Unexpected error installing {tool_name}: {e}")
                results[tool_name] = False
                
                if not self.continue_on_error:
                    break
        
        return results
    
    def install_franklin_via_pixi(self) -> bool:
        """
        Install Franklin using pixi global install.
        
        Returns:
            True if Franklin installation succeeded
        """
        if not self._command_exists("pixi"):
            self.logger.error("❌ Pixi is not available. Cannot install Franklin.")
            return False
        
        self.logger.info("📦 Installing Franklin via pixi global...")
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would run: pixi global install -c munch-group -c conda-forge franklin")
            return True
        
        try:
            cmd = ["pixi", "global", "install", "-c", "munch-group", "-c", "conda-forge", "franklin"]
            
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                self.logger.info("✓ Franklin installed successfully via pixi global")
                return True
            else:
                self.logger.error(f"✗ Franklin installation failed with exit code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("✗ Franklin installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"✗ Franklin installation failed: {e}")
            return False
    
    def run_full_installation(self) -> Dict[str, bool]:
        """
        Run the complete installation process:
        1. Install missing development tools
        2. Install Franklin via pixi (if pixi is available)
        
        Returns:
            Dictionary with installation results for each component
        """
        self.logger.info("🚀 Starting development environment installation...")
        
        # Install core development tools
        tool_results = self.install_missing_tools()
        
        # Install Franklin if pixi is available
        franklin_result = False
        if tool_results.get("pixi", False) or self.check_tool_status("pixi") == InstallationStatus.INSTALLED:
            franklin_result = self.install_franklin_via_pixi()
        else:
            self.logger.warning("⚠️ Skipping Franklin installation (pixi not available)")
        
        # Combine results
        all_results = {**tool_results, "franklin": franklin_result}
        
        # Show summary
        self._show_installation_summary(all_results)
        
        return all_results
    
    def _show_installation_summary(self, results: Dict[str, bool]) -> None:
        """Show a summary of installation results"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📋 INSTALLATION SUMMARY")
        self.logger.info("="*60)
        
        successful = []
        failed = []
        
        for tool_name, success in results.items():
            if tool_name == "franklin":
                display_name = "Franklin (via Pixi)"
            else:
                display_name = self.tools[tool_name].display_name
            
            if success:
                successful.append(display_name)
                self.logger.info(f"✅ {display_name}")
            else:
                failed.append(display_name)
                self.logger.info(f"❌ {display_name}")
        
        self.logger.info("-" * 60)
        self.logger.info(f"📊 Results: {len(successful)} successful, {len(failed)} failed")
        
        if failed:
            self.logger.warning(f"⚠️  Some installations failed: {', '.join(failed)}")
            self.logger.info("💡 You may need to install these manually or check the error messages above.")
        else:
            self.logger.info("🎉 All installations completed successfully!")
            self.logger.info("💡 You may need to restart your terminal to use the newly installed tools.")


def main():
    """Command-line interface for the development environment installer"""
    parser = argparse.ArgumentParser(
        description="Development Environment Installer - Automatically install missing dev tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dev_env_installer.py                          # Check and install all missing tools
  python dev_env_installer.py --check-only             # Only check what's installed
  python dev_env_installer.py --tools miniforge pixi   # Install only specific tools
  python dev_env_installer.py --force                  # Force reinstall all tools
  python dev_env_installer.py --dry-run                # See what would be installed
        """
    )
    
    parser.add_argument(
        "--script-dir", 
        type=str, 
        default=".",
        help="Directory containing installer scripts (default: current directory)"
    )
    
    parser.add_argument(
        "--tools",
        nargs="+",
        choices=["miniforge", "pixi", "docker", "chrome"],
        help="Specific tools to install (default: all missing tools)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if tools are already installed"
    )
    
    parser.add_argument(
        "--no-continue-on-error",
        action="store_true",
        help="Stop installation if any tool fails (default: continue)"
    )
    
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check installation status, don't install anything"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without actually installing"
    )
    
    parser.add_argument(
        "--no-franklin",
        action="store_true",
        help="Skip Franklin installation via pixi"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger('dev_env_installer').setLevel(logging.DEBUG)
    
    try:
        # Create installer instance
        installer = DevEnvironmentInstaller(
            script_directory=args.script_dir,
            force=args.force,
            continue_on_error=not args.no_continue_on_error,
            dry_run=args.dry_run
        )
        
        if args.check_only:
            # Just check status
            installer.logger.info("🔍 Checking development environment status...")
            status = installer.check_all_tools()
            
            # Show Franklin status if pixi is available
            if status.get("pixi") == InstallationStatus.INSTALLED:
                franklin_installed = installer._command_exists("franklin")
                installer.logger.info(f"Franklin (via Pixi): {'installed' if franklin_installed else 'not_installed'}")
            
            return 0 if all(s == InstallationStatus.INSTALLED for s in status.values()) else 1
        
        else:
            # Run installation
            if args.tools:
                # Install specific tools
                results = installer.install_missing_tools(args.tools)
                
                # Install Franklin if pixi was installed and not skipped
                if not args.no_franklin and ("pixi" in args.tools and results.get("pixi", False)):
                    franklin_result = installer.install_franklin_via_pixi()
                    results["franklin"] = franklin_result
                
                installer._show_installation_summary(results)
                
            else:
                # Full installation
                results = installer.run_full_installation()
            
            # Return appropriate exit code
            failed_count = sum(1 for success in results.values() if not success)
            return 0 if failed_count == 0 else 1
            
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
