#!/usr/bin/env python3
"""
Dependency checker module for Franklin installer.
Checks the installation status of various dependencies.
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum


class InstallState(Enum):
    """Installation state of a dependency."""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    OUTDATED = "outdated"
    CORRUPTED = "corrupted"
    UNKNOWN = "unknown"


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str
    display_name: str
    description: str
    state: InstallState
    version: Optional[str] = None
    latest_version: Optional[str] = None
    install_path: Optional[str] = None
    size_mb: Optional[float] = None
    required: bool = False
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
    
    def can_install(self) -> bool:
        """Check if this dependency can be installed."""
        return self.state in [InstallState.NOT_INSTALLED, InstallState.CORRUPTED]
    
    def can_reinstall(self) -> bool:
        """Check if this dependency can be reinstalled."""
        return self.state in [InstallState.INSTALLED, InstallState.OUTDATED, InstallState.CORRUPTED]
    
    def can_uninstall(self) -> bool:
        """Check if this dependency can be uninstalled."""
        return self.state in [InstallState.INSTALLED, InstallState.OUTDATED, InstallState.CORRUPTED]
    
    def can_update(self) -> bool:
        """Check if this dependency can be updated."""
        return self.state == InstallState.OUTDATED


class DependencyChecker:
    """Check installation status of development dependencies."""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        self.is_macos = self.platform == "darwin"
        self.is_linux = self.platform == "linux"
    
    def check_all_dependencies(self) -> Dict[str, DependencyInfo]:
        """Check all dependencies and return their status."""
        dependencies = {}
        
        # Check each dependency
        dependencies['miniforge'] = self.check_miniforge()
        dependencies['pixi'] = self.check_pixi()
        dependencies['docker'] = self.check_docker()
        dependencies['chrome'] = self.check_chrome()
        dependencies['franklin'] = self.check_franklin()
        
        return dependencies
    
    def check_miniforge(self) -> DependencyInfo:
        """Check Miniforge/Conda installation status."""
        info = DependencyInfo(
            name='miniforge',
            display_name='Miniforge',
            description='Python distribution and package manager',
            state=InstallState.NOT_INSTALLED,
            required=True
        )
        
        # Check for conda command
        conda_path = self._which('conda')
        if conda_path:
            info.install_path = conda_path
            info.state = InstallState.INSTALLED
            
            # Get version
            try:
                result = subprocess.run(
                    ['conda', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    if 'conda' in version_str:
                        info.version = version_str.split()[-1]
            except Exception:
                info.state = InstallState.CORRUPTED
            
            # Check for updates
            if info.version:
                latest = self._get_latest_conda_version()
                if latest:
                    info.latest_version = latest
                    if self._compare_versions(info.version, latest) < 0:
                        info.state = InstallState.OUTDATED
        
        return info
    
    def check_pixi(self) -> DependencyInfo:
        """Check Pixi installation status."""
        info = DependencyInfo(
            name='pixi',
            display_name='Pixi',
            description='Modern package manager for scientific computing',
            state=InstallState.NOT_INSTALLED,
            required=True,
            dependencies=['miniforge']
        )
        
        # Check for pixi command
        pixi_path = self._which('pixi')
        if pixi_path:
            info.install_path = pixi_path
            info.state = InstallState.INSTALLED
            
            # Get version
            try:
                result = subprocess.run(
                    ['pixi', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    if 'pixi' in version_str:
                        info.version = version_str.split()[-1]
            except Exception:
                info.state = InstallState.CORRUPTED
            
            # Check for updates
            if info.version:
                latest = self._get_latest_pixi_version()
                if latest:
                    info.latest_version = latest
                    if self._compare_versions(info.version, latest) < 0:
                        info.state = InstallState.OUTDATED
        
        return info
    
    def check_docker(self) -> DependencyInfo:
        """Check Docker Desktop installation status."""
        info = DependencyInfo(
            name='docker',
            display_name='Docker Desktop',
            description='Container platform for development',
            state=InstallState.NOT_INSTALLED,
            required=False
        )
        
        # Check for Docker
        if self.is_macos:
            docker_app = Path('/Applications/Docker.app')
            if docker_app.exists():
                info.install_path = str(docker_app)
                info.state = InstallState.INSTALLED
        elif self.is_windows:
            docker_path = self._which('docker')
            if docker_path:
                info.install_path = docker_path
                info.state = InstallState.INSTALLED
        else:
            docker_path = self._which('docker')
            if docker_path:
                info.install_path = docker_path
                info.state = InstallState.INSTALLED
        
        # Get version if installed
        if info.state == InstallState.INSTALLED:
            try:
                result = subprocess.run(
                    ['docker', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    if 'Docker version' in version_str:
                        info.version = version_str.split(',')[0].split()[-1]
            except Exception:
                info.state = InstallState.CORRUPTED
        
        return info
    
    def check_chrome(self) -> DependencyInfo:
        """Check Google Chrome installation status."""
        info = DependencyInfo(
            name='chrome',
            display_name='Google Chrome',
            description='Web browser for development',
            state=InstallState.NOT_INSTALLED,
            required=False
        )
        
        # Check for Chrome
        if self.is_macos:
            chrome_app = Path('/Applications/Google Chrome.app')
            if chrome_app.exists():
                info.install_path = str(chrome_app)
                info.state = InstallState.INSTALLED
                # Get version from Info.plist
                plist_path = chrome_app / 'Contents' / 'Info.plist'
                if plist_path.exists():
                    try:
                        import plistlib
                        with open(plist_path, 'rb') as f:
                            plist = plistlib.load(f)
                            info.version = plist.get('CFBundleShortVersionString')
                    except Exception:
                        pass
        elif self.is_windows:
            # Check common Chrome installation paths
            chrome_paths = [
                Path(os.environ.get('PROGRAMFILES', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                Path(os.environ.get('PROGRAMFILES(X86)', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            ]
            for chrome_path in chrome_paths:
                if chrome_path.exists():
                    info.install_path = str(chrome_path)
                    info.state = InstallState.INSTALLED
                    break
        else:
            # Linux
            chrome_path = self._which('google-chrome')
            if chrome_path:
                info.install_path = chrome_path
                info.state = InstallState.INSTALLED
        
        return info
    
    def check_franklin(self) -> DependencyInfo:
        """Check Franklin installation status."""
        info = DependencyInfo(
            name='franklin',
            display_name='Franklin',
            description='Educational platform for Jupyter notebooks',
            state=InstallState.NOT_INSTALLED,
            required=False,
            dependencies=['pixi']
        )
        
        # Check for franklin command
        franklin_path = self._which('franklin')
        if franklin_path:
            info.install_path = franklin_path
            info.state = InstallState.INSTALLED
            
            # Get version
            try:
                result = subprocess.run(
                    ['franklin', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    # Parse version from output
                    if 'version' in version_str.lower():
                        parts = version_str.split()
                        for i, part in enumerate(parts):
                            if 'version' in part.lower() and i + 1 < len(parts):
                                info.version = parts[i + 1]
                                break
            except Exception:
                info.state = InstallState.CORRUPTED
        
        # Check if installed via pixi global
        if not franklin_path and self._which('pixi'):
            try:
                result = subprocess.run(
                    ['pixi', 'global', 'list'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and 'franklin' in result.stdout:
                    info.state = InstallState.INSTALLED
                    # Extract version from pixi output
                    for line in result.stdout.splitlines():
                        if 'franklin' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                info.version = parts[1]
                            break
            except Exception:
                pass
        
        return info
    
    def _which(self, command: str) -> Optional[str]:
        """Find command in PATH."""
        try:
            if self.is_windows:
                result = subprocess.run(
                    ['where', command],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ['which', command],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if result.returncode == 0:
                path = result.stdout.strip().splitlines()[0]
                return path if path else None
        except Exception:
            pass
        return None
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
        try:
            from packaging import version
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
        except ImportError:
            # Fallback to simple string comparison
            parts1 = version1.split('.')
            parts2 = version2.split('.')
            
            for i in range(max(len(parts1), len(parts2))):
                p1 = int(parts1[i]) if i < len(parts1) and parts1[i].isdigit() else 0
                p2 = int(parts2[i]) if i < len(parts2) and parts2[i].isdigit() else 0
                
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            
            return 0
    
    def _get_latest_conda_version(self) -> Optional[str]:
        """Get latest conda version from conda-forge."""
        try:
            result = subprocess.run(
                ['conda', 'search', '-c', 'conda-forge', 'conda', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if 'conda' in data:
                    versions = [pkg['version'] for pkg in data['conda']]
                    if versions:
                        return sorted(versions)[-1]
        except Exception:
            pass
        return None
    
    def _get_latest_pixi_version(self) -> Optional[str]:
        """Get latest pixi version."""
        # This would normally check GitHub releases or package registry
        # For now, return None
        return None


def get_dependency_status() -> Dict[str, DependencyInfo]:
    """Get the status of all dependencies."""
    checker = DependencyChecker()
    return checker.check_all_dependencies()


def print_dependency_status():
    """Print dependency status to console."""
    dependencies = get_dependency_status()
    
    print("\nDependency Status:")
    print("-" * 60)
    
    for name, info in dependencies.items():
        status_symbol = {
            InstallState.INSTALLED: "✓",
            InstallState.NOT_INSTALLED: "✗",
            InstallState.OUTDATED: "⚠",
            InstallState.CORRUPTED: "⚠",
            InstallState.UNKNOWN: "?"
        }.get(info.state, "?")
        
        print(f"{status_symbol} {info.display_name:20} {info.state.value:15}", end="")
        if info.version:
            print(f" v{info.version}", end="")
        if info.state == InstallState.OUTDATED and info.latest_version:
            print(f" (latest: v{info.latest_version})", end="")
        print()
        
        if info.install_path:
            print(f"  Path: {info.install_path}")
        if info.dependencies:
            print(f"  Depends on: {', '.join(info.dependencies)}")
    
    print("-" * 60)


if __name__ == "__main__":
    print_dependency_status()