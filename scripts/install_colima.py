#!/usr/bin/env python3
"""
Docker Engine installer for Mac and Windows
Installs Docker Engine only (no Desktop GUI)
Usage: python install_docker_engine.py [--uninstall]
"""

import os
import sys
import subprocess
import platform
import urllib.request
import json
import argparse
from pathlib import Path


class DockerEngineInstaller:
    def __init__(self, uninstall_mode=False):
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.silent = True  # Enable silent mode by default
        self.uninstall_mode = uninstall_mode
        
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
        """No longer needed - removed Homebrew dependency"""
        pass
    
    def install_docker_mac(self):
        """Install actual Docker Engine on macOS using Colima (actively maintained)"""
        print("Installing Docker Engine on macOS with Colima...")
        print("This will use Nix (if available) or direct download with Rosetta support...")
        
        try:
            # Install Lima first (required by Colima)
            print("Installing Lima (required by Colima)...")
            self.install_lima_mac()
            
            # Install Colima (container runtime for macOS)
            print("Installing Colima...")
            self.install_colima_mac()
            
            # Install Docker CLI
            print("Installing Docker CLI...")
            self.install_docker_cli_mac()
            
            # Install Docker Compose
            print("Installing Docker Compose...")
            self.install_docker_compose_mac()
            
            # Start Colima with Docker runtime
            print("Starting Colima with Docker runtime...")
            subprocess.run("colima start --runtime docker", shell=True, check=True)
            
            # Verify installation
            print("Verifying Docker installation...")
            subprocess.run("docker --version", shell=True, check=True)
            subprocess.run("docker info", shell=True, check=True)
            
            print("✓ Docker Engine with Colima installed successfully on macOS")
            print("\nNext steps:")
            print("1. Test Docker: docker run hello-world")
            print("2. Manage Colima: colima stop / colima start")
            print("3. View status: colima status")
            print("4. SSH into VM: colima ssh")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Installation failed: {e}")
            return False
        
        return True
    
    def install_lima_mac(self):
        """Install Lima on macOS with multiple installation methods"""
        try:
            # Check if Lima is already installed
            subprocess.run("limactl --version", shell=True, check=True, capture_output=True)
            print("✓ Lima already installed")
            return
        except subprocess.CalledProcessError:
            pass
        
        # Try multiple installation methods
        installation_methods = [
            self.install_lima_nix,
            self.install_lima_direct_download
        ]
        
        for method in installation_methods:
            try:
                method()
                print("✓ Lima installed successfully")
                return
            except Exception as e:
                print(f"Lima installation method failed: {e}")
                continue
        
        raise Exception("All Lima installation methods failed")
    
    def install_lima_nix(self):
        """Install Lima using Nix package manager"""
        print("Attempting to install Lima via Nix...")
        
        # Check if Nix is available
        try:
            subprocess.run("nix --version", shell=True, check=True, capture_output=True)
            print("Installing Lima via Nix...")
        except subprocess.CalledProcessError:
            raise Exception("Nix not available")
        
        # Install Lima via Nix
        subprocess.run("nix-env -iA nixpkgs.lima", shell=True, check=True)
        print("✓ Lima installed via Nix")
    
    def install_lima_direct_download(self):
        """Install Lima via direct download"""
        print("Installing Lima via direct download...")
        
        # Determine if we need Rosetta for Apple Silicon
        needs_rosetta = self.arch in ["arm64", "aarch64"]
        
        if needs_rosetta:
            self.ensure_rosetta_installed()
        
        # Use latest Lima version
        lima_version = "1.0.1"  # Latest stable version
        
        # Lima architecture naming
        arch_variants = []
        if self.arch in ["arm64", "aarch64"]:
            arch_variants = ["aarch64", "x86_64"]  # Try native first, then Intel
        else:
            arch_variants = ["x86_64"]
        
        # Try each architecture variant
        for arch in arch_variants:
            lima_url = f"https://github.com/lima-vm/lima/releases/download/v{lima_version}/lima-{lima_version}-Darwin-{arch}.tar.gz"
            
            print(f"Trying to download Lima v{lima_version} for {arch}...")
            
            try:
                subprocess.run(f"curl -fsSL {lima_url} -o lima.tar.gz", shell=True, check=True)
                
                if arch == "x86_64" and needs_rosetta:
                    print("✓ Downloaded Intel binary for Apple Silicon (will run via Rosetta)")
                else:
                    print(f"✓ Downloaded {arch} binary")
                
                break  # Success, exit the loop
                
            except subprocess.CalledProcessError:
                print(f"Failed to download {arch} binary")
                if arch == arch_variants[-1]:  # Last attempt
                    raise Exception(f"Failed to download Lima for any architecture")
                continue
        
        print("Extracting Lima...")
        subprocess.run("tar -xzf lima.tar.gz", shell=True, check=True)
        
        print("Installing Lima binaries...")
        subprocess.run("sudo mkdir -p /usr/local/bin", shell=True, check=True)
        
        # Install all Lima binaries
        lima_binaries = ["limactl", "lima"]  # Main binaries
        
        for binary in lima_binaries:
            src_path = f"bin/{binary}"
            dst_path = f"/usr/local/bin/{binary}"
            if os.path.exists(src_path):
                subprocess.run(f"sudo cp '{src_path}' '{dst_path}'", shell=True, check=True)
                subprocess.run(f"sudo chmod +x '{dst_path}'", shell=True, check=True)
                print(f"✓ Installed {binary}")
        
        # Clean up
        subprocess.run("rm -rf lima.tar.gz bin share", shell=True, check=False)
        
        print("✓ Lima installed via direct download")
    
    def install_colima_mac(self):
        """Install Colima on macOS with multiple installation methods"""
        try:
            # Check if Colima is already installed (fix permission issue)
            result = subprocess.run("which colima", shell=True, capture_output=True)
            if result.returncode == 0:
                try:
                    subprocess.run("colima --version", shell=True, check=True)
                    print("✓ Colima already installed")
                    return
                except subprocess.CalledProcessError:
                    # colima exists but might have permission issues, continue with installation
                    pass
        except:
            pass
        
        # Try multiple installation methods in order of preference
        installation_methods = [
            self.install_colima_nix,
            self.install_colima_direct_download
        ]
        
        for method in installation_methods:
            try:
                method()
                print("✓ Colima installed successfully")
                return
            except Exception as e:
                print(f"Installation method failed: {e}")
                continue
        
        raise Exception("All Colima installation methods failed")
    
    def install_colima_nix(self):
        """Install Colima using Nix package manager"""
        print("Attempting to install Colima via Nix...")
        
        # Check if Nix is available
        try:
            subprocess.run("nix --version", shell=True, check=True, capture_output=True)
            print("✓ Nix found, installing Colima...")
        except subprocess.CalledProcessError:
            print("Nix not found, trying alternative method...")
            raise Exception("Nix not available")
        
        # Install Colima via Nix
        subprocess.run("nix-env -iA nixpkgs.colima", shell=True, check=True)
        print("✓ Colima installed via Nix")
    
    def install_colima_direct_download(self):
        """Install Colima via direct download with Rosetta support"""
        print("Installing Colima via direct download...")
        
        # Use the latest version of Colima
        colima_version = "0.8.2"  # Latest stable version
        
        # Determine if we need Rosetta for Apple Silicon
        needs_rosetta = self.arch in ["arm64", "aarch64"]
        
        if needs_rosetta:
            print("Apple Silicon detected - ensuring Rosetta 2 is installed...")
            self.ensure_rosetta_installed()
        
        # Colima uses "arm64" for Apple Silicon, but let's try both architectures
        arch_variants = []
        if self.arch in ["arm64", "aarch64"]:
            arch_variants = ["arm64", "x86_64"]  # Try native first, then Intel
        else:
            arch_variants = ["x86_64"]
        
        # Try each architecture variant
        for arch in arch_variants:
            colima_url = f"https://github.com/abiosoft/colima/releases/download/v{colima_version}/colima-Darwin-{arch}"
            
            print(f"Trying to download Colima v{colima_version} for {arch}...")
            
            try:
                subprocess.run(f"curl -fsSL {colima_url} -o colima", shell=True, check=True)
                
                if arch == "x86_64" and needs_rosetta:
                    print("✓ Downloaded Intel binary for Apple Silicon (will run via Rosetta)")
                else:
                    print(f"✓ Downloaded {arch} binary")
                
                break  # Success, exit the loop
                
            except subprocess.CalledProcessError:
                print(f"Failed to download {arch} binary")
                if arch == arch_variants[-1]:  # Last attempt
                    raise Exception(f"Failed to download Colima for any architecture")
                continue
        
        print("Installing Colima...")
        subprocess.run("sudo mkdir -p /usr/local/bin", shell=True, check=True)
        subprocess.run("sudo mv colima /usr/local/bin/", shell=True, check=True)
        subprocess.run("sudo chmod +x /usr/local/bin/colima", shell=True, check=True)
        
        print("✓ Colima installed via direct download")
    
    def ensure_rosetta_installed(self):
        """Ensure Rosetta 2 is installed on Apple Silicon Macs"""
        try:
            # Check if Rosetta is already installed by trying to run an x86_64 binary
            result = subprocess.run("/usr/bin/arch -x86_64 /usr/bin/true", shell=True, capture_output=True)
            if result.returncode == 0:
                print("✓ Rosetta 2 already installed")
                return
        except:
            pass
        
        print("Installing Rosetta 2...")
        try:
            # Install Rosetta 2 silently
            subprocess.run("sudo softwareupdate --install-rosetta --agree-to-license", shell=True, check=True)
            print("✓ Rosetta 2 installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠ Rosetta 2 installation failed: {e}")
            print("You may need to install Rosetta 2 manually:")
            print("sudo softwareupdate --install-rosetta --agree-to-license")
    
    def check_nix_available(self):
        """Check if Nix package manager is available"""
        try:
            subprocess.run("nix --version", shell=True, check=True, capture_output=True)
            return True
        except:
            return False
    
    def install_docker_cli_mac(self):
        """Install Docker CLI on macOS"""
        try:
            # Check if Docker CLI is already installed
            subprocess.run("docker --version", shell=True, check=True)
            print("✓ Docker CLI already installed")
            return
        except subprocess.CalledProcessError:
            pass
        
        # Determine architecture
        arch = "x86_64" if self.arch in ["x86_64", "amd64"] else "aarch64"
        
        # Docker CLI binary URLs
        docker_version = "24.0.7"  # Latest stable
        docker_url = f"https://download.docker.com/mac/static/stable/{arch}/docker-{docker_version}.tgz"
        
        print(f"Downloading Docker CLI v{docker_version} for {arch}...")
        subprocess.run(f"curl -fsSL {docker_url} -o docker.tgz", shell=True, check=True)
        
        print("Extracting Docker CLI...")
        subprocess.run("tar -xzf docker.tgz", shell=True, check=True)
        
        print("Installing Docker CLI...")
        subprocess.run("sudo mkdir -p /usr/local/bin", shell=True, check=True)
        
        # Only install the docker client
        if os.path.exists("docker/docker"):
            subprocess.run("sudo cp docker/docker /usr/local/bin/", shell=True, check=True)
            subprocess.run("sudo chmod +x /usr/local/bin/docker", shell=True, check=True)
            print("✓ Installed Docker CLI")
        
        # Clean up
        subprocess.run("rm -rf docker docker.tgz", shell=True, check=False)
    
    def install_docker_compose_mac(self):
        """Install Docker Compose on macOS"""
        try:
            # Check if Docker Compose is already installed
            subprocess.run("docker-compose --version", shell=True, check=True)
            print("✓ Docker Compose already installed")
            return
        except subprocess.CalledProcessError:
            pass
        
        # Determine architecture
        arch_map = {
            "x86_64": "x86_64",
            "amd64": "x86_64",
            "arm64": "aarch64", 
            "aarch64": "aarch64"
        }
        arch = arch_map.get(self.arch, "x86_64")
        
        print("Getting latest Docker Compose version...")
        try:
            # Get latest version from GitHub API
            result = subprocess.run(
                'curl -s https://api.github.com/repos/docker/compose/releases/latest | grep "tag_name" | cut -d\'"\'"\' -f4',
                shell=True, capture_output=True, text=True, check=True
            )
            compose_version = result.stdout.strip()
        except:
            compose_version = "v2.23.3"  # Fallback version
        
        compose_url = f"https://github.com/docker/compose/releases/download/{compose_version}/docker-compose-darwin-{arch}"
        
        print(f"Downloading Docker Compose {compose_version} for {arch}...")
        subprocess.run(f"curl -fsSL {compose_url} -o docker-compose", shell=True, check=True)
        
        print("Installing Docker Compose...")
        subprocess.run("sudo mv docker-compose /usr/local/bin/", shell=True, check=True)
        subprocess.run("sudo chmod +x /usr/local/bin/docker-compose", shell=True, check=True)
        
        print("✓ Docker Compose installed successfully")
        
        # Add to PATH if needed
        self.add_to_path_mac("/usr/local/bin") #binary URLs
        try:
            docker_version = "24.0.7"  # Latest stable
            docker_url = f"https://download.docker.com/mac/static/stable/{arch}/docker-{docker_version}.tgz"
            
            print(f"Downloading Docker Engine for {arch}...")
            subprocess.run(f"curl -fsSL {docker_url} -o docker.tgz", shell=True, check=True)
            
            print("Extracting Docker binaries...")
            subprocess.run("tar -xzf docker.tgz", shell=True, check=True)
            
            print("Installing Docker binaries...")
            subprocess.run("sudo mkdir -p /usr/local/bin", shell=True, check=True)
            
            # List and copy only the files that exist
            result = subprocess.run("ls -1 docker/", shell=True, capture_output=True, text=True, check=True)
            docker_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            for docker_file in docker_files:
                if docker_file:  # Skip empty lines
                    src_path = f"docker/{docker_file}"
                    dst_path = f"/usr/local/bin/{docker_file}"
                    subprocess.run(f"sudo cp '{src_path}' '{dst_path}'", shell=True, check=True)
                    subprocess.run(f"sudo chmod +x '{dst_path}'", shell=True, check=True)
                    print(f"✓ Installed {docker_file}")
            
            # Install Docker Machine for macOS (needed to create Docker hosts)
            print("Installing Docker Machine...")
            machine_version = "0.16.2"
            
            # Docker Machine only has x86_64 builds, even for Apple Silicon
            # Apple Silicon Macs can run x86_64 binaries via Rosetta
            machine_arch = "x86_64"
            machine_url = f"https://github.com/docker/machine/releases/download/v{machine_version}/docker-machine-Darwin-{machine_arch}"
            
            try:
                subprocess.run(f"curl -fsSL {machine_url} -o docker-machine", shell=True, check=True)
                subprocess.run("sudo mv docker-machine /usr/local/bin/", shell=True, check=True)
                subprocess.run("sudo chmod +x /usr/local/bin/docker-machine", shell=True, check=True)
                print("✓ Docker Machine installed successfully")
            except subprocess.CalledProcessError:
                print("⚠ Docker Machine installation failed - you can install it manually later")
                print(f"Manual install: curl -L {machine_url} -o /usr/local/bin/docker-machine && chmod +x /usr/local/bin/docker-machine")
            
            # Install VirtualBox (alternative approach without Homebrew)
            print("Installing VirtualBox...")
            self.install_virtualbox_mac()
            
            # Clean up
            subprocess.run("rm -rf docker docker.tgz", shell=True, check=False)
            
            # Add to PATH if needed
            self.add_to_path_mac("/usr/local/bin")
            
            print("✓ Docker Engine installed successfully on macOS")
            print("\nNext steps:")
            print("1. Create a Docker machine: docker-machine create --driver virtualbox default")
            print("2. Configure environment: eval $(docker-machine env default)")
            print("3. Start using Docker: docker run hello-world")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Installation failed: {e}")
            return False
        
        return True
    
    def install_virtualbox_mac(self):
        """Install VirtualBox on macOS without Homebrew"""
        try:
            # Check if VirtualBox is already installed
            result = subprocess.run("VBoxManage --version", shell=True, capture_output=True)
            if result.returncode == 0:
                print("✓ VirtualBox already installed")
                return
            
            print("Downloading VirtualBox...")
            # Get latest VirtualBox version
            vbox_version = "7.0.12"
            vbox_build = "159484"
            vbox_url = f"https://download.virtualbox.org/virtualbox/{vbox_version}/VirtualBox-{vbox_version}-{vbox_build}-OSX.dmg"
            
            subprocess.run(f"curl -fsSL '{vbox_url}' -o VirtualBox.dmg", shell=True, check=True)
            
            print("Mounting and installing VirtualBox...")
            # Mount the DMG
            mount_result = subprocess.run("hdiutil attach VirtualBox.dmg -nobrowse -quiet", 
                                        shell=True, capture_output=True, text=True, check=True)
            
            # Find mount point
            mount_point = None
            for line in mount_result.stdout.split('\n'):
                if '/Volumes/VirtualBox' in line:
                    mount_point = '/Volumes/VirtualBox'
                    break
            
            if mount_point:
                # Install VirtualBox
                pkg_file = f"{mount_point}/VirtualBox.pkg"
                subprocess.run(f"sudo installer -pkg '{pkg_file}' -target /", shell=True, check=True)
                
                # Unmount
                subprocess.run(f"hdiutil detach '{mount_point}' -quiet", shell=True, check=False)
            else:
                raise Exception("Could not find VirtualBox mount point")
            
            # Clean up
            subprocess.run("rm -f VirtualBox.dmg", shell=True, check=False)
            
            print("✓ VirtualBox installed successfully")
            
        except Exception as e:
            print(f"⚠ VirtualBox installation failed: {e}")
            print("You may need to install VirtualBox manually from: https://www.virtualbox.org/")
    
    def add_to_path_mac(self, path_to_add):
        """Add directory to PATH in shell profiles"""
        shell_profiles = [
            os.path.expanduser("~/.bash_profile"),
            os.path.expanduser("~/.bashrc"),
            os.path.expanduser("~/.zshrc"),
            os.path.expanduser("~/.profile")
        ]
        
        path_line = f'export PATH="{path_to_add}:$PATH"'
        
        for profile in shell_profiles:
            if os.path.exists(profile):
                try:
                    with open(profile, 'r') as f:
                        content = f.read()
                    
                    if path_to_add not in content:
                        with open(profile, 'a') as f:
                            f.write(f'\n# Added by Docker installer\n{path_line}\n')
                        print(f"✓ Added to PATH in {profile}")
                except Exception as e:
                    print(f"⚠ Could not update {profile}: {e}")
                    
        # Also try to add to current session
        current_path = os.environ.get('PATH', '')
        if path_to_add not in current_path:
            os.environ['PATH'] = f"{path_to_add}:{current_path}"
    
    def uninstall_docker_mac(self):
        """Uninstall Docker Engine from macOS (Colima-based installation)"""
        print("Uninstalling Docker Engine from macOS...")
        
        try:
            # Stop Colima if running
            print("Stopping Colima...")
            try:
                subprocess.run("colima stop", shell=True, check=False)
                subprocess.run("colima delete --force", shell=True, check=False)
            except:
                pass
            
            # Remove Colima
            print("Removing Colima...")
            if os.path.exists("/usr/local/bin/colima"):
                subprocess.run("sudo rm -f /usr/local/bin/colima", shell=True, check=False)
                print("✓ Removed Colima")
            
            # Remove Lima
            print("Removing Lima...")
            lima_binaries = ["/usr/local/bin/limactl", "/usr/local/bin/lima"]
            for binary in lima_binaries:
                if os.path.exists(binary):
                    subprocess.run(f"sudo rm -f {binary}", shell=True, check=False)
                    print(f"✓ Removed {os.path.basename(binary)}")
            
            # Remove Docker CLI
            print("Removing Docker CLI...")
            if os.path.exists("/usr/local/bin/docker"):
                subprocess.run("sudo rm -f /usr/local/bin/docker", shell=True, check=False)
                print("✓ Removed Docker CLI")
            
            # Remove Docker Compose
            print("Removing Docker Compose...")
            if os.path.exists("/usr/local/bin/docker-compose"):
                subprocess.run("sudo rm -f /usr/local/bin/docker-compose", shell=True, check=False)
                print("✓ Removed Docker Compose")
            
            # Remove data directories
            data_dirs = [
                os.path.expanduser("~/.colima"),
                os.path.expanduser("~/.lima")
            ]
            
            for data_dir in data_dirs:
                if os.path.exists(data_dir):
                    subprocess.run(f"rm -rf '{data_dir}'", shell=True, check=False)
                    print(f"✓ Removed {os.path.basename(data_dir)} data directory")
            
            # Remove Docker contexts
            print("Cleaning up Docker contexts...")
            try:
                subprocess.run("docker context rm colima-default", shell=True, check=False)
            except:
                pass
            
            # Clean up PATH entries (remove lines added by installer)
            self.remove_from_path_mac("/usr/local/bin")
            
            print("✓ Docker Engine uninstalled successfully from macOS")
            print("\nColima, Lima, and Docker have been completely removed.")
            
        except Exception as e:
            print(f"✗ Uninstallation failed: {e}")
            return False
        
        return True
    
    def uninstall_docker_windows(self):
        """Uninstall Docker Engine from Windows"""
        print("Uninstalling Docker Engine from Windows...")
        
        try:
            # Stop Docker service in WSL2
            print("Stopping Docker service...")
            subprocess.run('wsl -e bash -c "sudo service docker stop"', shell=True, check=False)
            subprocess.run('wsl -e bash -c "sudo systemctl disable docker"', shell=True, check=False)
            
            # Remove Docker from WSL2
            print("Removing Docker from WSL2...")
            wsl_commands = [
                "sudo apt-get remove -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
                "sudo apt-get autoremove -y",
                "sudo rm -rf /var/lib/docker",
                "sudo rm -rf /etc/docker",
                "sudo groupdel docker"
            ]
            
            for cmd in wsl_commands:
                wsl_cmd = f'wsl -e bash -c "{cmd}"'
                subprocess.run(wsl_cmd, shell=True, check=False)
            
            print("✓ Docker Engine uninstalled successfully from Windows")
            print("\nNote: WSL2 and Ubuntu distribution were not removed.")
            print("To completely remove WSL2: wsl --unregister Ubuntu-22.04")
            
        except Exception as e:
            print(f"✗ Uninstallation failed: {e}")
            return False
        
        return True
    
    def remove_from_path_mac(self, path_to_remove):
        """Remove directory from PATH in shell profiles"""
        shell_profiles = [
            os.path.expanduser("~/.bash_profile"),
            os.path.expanduser("~/.bashrc"),
            os.path.expanduser("~/.zshrc"),
            os.path.expanduser("~/.profile")
        ]
        
        for profile in shell_profiles:
            if os.path.exists(profile):
                try:
                    with open(profile, 'r') as f:
                        lines = f.readlines()
                    
                    # Remove lines containing the Docker installer comment or the path
                    filtered_lines = []
                    skip_next = False
                    
                    for line in lines:
                        if "# Added by Docker installer" in line:
                            skip_next = True
                            continue
                        elif skip_next and path_to_remove in line:
                            skip_next = False
                            continue
                        else:
                            skip_next = False
                            filtered_lines.append(line)
                    
                    if len(filtered_lines) != len(lines):
                        with open(profile, 'w') as f:
                            f.writelines(filtered_lines)
                        print(f"✓ Cleaned up PATH in {profile}")
                        
                except Exception as e:
                    print(f"⚠ Could not clean {profile}: {e}")
    
    def uninstall(self):
        """Main uninstallation method"""
        print(f"Docker Engine Uninstaller for {self.system.title()}")
        print("=" * 50)
        
        # Check if Docker is installed
        if not self.check_docker_installation():
            print("Docker is not installed or not found in PATH")
            return True
        
        # Confirm uninstallation if not in silent mode
        if not self.silent:
            response = input("Are you sure you want to uninstall Docker Engine? (y/N): ")
            if response.lower() != 'y':
                print("Uninstallation cancelled")
                return True
        
        # Uninstall based on OS
        if self.system == "darwin":  # macOS
            return self.uninstall_docker_mac()
        elif self.system == "windows":
            return self.uninstall_docker_windows()
        else:
            print(f"✗ Unsupported operating system for uninstall: {self.system}")
            return False
    
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
        if self.uninstall_mode:
            return self.uninstall()
            
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
    parser = argparse.ArgumentParser(
        description="Docker Engine installer for Mac and Windows (without Desktop GUI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install_docker_engine.py           # Install Docker Engine
  python install_docker_engine.py --uninstall  # Uninstall Docker Engine
        """
    )
    parser.add_argument(
        "--uninstall", 
        action="store_true", 
        help="Uninstall Docker Engine instead of installing"
    )
    
    args = parser.parse_args()
    
    try:
        installer = DockerEngineInstaller(uninstall_mode=args.uninstall)
        success = installer.install()  # This will call uninstall() if in uninstall mode
        
        if success:
            action = "uninstallation" if args.uninstall else "installation"
            print(f"\n🎉 Docker Engine {action} completed!")
        else:
            action = "uninstallation" if args.uninstall else "installation"
            print(f"\n❌ Docker Engine {action} failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        action = "Uninstallation" if args.uninstall else "Installation"
        print(f"\n\n{action} cancelled by user")
        sys.exit(1)
    except Exception as e:
        action = "uninstallation" if args.uninstall else "installation"
        print(f"\n❌ Unexpected error during {action}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()