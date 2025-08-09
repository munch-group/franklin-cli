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
        """Install Docker Engine on macOS without Homebrew"""
        print("Installing Docker Engine on macOS (without Homebrew)...")
        
        try:
            # Determine architecture
            arch = "x86_64" if self.arch in ["x86_64", "amd64"] else "aarch64"
            
            # Docker Engine binary URLs
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
            machine_arch = "x86_64" if arch == "x86_64" else "arm64"
            machine_version = "0.16.2"
            machine_url = f"https://github.com/docker/machine/releases/download/v{machine_version}/docker-machine-Darwin-{machine_arch}"
            
            subprocess.run(f"curl -fsSL {machine_url} -o docker-machine", shell=True, check=True)
            subprocess.run("sudo mv docker-machine /usr/local/bin/", shell=True, check=True)
            subprocess.run("sudo chmod +x /usr/local/bin/docker-machine", shell=True, check=True)
            
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
        """Uninstall Docker Engine from macOS"""
        print("Uninstalling Docker Engine from macOS...")
        
        try:
            # Stop any running Docker machines
            print("Stopping Docker machines...")
            try:
                result = subprocess.run("docker-machine ls -q", shell=True, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    machines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                    for machine in machines:
                        print(f"Stopping machine: {machine}")
                        subprocess.run(f"docker-machine stop {machine}", shell=True, check=False)
                        subprocess.run(f"docker-machine rm -f {machine}", shell=True, check=False)
            except:
                pass
            
            # Remove Docker binaries
            print("Removing Docker binaries...")
            docker_binaries = [
                "/usr/local/bin/docker",
                "/usr/local/bin/dockerd",
                "/usr/local/bin/docker-init",
                "/usr/local/bin/docker-proxy",
                "/usr/local/bin/containerd",
                "/usr/local/bin/containerd-shim",
                "/usr/local/bin/containerd-shim-runc-v2",
                "/usr/local/bin/ctr",
                "/usr/local/bin/runc",
                "/usr/local/bin/docker-machine"
            ]
            
            for binary in docker_binaries:
                if os.path.exists(binary):
                    subprocess.run(f"sudo rm -f {binary}", shell=True, check=False)
                    print(f"✓ Removed {binary}")
            
            # Remove Docker Machine data
            docker_machine_dir = os.path.expanduser("~/.docker/machine")
            if os.path.exists(docker_machine_dir):
                subprocess.run(f"rm -rf '{docker_machine_dir}'", shell=True, check=False)
                print("✓ Removed Docker Machine data")
            
            # Clean up PATH entries (remove lines added by installer)
            self.remove_from_path_mac("/usr/local/bin")
            
            print("Docker Engine uninstalled successfully from macOS")
            print("\nNote: VirtualBox was not removed. Uninstall manually if no longer needed:")
            print("sudo /Applications/VirtualBox.app/Contents/MacOS/VirtualBox_Uninstall_Tool.sh")
            
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
            
            print("Docker Engine uninstalled successfully from Windows")
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
            
            print("Docker Engine installed successfully on Windows")
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
            print(f"\nDocker Engine {action} failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        action = "Uninstallation" if args.uninstall else "Installation"
        print(f"\n\n{action} cancelled by user")
        sys.exit(1)
    except Exception as e:
        action = "uninstallation" if args.uninstall else "installation"
        print(f"\nUnexpected error during {action}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()