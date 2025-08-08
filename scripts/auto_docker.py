#!/usr/bin/env python3
"""
Docker Engine installer for Mac and Windows
Installs Docker Engine only (no Desktop GUI)
"""

import os
import sys
import subprocess
import platform
import urllib.request
import json
from pathlib import Path


class DockerEngineInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.silent = True  # Enable silent mode by default
        
    def run_command(self, command, shell=True, check=True):
        """Run a system command and return the result"""
        try:
            result = subprocess.run(
                command, 
                shell=shell, 
                check=check, 
                capture_output=True, 
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {e}")
            print(f"Output: {e.output}")
            raise
    
    def check_admin_privileges(self):
        """Check if script is running with admin privileges"""
        if self.system == "windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.getuid() == 0
    
    def install_homebrew_if_needed(self):
        """Install Homebrew on macOS if not present"""
        try:
            self.run_command("brew --version")
            print("✓ Homebrew already installed")
        except subprocess.CalledProcessError:
            print("Installing Homebrew silently...")
            # Set environment variables for non-interactive installation
            env_vars = {
                'NONINTERACTIVE': '1',
                'CI': '1'
            }
            env = os.environ.copy()
            env.update(env_vars)
            
            install_cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            subprocess.run(install_cmd, shell=True, env=env, check=True)
    
    def install_docker_mac(self):
        """Install Docker Engine on macOS"""
        print("Installing Docker Engine on macOS...")
        
        # Install Homebrew if needed
        self.install_homebrew_if_needed()
        
        try:
            # Install Docker using Homebrew (non-interactive)
            print("Installing Docker via Homebrew...")
            env = os.environ.copy()
            env['HOMEBREW_NO_INSTALL_CLEANUP'] = '1'
            env['HOMEBREW_NO_AUTO_UPDATE'] = '1'
            
            subprocess.run("brew install docker", shell=True, env=env, check=True)
            
            # Install Docker Machine (for creating Docker hosts)
            print("Installing Docker Machine...")
            subprocess.run("brew install docker-machine", shell=True, env=env, check=True)
            
            # Install VirtualBox silently
            print("Installing VirtualBox...")
            subprocess.run("brew install --cask virtualbox --no-quarantine", shell=True, env=env, check=False)
            
            print("✓ Docker Engine installed successfully on macOS")
            print("\nNext steps:")
            print("1. Create a Docker machine: docker-machine create default")
            print("2. Configure environment: eval $(docker-machine env default)")
            print("3. Start using Docker: docker run hello-world")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Installation failed: {e}")
            return False
        
        return True
    
    def install_docker_windows(self):
        """Install Docker Engine on Windows silently"""
        print("Installing Docker Engine on Windows...")
        
        # Check for WSL2
        if not self.check_wsl2():
            print("Installing WSL2...")
            self.install_wsl2()
        
        try:
            # Enable required Windows features silently
            print("Enabling required Windows features...")
            features = [
                "Microsoft-Windows-Subsystem-Linux",
                "VirtualMachinePlatform"
            ]
            
            for feature in features:
                cmd = f'powershell -Command "Enable-WindowsOptionalFeature -Online -FeatureName {feature} -NoRestart -All"'
                self.run_command(cmd)
            
            # Install Docker in WSL2 silently
            print("Installing Docker in WSL2...")
            wsl_commands = [
                "export DEBIAN_FRONTEND=noninteractive",
                "curl -fsSL https://get.docker.com -o get-docker.sh",
                "sudo sh get-docker.sh",
                "sudo usermod -aG docker root",
                "sudo service docker start",
                "sudo systemctl enable docker"
            ]
            
            combined_cmd = " && ".join(wsl_commands)
            wsl_cmd = f'wsl -e bash -c "{combined_cmd}"'
            self.run_command(wsl_cmd)
            
            print("✓ Docker Engine installed successfully on Windows")
            print("\nNext steps:")
            print("1. Restart your computer to complete WSL2 setup")
            print("2. Open WSL2 terminal")
            print("3. Start Docker service: sudo service docker start")
            print("4. Test Docker: docker run hello-world")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Installation failed: {e}")
            return False
        
        return True
    
    def check_wsl2(self):
        """Check if WSL2 is installed and configured"""
        try:
            result = self.run_command("wsl -l -v", check=False)
            return "Version 2" in result.stdout
        except:
            return False
    
    def install_wsl2(self):
        """Install and configure WSL2 silently"""
        try:
            # Download and install WSL2 kernel update
            kernel_url = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
            kernel_file = "wsl_update_x64.msi"
            
            print("Downloading WSL2 kernel update...")
            urllib.request.urlretrieve(kernel_url, kernel_file)
            
            print("Installing WSL2 kernel update...")
            self.run_command(f"msiexec /i {kernel_file} /quiet /norestart")
            
            # Set WSL2 as default
            self.run_command("wsl --set-default-version 2")
            
            # Install Ubuntu silently using winget or direct download
            print("Installing Ubuntu for WSL2...")
            try:
                # Try winget first (Windows 10 1709+)
                self.run_command("winget install Canonical.Ubuntu.2204 --silent --accept-package-agreements --accept-source-agreements")
            except:
                # Fallback to manual installation
                ubuntu_url = "https://aka.ms/wslubuntu2204"
                subprocess.run(f'powershell -Command "Invoke-WebRequest -Uri {ubuntu_url} -OutFile Ubuntu.appx -UseBasicParsing"', shell=True, check=True)
                subprocess.run('powershell -Command "Add-AppxPackage Ubuntu.appx"', shell=True, check=True)
                if os.path.exists("Ubuntu.appx"):
                    os.remove("Ubuntu.appx")
            
            # Initialize WSL with default user (no password)
            print("Initializing WSL with default configuration...")
            self.run_command('ubuntu2204.exe install --root')
            
            # Clean up
            if os.path.exists(kernel_file):
                os.remove(kernel_file)
                
        except Exception as e:
            print(f"WSL2 installation failed: {e}")
            raise
    
    def check_docker_installation(self):
        """Check if Docker is already installed"""
        try:
            result = self.run_command("docker --version", check=False)
            if result.returncode == 0:
                print(f"✓ Docker already installed: {result.stdout.strip()}")
                return True
        except:
            pass
        return False
    
    def install(self):
        """Main installation method - fully automated"""
        print(f"Docker Engine Installer for {self.system.title()}")
        print("=" * 50)
        
        # Skip confirmation if running silently
        if self.check_docker_installation() and not self.silent:
            response = input("Docker is already installed. Reinstall? (y/N): ")
            if response.lower() != 'y':
                return True
        elif self.check_docker_installation():
            print("Docker already installed, skipping installation...")
            return True
        
        # Check admin privileges for Windows
        if self.system == "windows" and not self.check_admin_privileges():
            print("✗ Administrator privileges required for Windows installation")
            print("Please run this script as Administrator")
            return False
        
        # Install based on OS
        if self.system == "darwin":  # macOS
            return self.install_docker_mac()
        elif self.system == "windows":
            return self.install_docker_windows()
        else:
            print(f"✗ Unsupported operating system: {self.system}")
            print("This installer supports macOS and Windows only")
            print("For Linux, use: curl -fsSL https://get.docker.com | sh")
            return False


def main():
    """Main function"""
    try:
        installer = DockerEngineInstaller()
        success = installer.install()
        
        if success:
            print("\n🎉 Docker Engine installation completed!")
        else:
            print("\n❌ Docker Engine installation failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()