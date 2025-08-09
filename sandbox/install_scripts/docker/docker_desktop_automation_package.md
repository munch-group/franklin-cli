# Docker Desktop Automation Package

Complete collection of scripts and documentation for automated Docker Desktop installation, configuration, and management on Windows and macOS.

## Package Contents

```
docker-desktop-automation/
├── README.md                           # This file - overview and instructions
├── windows/
│   ├── install-docker-desktop.ps1     # Windows PowerShell script
│   ├── docker-desktop-functions.ps1   # Windows helper functions
│   └── README-Windows.md               # Windows-specific documentation
├── macos/
│   ├── install-docker-desktop.sh      # macOS bash script
│   └── README-macOS.md                 # macOS-specific documentation
├── docs/
│   ├── Windows-Configuration-Guide.md # Comprehensive Windows guide
│   ├── macOS-Configuration-Guide.md   # Comprehensive macOS guide
│   └── Configuration-Settings.md      # Settings reference
└── examples/
    ├── enterprise-config.json         # Example enterprise configuration
    └── personal-config.json           # Example personal configuration
```

## Quick Start

### Windows
```powershell
# Run as Administrator
.\windows\install-docker-desktop.ps1

# With custom organization
.\windows\install-docker-desktop.ps1 -OrganizationName "YourCompany"

# Uninstall
.\windows\install-docker-desktop.ps1 -CleanUninstall
```

### macOS
```bash
# Standard installation
./macos/install-docker-desktop.sh

# Clean uninstall
./macos/install-docker-desktop.sh --clean-uninstall

# Check status
./macos/install-docker-desktop.sh --status
```

---

## File: windows/install-docker-desktop.ps1

```powershell
param(
    [string]$OrganizationName = "",
    [switch]$EnableWSL2 = $true,
    [switch]$DisableAnalytics = $true,
    [switch]$AutoRepairWSL = $true,
    [switch]$Uninstall = $false,
    [switch]$CleanUninstall = $false
)

# Verify administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Administrator privileges required"
    exit 1
}

function Remove-DockerDesktop {
    param(
        [switch]$KeepUserData = $false,
        [switch]$KeepWSLDistros = $false
    )
    
    Write-Host "Starting Docker Desktop uninstallation..." -ForegroundColor Yellow
    
    try {
        # Stop Docker Desktop and related services
        Write-Host "Stopping Docker Desktop services..." -ForegroundColor Yellow
        
        # Stop Docker Desktop application
        Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force
        Get-Process -Name "com.docker.backend" -ErrorAction SilentlyContinue | Stop-Process -Force
        Get-Process -Name "com.docker.proxy" -ErrorAction SilentlyContinue | Stop-Process -Force
        Get-Process -Name "vpnkit" -ErrorAction SilentlyContinue | Stop-Process -Force
        
        # Stop Docker service
        $service = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
        if ($service) {
            Stop-Service -Name "com.docker.service" -Force
            Set-Service -Name "com.docker.service" -StartupType Disabled
        }
        
        # Stop and remove WSL distros if requested
        if (-not $KeepWSLDistros) {
            Write-Host "Removing Docker WSL distros..." -ForegroundColor Yellow
            wsl --unregister docker-desktop 2>$null
            wsl --unregister docker-desktop-data 2>$null
        }
        
        # Uninstall Docker Desktop
        Write-Host "Uninstalling Docker Desktop..." -ForegroundColor Yellow
        
        # Try uninstalling via Windows Apps first
        $dockerApp = Get-WmiObject -Class Win32_Product | Where-Object { $_.Name -like "*Docker Desktop*" }
        if ($dockerApp) {
            $dockerApp.Uninstall() | Out-Null
        }
        
        # Fallback: Try MSI uninstall
        $uninstallKeys = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
        )
        
        foreach ($keyPath in $uninstallKeys) {
            $apps = Get-ItemProperty $keyPath -ErrorAction SilentlyContinue
            $dockerApp = $apps | Where-Object { $_.DisplayName -like "*Docker Desktop*" }
            
            if ($dockerApp) {
                foreach ($app in $dockerApp) {
                    if ($app.UninstallString) {
                        Write-Host "Running uninstaller: $($app.UninstallString)" -ForegroundColor Cyan
                        $uninstallArgs = $app.UninstallString -replace "msiexec.exe", "" -replace "/I", "/X"
                        Start-Process "msiexec.exe" -ArgumentList "$uninstallArgs /quiet /norestart" -Wait
                    }
                }
            }
        }
        
        # Remove installation directories
        Write-Host "Removing Docker Desktop files..." -ForegroundColor Yellow
        
        $installPaths = @(
            "${env:ProgramFiles}\Docker",
            "${env:ProgramFiles(x86)}\Docker",
            "${env:ProgramData}\Docker",
            "${env:ProgramData}\DockerDesktop"
        )
        
        foreach ($path in $installPaths) {
            if (Test-Path $path) {
                Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "Removed: $path" -ForegroundColor Green
            }
        }
        
        # Remove user data if requested
        if (-not $KeepUserData) {
            Write-Host "Removing user data..." -ForegroundColor Yellow
            
            $userPaths = @(
                "$env:APPDATA\Docker",
                "$env:LOCALAPPDATA\Docker",
                "$env:USERPROFILE\.docker"
            )
            
            foreach ($path in $userPaths) {
                if (Test-Path $path) {
                    Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
                    Write-Host "Removed: $path" -ForegroundColor Green
                }
            }
        }
        
        # Remove registry entries
        Write-Host "Cleaning registry entries..." -ForegroundColor Yellow
        
        $registryPaths = @(
            "HKCU:\SOFTWARE\Docker Inc.",
            "HKLM:\SOFTWARE\Docker Inc.",
            "HKLM:\SOFTWARE\WOW6432Node\Docker Inc.",
            "HKLM:\SYSTEM\CurrentControlSet\Services\com.docker.service"
        )
        
        foreach ($regPath in $registryPaths) {
            if (Test-Path $regPath) {
                Remove-Item $regPath -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "Removed registry: $regPath" -ForegroundColor Green
            }
        }
        
        # Remove from docker-users group
        Write-Host "Removing users from docker-users group..." -ForegroundColor Yellow
        try {
            $group = Get-LocalGroup -Name "docker-users" -ErrorAction SilentlyContinue
            if ($group) {
                $members = Get-LocalGroupMember -Group "docker-users" -ErrorAction SilentlyContinue
                foreach ($member in $members) {
                    Remove-LocalGroupMember -Group "docker-users" -Member $member.Name -ErrorAction SilentlyContinue
                }
                Remove-LocalGroup -Name "docker-users" -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Warning "Could not clean up docker-users group: $($_.Exception.Message)"
        }
        
        # Remove Windows features if no other VM software depends on them
        $confirmation = Read-Host "Remove Hyper-V and Virtual Machine Platform features? This may affect other virtualization software (y/N)"
        if ($confirmation -eq "y" -or $confirmation -eq "Y") {
            Write-Host "Disabling Windows virtualization features..." -ForegroundColor Yellow
            dism.exe /online /disable-feature /featurename:Microsoft-Hyper-V-All /norestart
            dism.exe /online /disable-feature /featurename:VirtualMachinePlatform /norestart
            dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart
        }
        
        # Clean up firewall rules
        Write-Host "Removing Docker firewall rules..." -ForegroundColor Yellow
        Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*Docker*" } | Remove-NetFirewallRule -ErrorAction SilentlyContinue
        
        Write-Host "Docker Desktop uninstallation completed successfully!" -ForegroundColor Green
        Write-Host "A system restart is recommended to complete the removal process." -ForegroundColor Yellow
        
    } catch {
        Write-Error "Uninstallation failed: $($_.Exception.Message)"
        return $false
    }
    
    return $true
}

function Get-DockerInstallationStatus {
    Write-Host "=== Docker Desktop Installation Status ===" -ForegroundColor Cyan
    
    # Check if Docker Desktop is installed
    $dockerExe = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    $dockerInstalled = Test-Path $dockerExe
    
    Write-Host "Docker Desktop Installed: $dockerInstalled" -ForegroundColor $(if ($dockerInstalled) { "Green" } else { "Red" })
    
    if ($dockerInstalled) {
        $version = (Get-Item $dockerExe).VersionInfo.FileVersion
        Write-Host "Version: $version" -ForegroundColor White
    }
    
    # Check Docker service
    $service = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
    if ($service) {
        Write-Host "Docker Service Status: $($service.Status)" -ForegroundColor White
        Write-Host "Docker Service Startup: $($service.StartType)" -ForegroundColor White
    } else {
        Write-Host "Docker Service: Not found" -ForegroundColor Red
    }
    
    # Check WSL distros
    Write-Host "`nWSL Docker Distros:" -ForegroundColor Yellow
    try {
        $distros = wsl --list --quiet 2>$null
        $dockerDistros = $distros | Where-Object { $_ -match "docker" }
        if ($dockerDistros) {
            $dockerDistros | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
        } else {
            Write-Host "  No Docker WSL distros found" -ForegroundColor Red
        }
    } catch {
        Write-Host "  WSL not available" -ForegroundColor Red
    }
    
    # Check user groups
    try {
        $group = Get-LocalGroup -Name "docker-users" -ErrorAction SilentlyContinue
        if ($group) {
            $members = Get-LocalGroupMember -Group "docker-users" -ErrorAction SilentlyContinue
            Write-Host "`nDocker Users Group Members:" -ForegroundColor Yellow
            if ($members) {
                $members | ForEach-Object { Write-Host "  $($_.Name)" -ForegroundColor Green }
            } else {
                Write-Host "  No members" -ForegroundColor Red
            }
        } else {
            Write-Host "`nDocker Users Group: Not found" -ForegroundColor Red
        }
    } catch {
        Write-Host "`nDocker Users Group: Could not check" -ForegroundColor Red
    }
    
    # Check data directories
    Write-Host "`nData Directories:" -ForegroundColor Yellow
    $dataPaths = @(
        "$env:APPDATA\Docker",
        "$env:LOCALAPPDATA\Docker", 
        "$env:ProgramData\Docker",
        "$env:USERPROFILE\.docker"
    )
    
    foreach ($path in $dataPaths) {
        $exists = Test-Path $path
        $size = if ($exists) { 
            try {
                $folderSize = (Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
                "{0:N2} MB" -f ($folderSize / 1MB)
            } catch { "Unknown" }
        } else { "N/A" }
        
        Write-Host "  $path : $exists ($size)" -ForegroundColor $(if ($exists) { "Green" } else { "Red" })
    }
}

# Handle uninstall operations
if ($Uninstall -or $CleanUninstall) {
    Write-Host "Docker Desktop Uninstallation" -ForegroundColor Red
    Write-Host "==============================" -ForegroundColor Red
    
    # Show current installation status
    Get-DockerInstallationStatus
    
    Write-Host "`nUninstall Options:" -ForegroundColor Yellow
    Write-Host "- Standard uninstall: Removes Docker Desktop but keeps user data and WSL distros" -ForegroundColor White
    Write-Host "- Clean uninstall: Removes everything including user data and WSL distros" -ForegroundColor White
    
    $confirmUninstall = Read-Host "`nProceed with uninstallation? (yes/no)"
    if ($confirmUninstall -ne "yes") {
        Write-Host "Uninstallation cancelled" -ForegroundColor Yellow
        exit 0
    }
    
    if ($CleanUninstall) {
        $result = Remove-DockerDesktop
    } else {
        $result = Remove-DockerDesktop -KeepUserData -KeepWSLDistros
    }
    
    if ($result) {
        Write-Host "`nFinal status check:" -ForegroundColor Cyan
        Get-DockerInstallationStatus
    }
    
    exit $(if ($result) { 0 } else { 1 })
}

# Enable Windows features for WSL2
if ($EnableWSL2) {
    Write-Host "Enabling WSL2 features..." -ForegroundColor Yellow
    
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    
    # Download and install WSL2 kernel
    $wslKernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
    $wslKernelPath = "$env:TEMP\wsl_update_x64.msi"
    Invoke-WebRequest -Uri $wslKernelUrl -OutFile $wslKernelPath
    Start-Process msiexec.exe -Wait -ArgumentList "/I $wslKernelPath /quiet"
    
    # Set WSL default version and handle any errors
    try {
        wsl --set-default-version 2
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "WSL default version setting may have failed. Will retry after Docker installation."
        }
    } catch {
        Write-Warning "WSL configuration will be handled during Docker setup"
    }
}

# Download and install Docker Desktop
Write-Host "Downloading Docker Desktop..." -ForegroundColor Yellow
$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker Desktop Installer.exe"
$dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller

$installArgs = @('install', '--quiet', '--accept-license', '--backend=wsl-2')
if ($OrganizationName) {
    $installArgs += "--allowed-org=$OrganizationName"
}

Write-Host "Installing Docker Desktop..." -ForegroundColor Yellow
Start-Process $dockerInstaller -Wait -ArgumentList $installArgs

# Add current user to docker-users group
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Add-LocalGroupMember -Group "docker-users" -Member $currentUser -ErrorAction SilentlyContinue

# Configure Docker Desktop settings
Write-Host "Configuring Docker Desktop settings..." -ForegroundColor Yellow

$dockerConfig = @{
    AutoDownloadUpdates = -not $DisableAnalytics
    AutoPauseTimedActivitySeconds = 30
    AutoPauseTimeoutSeconds = 300
    AutoStart = $false
    Cpus = 5
    DisplayedOnboarding = $true
    EnableIntegrityCheck = $true
    FilesharingDirectories = @(
        "/Users",
        "/Volumes", 
        "/private",
        "/tmp",
        "/var/folders"
    )
    MemoryMiB = 8000
    DiskSizeMiB = 25000
    OpenUIOnStartupDisabled = $true
    ShowAnnouncementNotifications = $true
    ShowGeneralNotifications = $true
    SwapMiB = 1024
    UseCredentialHelper = $true
    UseResourceSaver = $false
}

# Configure analytics settings if requested
if ($DisableAnalytics) {
    $settingsPath = "$env:APPDATA\Docker\settings-store.json"
    if (Test-Path $settingsPath) {
        try {
            $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
            $settings | Add-Member -Type NoteProperty -Name analyticsEnabled -Value $false -Force
            $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath
            Write-Host "Analytics disabled" -ForegroundColor Green
        } catch {
            Write-Warning "Could not disable analytics in settings file"
        }
    }
}

Write-Host "`nInstallation and configuration complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart your computer to ensure group membership takes effect" -ForegroundColor White
Write-Host "2. Start Docker Desktop manually or it will auto-start based on your settings" -ForegroundColor White

if ($EnableWSL2) {
    Write-Host "3. Verify WSL2 integration by running: docker run hello-world" -ForegroundColor White
    
    # Show current WSL status
    Write-Host "`nCurrent WSL status:" -ForegroundColor Cyan
    try {
        wsl --list --verbose
    } catch {
        Write-Host "Could not retrieve WSL status. This is normal if WSL was just installed." -ForegroundColor Yellow
    }
}

Write-Host "`nTo uninstall Docker Desktop later, run this script with -Uninstall or -CleanUninstall" -ForegroundColor Cyan
```

---

## File: macos/install-docker-desktop.sh

```bash
#!/bin/bash
set -euo pipefail

# Configuration
INSTALL_METHOD="dmg"  # Options: dmg, homebrew
USERNAME=$(whoami)
LOG_FILE="/tmp/docker_install.log"
DOCKER_SETTINGS_DIR="$HOME/Library/Group Containers/group.com.docker"
DOCKER_SETTINGS_FILE="$DOCKER_SETTINGS_DIR/settings-store.json"
BACKUP_DIR="$HOME/.docker/config-backups"

# Command line options
UNINSTALL=false
CLEAN_UNINSTALL=false
STATUS_CHECK=false
CONFIGURE_ONLY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --clean-uninstall)
            CLEAN_UNINSTALL=true
            shift
            ;;
        --status)
            STATUS_CHECK=true
            shift
            ;;
        --configure-only)
            CONFIGURE_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --uninstall        Remove Docker Desktop (keep user data)"
            echo "  --clean-uninstall  Remove Docker Desktop and all data"
            echo "  --status          Show installation status"
            echo "  --configure-only  Only configure existing installation"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_requirements() {
    MACOS_VERSION=$(sw_vers -productVersion)
    MAJOR_VERSION=$(echo $MACOS_VERSION | cut -d. -f1)
    
    if [[ $MAJOR_VERSION -lt 13 ]]; then
        log "ERROR: macOS 13.0 (Ventura) or later required"
        exit 1
    fi
    
    AVAILABLE_SPACE=$(df -g / | tail -1 | awk '{print $4}')
    if [[ $AVAILABLE_SPACE -lt 10 ]]; then
        log "ERROR: Insufficient disk space"
        exit 1
    fi
}

get_installation_status() {
    echo "=== Docker Desktop Installation Status ==="
    
    # Check if Docker Desktop is installed
    local docker_app="/Applications/Docker.app"
    local docker_installed=false
    
    if [[ -d "$docker_app" ]]; then
        docker_installed=true
        echo "✅ Docker Desktop: Installed"
        
        # Get version info
        local version_plist="$docker_app/Contents/Info.plist"
        if [[ -f "$version_plist" ]]; then
            local version=$(defaults read "$version_plist" CFBundleShortVersionString 2>/dev/null || echo "Unknown")
            echo "   Version: $version"
        fi
    else
        echo "❌ Docker Desktop: Not installed"
    fi
    
    # Check if Docker is running
    if pgrep -x "Docker Desktop" > /dev/null; then
        echo "✅ Docker Desktop: Running"
    else
        echo "⚠️  Docker Desktop: Not running"
    fi
    
    # Check Docker daemon
    if command -v docker &> /dev/null; then
        if docker info &>/dev/null; then
            echo "✅ Docker Daemon: Running"
        else
            echo "⚠️  Docker Daemon: Not accessible"
        fi
    else
        echo "❌ Docker CLI: Not found"
    fi
    
    # Check privileged helper
    local helper_plist="/Library/LaunchDaemons/com.docker.vmnetd.plist"
    if [[ -f "$helper_plist" ]]; then
        echo "✅ Privileged Helper: Installed"
        if launchctl list | grep -q com.docker.vmnetd; then
            echo "   Status: Running"
        else
            echo "   Status: Not running"
        fi
    else
        echo "❌ Privileged Helper: Not installed"
    fi
    
    # Check configuration files
    echo ""
    echo "Configuration Files:"
    if [[ -f "$DOCKER_SETTINGS_FILE" ]]; then
        echo "✅ Settings file: $DOCKER_SETTINGS_FILE"
        local size=$(stat -f%z "$DOCKER_SETTINGS_FILE" 2>/dev/null || echo "0")
        echo "   Size: $size bytes"
    else
        echo "❌ Settings file: Not found"
    fi
    
    # Check data usage
    echo ""
    echo "Data Usage:"
    local data_paths=(
        "$DOCKER_SETTINGS_DIR"
        "$HOME/.docker"
        "/var/lib/docker"
    )
    
    for path in "${data_paths[@]}"; do
        if [[ -d "$path" ]]; then
            local size=$(du -sh "$path" 2>/dev/null | cut -f1 || echo "Unknown")
            echo "✅ $path: $size"
        else
            echo "❌ $path: Not found"
        fi
    done
    
    # Check VM disk image
    local vm_disk="$DOCKER_SETTINGS_DIR/Data/vms/0/data/Docker.raw"
    if [[ -f "$vm_disk" ]]; then
        local vm_size=$(du -sh "$vm_disk" 2>/dev/null | cut -f1 || echo "Unknown")
        echo "✅ VM Disk: $vm_size"
    else
        echo "❌ VM Disk: Not found"
    fi
}

uninstall_docker_desktop() {
    local keep_user_data=${1:-false}
    
    log "Starting Docker Desktop uninstallation..."
    
    # Stop Docker Desktop
    log "Stopping Docker Desktop..."
    osascript -e 'quit app "Docker"' 2>/dev/null || true
    
    # Wait for processes to stop
    local count=0
    while pgrep -x "Docker Desktop" > /dev/null && [[ $count -lt 30 ]]; do
        sleep 1
        ((count++))
    done
    
    # Force kill if still running
    if pgrep -x "Docker Desktop" > /dev/null; then
        log "Force killing Docker Desktop processes..."
        pkill -9 "Docker Desktop" 2>/dev/null || true
        pkill -9 "com.docker" 2>/dev/null || true
    fi
    
    # Remove application
    local docker_app="/Applications/Docker.app"
    if [[ -d "$docker_app" ]]; then
        log "Removing Docker Desktop application..."
        rm -rf "$docker_app"
        echo "✅ Removed: $docker_app"
    fi
    
    # Remove privileged helper
    local helper_plist="/Library/LaunchDaemons/com.docker.vmnetd.plist"
    if [[ -f "$helper_plist" ]]; then
        log "Removing privileged helper..."
        sudo launchctl unload "$helper_plist" 2>/dev/null || true
        sudo rm -f "$helper_plist"
        sudo rm -f "/Library/PrivilegedHelperTools/com.docker.vmnetd"
        echo "✅ Removed privileged helper"
    fi
    
    # Remove symlinks
    local symlinks=(
        "/usr/local/bin/docker"
        "/usr/local/bin/docker-compose"
        "/usr/local/bin/docker-credential-desktop"
        "/usr/local/bin/docker-credential-ecr-login"
        "/usr/local/bin/docker-credential-osxkeychain"
        "/var/run/docker.sock"
    )
    
    for symlink in "${symlinks[@]}"; do
        if [[ -L "$symlink" ]]; then
            sudo rm -f "$symlink"
            echo "✅ Removed symlink: $symlink"
        fi
    done
    
    # Remove user data if requested
    if [[ "$keep_user_data" != "true" ]]; then
        log "Removing user data..."
        
        local user_paths=(
            "$DOCKER_SETTINGS_DIR"
            "$HOME/.docker"
            "$HOME/Library/Containers/com.docker.docker"
            "$HOME/Library/Application Support/Docker Desktop"
            "$HOME/Library/Preferences/com.docker.docker.plist"
            "$HOME/Library/Preferences/com.electron.docker-frontend.plist"
            "$HOME/Library/Saved Application State/com.electron.docker-frontend.savedState"
            "$HOME/Library/Logs/Docker Desktop"
            "$HOME/Library/Caches/com.docker.docker"
        )
        
        for path in "${user_paths[@]}"; do
            if [[ -e "$path" ]]; then
                rm -rf "$path"
                echo "✅ Removed: $path"
            fi
        done
    else
        log "Keeping user data (use --clean-uninstall to remove all data)"
    fi
    
    # Remove system data
    log "Removing system data..."
    local system_paths=(
        "/var/lib/docker"
        "/Library/Logs/Docker Desktop"
        "/tmp/docker.sock"
    )
    
    for path in "${system_paths[@]}"; do
        if [[ -e "$path" ]]; then
            sudo rm -rf "$path" 2>/dev/null || true
            echo "✅ Removed: $path"
        fi
    done
    
    # Clean up processes and kernel extensions
    log "Cleaning up system resources..."
    
    # Remove any remaining Docker processes
    pkill -f "docker" 2>/dev/null || true
    pkill -f "com.docker" 2>/dev/null || true
    
    # Clean up network interfaces (Docker creates these)
    sudo ifconfig bridge0 down 2>/dev/null || true
    
    log "Docker Desktop uninstallation completed!"
    echo ""
    echo "Uninstallation Summary:"
    echo "✅ Docker Desktop application removed"
    echo "✅ Privileged helper removed"
    echo "✅ System symlinks removed"
    
    if [[ "$keep_user_data" != "true" ]]; then
        echo "✅ User data removed"
    else
        echo "⚠️  User data preserved"
    fi
    
    echo ""
    echo "You may want to restart your Mac to ensure all resources are cleaned up."
}

install_via_dmg() {
    ARCH=$(uname -m)
    if [[ $ARCH == "arm64" ]]; then
        DOWNLOAD_URL="https://desktop.docker.com/mac/main/arm64/Docker.dmg"
    else
        DOWNLOAD_URL="https://desktop.docker.com/mac/main/amd64/Docker.dmg"
    fi
    
    log "Downloading Docker Desktop for $ARCH"
    curl -L -o /tmp/Docker.dmg "$DOWNLOAD_URL"
    
    log "Installing Docker Desktop"
    sudo hdiutil attach /tmp/Docker.dmg -nobrowse
    sudo /Volumes/Docker/Docker.app/Contents/MacOS/install \
        --accept-license --user="$USERNAME"
    sudo hdiutil detach /Volumes/Docker
    rm -f /tmp/Docker.dmg
}

configure_docker_desktop() {
    log "Configuring Docker Desktop settings..."
    
    # Ensure Docker Desktop has run at least once
    if [[ ! -f "$DOCKER_SETTINGS_FILE" ]]; then
        log "Launching Docker Desktop for initial setup..."
        open -a Docker
        
        # Wait up to 3 minutes for settings file creation
        local count=0
        while [[ ! -f "$DOCKER_SETTINGS_FILE" ]] && [[ $count -lt 180 ]]; do
            sleep 1
            ((count++))
        done
        
        if [[ ! -f "$DOCKER_SETTINGS_FILE" ]]; then
            log "ERROR: Settings file not created after 3 minutes"
            exit 1
        fi
    fi
    
    # Create backup
    mkdir -p "$BACKUP_DIR"
    cp "$DOCKER_SETTINGS_FILE" "$BACKUP_DIR/settings-$(date +%Y%m%d-%H%M%S).json"
    
    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        log "Installing jq for JSON manipulation..."
        if command -v brew &> /dev/null; then
            brew install jq
        else
            log "ERROR: jq is required but not available. Please install Homebrew or jq manually."
            exit 1
        fi
    fi
    
    # Apply configuration using jq
    local temp_file=$(mktemp)
    
    # Configure Docker Desktop settings to match your requirements
    jq '.memoryMiB = 8000 |
        .cpus = 5 |
        .diskSizeMiB = 25000 |
        .swapMiB = 1024 |
        .autoStart = false |
        .openUIOnStartupDisabled = true |
        .displayedOnboarding = true |
        .enableIntegrityCheck = true |
        .showAnnouncementNotifications = true |
        .showGeneralNotifications = true |
        .useCredentialHelper = true |
        .useResourceSaver = false |
        .autoPauseTimeoutSeconds = 300 |
        .disableUpdate = true |
        .filesharingDirectories = ["/Users", "/Volumes", "/private", "/tmp", "/var/folders"]' \
        "$DOCKER_SETTINGS_FILE" > "$temp_file"
    
    # Apply Apple Silicon optimizations if available
    if [[ $(uname -m) == "arm64" ]]; then
        jq '.useVirtualizationFramework = true |
            .useVirtualizationFrameworkVirtioFS = true |
            .useVirtualizationFrameworkRosetta = true' \
            "$temp_file" > "${temp_file}.arm64" && mv "${temp_file}.arm64" "$temp_file"
    fi
    
    # Validate JSON before replacement
    if jq empty "$temp_file" 2>/dev/null; then
        mv "$temp_file" "$DOCKER_SETTINGS_FILE"
        log "Configuration applied successfully"
        
        # Restart Docker Desktop to apply changes
        log "Restarting Docker Desktop to apply configuration..."
        osascript -e 'quit app "Docker"' 2>/dev/null || true
        sleep 3
        open -a Docker
        
        # Wait for Docker to be ready
        local count=0
        while [[ $count -lt 60 ]]; do
            if docker info &>/dev/null; then
                log "Docker Desktop restarted and ready"
                break
            fi
            sleep 2
            ((count+=2))
        done
        
    else
        rm "$temp_file"
        log "ERROR: Generated configuration is invalid JSON"
        exit 1
    fi
}

# Main execution logic
main() {
    if [[ "$STATUS_CHECK" == "true" ]]; then
        get_installation_status
        exit 0
    fi
    
    if [[ "$UNINSTALL" == "true" ]] || [[ "$CLEAN_UNINSTALL" == "true" ]]; then
        echo "Docker Desktop Uninstallation"
        echo "=============================="
        echo ""
        
        # Show current status
        get_installation_status
        echo ""
        
        local keep_data="true"
        if [[ "$CLEAN_UNINSTALL" == "true" ]]; then
            keep_data="false"
            echo "⚠️  CLEAN UNINSTALL: This will remove ALL Docker data including:"
            echo "   - Container images and volumes"
            echo "   - Docker settings and configuration"
            echo "   - All user data and preferences"
        else
            echo "Standard uninstall: Docker Desktop will be removed but user data preserved"
        fi
        
        echo ""
        read -p "Proceed with uninstallation? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            echo "Uninstallation cancelled"
            exit 0
        fi
        
        uninstall_docker_desktop "$keep_data"
        
        echo ""
        echo "Final status:"
        get_installation_status
        exit 0
    fi
    
    if [[ "$CONFIGURE_ONLY" == "true" ]]; then
        # Check if Docker Desktop is installed
        if [[ ! -d "/Applications/Docker.app" ]]; then
            log "ERROR: Docker Desktop is not installed. Install it first."
            exit 1
        fi
        configure_docker_desktop
        exit 0
    fi
    
    # Normal installation flow
    log "Starting Docker Desktop installation..."
    check_requirements
    install_via_dmg
    configure_docker_desktop
    log "Installation and configuration complete!"
    
    echo ""
    echo "🐳 Docker Desktop installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Docker Desktop should start automatically"
    echo "2. Test the installation: docker run hello-world"
    echo "3. Access Docker Desktop from Applications folder or menu bar"
    echo ""
    echo "To uninstall later, run: $0 --uninstall (or --clean-uninstall)"
    echo "To check status, run: $0 --status"
}

# Run main function
main "$@"
```

---

## File: examples/enterprise-config.json

```json
{
  "configurationFileVersion": 2,
  "autoDownloadUpdates": false,
  "autoPauseTimeoutSeconds": 600,
  "autoStart": true,
  "cpus": 4,
  "displayedOnboarding": true,
  "enableIntegrityCheck": true,
  "memoryMiB": 8192,
  "diskSizeMiB": 102400,
  "openUIOnStartupDisabled": true,
  "showAnnouncementNotifications": false,
  "showGeneralNotifications": false,
  "swapMiB": 2048,
  "useCredentialHelper": true,
  "useResourceSaver": true,
  "filesharingDirectories": [
    "/opt/projects",
    "/var/data",
    "/Users"
  ],
  "analyticsEnabled": false,
  "allowedOrgs": ["your-enterprise-org"]
}
```

---

## File: examples/personal-config.json

```json
{
  "configurationFileVersion": 2,
  "autoDownloadUpdates": true,
  "autoPauseTimeoutSeconds": 300,
  "autoStart": false,
  "cpus": 2,
  "displayedOnboarding": true,
  "enableIntegrityCheck": true,
  "memoryMiB": 4096,
  "diskSizeMiB": 61440,
  "openUIOnStartupDisabled": false,
  "showAnnouncementNotifications": true,
  "showGeneralNotifications": true,
  "swapMiB": 1024,
  "useCredentialHelper": true,
  "useResourceSaver": true,
  "filesharingDirectories": [
    "/Users",
    "/Volumes",
    "/tmp"
  ],
  "analyticsEnabled": true
}
```

---

## File: docs/Configuration-Settings.md

# Docker Desktop Configuration Settings Reference

## Core Resource Settings

| Setting | Type | Description | Windows | macOS | Default |
|---------|------|-------------|---------|-------|---------|
| `cpus` | integer | CPU cores allocated to Docker | ✅ | ✅ | 2 |
| `memoryMiB` | integer | Memory in MiB | ✅ | ✅ | 2048 |
| `diskSizeMiB` | integer | Virtual disk size in MiB | ✅ | ✅ | 65536 |
| `swapMiB` | integer | Swap file size in MiB | ✅ | ✅ | 1024 |

## Application Behavior

| Setting | Type | Description | Windows | macOS | Default |
|---------|------|-------------|---------|-------|---------|
| `autoStart` | boolean | Start Docker on system boot | ✅ | ✅ | true |
| `openUIOnStartupDisabled` | boolean | Prevent UI from opening on start | ✅ | ✅ | false |
| `displayedOnboarding` | boolean | Mark onboarding as completed | ✅ | ✅ | false |
| `useResourceSaver` | boolean | Enable resource saver mode | ✅ | ✅ | true |
| `autoPauseTimeoutSeconds` | integer | Auto-pause timeout | ✅ | ✅ | 300 |

## Update and Analytics

| Setting | Type | Description | Windows | macOS | Default |
|---------|------|-------------|---------|-------|---------|
| `autoDownloadUpdates` | boolean | Auto-download updates | ✅ | ✅ | true |
| `disableUpdate` | boolean | Disable all updates | ✅ | ✅ | false |
| `analyticsEnabled` | boolean | Enable usage analytics | ✅ | ✅ | true |
| `showAnnouncementNotifications` | boolean | Show product announcements | ✅ | ✅ | true |
| `showGeneralNotifications` | boolean | Show general notifications | ✅ | ✅ | true |

## File Sharing and Security

| Setting | Type | Description | Windows | macOS | Default |
|---------|------|-------------|---------|-------|---------|
| `filesharingDirectories` | array | Shared directories | ✅ | ✅ | Platform default |
| `useCredentialHelper` | boolean | Use system credential helper | ✅ | ✅ | true |
| `enableIntegrityCheck` | boolean | Enable container integrity checks | ✅ | ✅ | true |

## Platform-Specific Settings

### Windows Only
- `wslEngineEnabled`: Enable WSL2 backend
- `useWindowsContainers`: Use Windows containers instead of Linux

### macOS Only  
- `useVirtualizationFramework`: Use Apple's Virtualization Framework (Apple Silicon)
- `useVirtualizationFrameworkVirtioFS`: Enable VirtioFS file sharing
- `useVirtualizationFrameworkRosetta`: Enable Rosetta 2 for x86 emulation

---

## File: README-Windows.md

# Windows Docker Desktop Automation

## Prerequisites

- Windows 10/11 Pro, Enterprise, or Education
- Administrator privileges
- PowerShell 5.1 or later
- At least 4GB RAM and 10GB disk space

## Quick Start

```powershell
# Basic installation
.\install-docker-desktop.ps1

# Enterprise installation with organization constraint
.\install-docker-desktop.ps1 -OrganizationName "YourCompany"

# Installation without WSL2 (uses Hyper-V)
.\install-docker-desktop.ps1 -EnableWSL2:$false

# Status check
Get-DockerInstallationStatus

# Uninstall (keeps user data)
.\install-docker-desktop.ps1 -Uninstall

# Complete removal
.\install-docker-desktop.ps1 -CleanUninstall
```

## WSL2 Integration

The script automatically:
- Enables WSL and Virtual Machine Platform features
- Downloads and installs WSL2 kernel update
- Sets WSL2 as default version
- Creates Docker WSL distros on first run

### WSL Troubleshooting

If you encounter WSL-related issues:

```powershell
# Manual WSL reset
wsl --shutdown
wsl --update
wsl --set-default-version 2

# Reset Docker WSL distros
wsl --unregister docker-desktop
wsl --unregister docker-desktop-data
# Then restart Docker Desktop
```

## Enterprise Deployment

For enterprise environments, consider:

1. **Group Policy**: Deploy via MSI with ADMINSETTINGS parameter
2. **SCCM/Intune**: Use MSI package with silent installation
3. **Registry Settings**: Pre-configure organization constraints

### MSI Deployment Example

```cmd
msiexec /i "DockerDesktop.msi" /quiet ADMINSETTINGS="{\"allowedOrgs\":[\"your-org\"]}"
```

## Troubleshooting

### Common Issues

1. **"Administrator privileges required"**
   - Run PowerShell as Administrator
   - Check UAC settings

2. **WSL installation fails**
   - Ensure virtualization is enabled in BIOS
   - Check Windows version compatibility
   - Run Windows Update

3. **Docker service won't start**
   - Check Event Viewer for detailed errors
   - Verify docker-users group membership
   - Restart computer after installation

### Diagnostic Commands

```powershell
# Check Windows features
Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux

# Check Docker service
Get-Service com.docker.service
Get-EventLog -LogName Application -Source "Docker Desktop" -Newest 10

# Check WSL status
wsl --list --verbose
wsl --status
```

---

## File: README-macOS.md

# macOS Docker Desktop Automation

## Prerequisites

- macOS 13.0 (Ventura) or later
- At least 4GB RAM and 10GB disk space
- Admin access for privileged operations

## Quick Start

```bash
# Make script executable
chmod +x install-docker-desktop.sh

# Basic installation
./install-docker-desktop.sh

# Status check
./install-docker-desktop.sh --status

# Configure existing installation
./install-docker-desktop.sh --configure-only

# Uninstall (keeps user data)
./install-docker-desktop.sh --uninstall

# Complete removal
./install-docker-desktop.sh --clean-uninstall
```

## Apple Silicon Optimizations

On Apple Silicon Macs, the script automatically enables:
- Virtualization Framework for better performance
- VirtioFS for faster file sharing
- Rosetta 2 for x86 container compatibility

## File Sharing Performance

Default shared directories:
- `/Users` - User home directories
- `/Volumes` - External drives
- `/private` - System private directory
- `/tmp` - Temporary files
- `/var/folders` - System temporary folders

For better performance, consider limiting shared directories to only what you need.

## Troubleshooting

### Common Issues

1. **"jq: command not found"**
   ```bash
   # Install via Homebrew
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   brew install jq
   ```

2. **Permission denied during installation**
   ```bash
   # Check if script is executable
   ls -la install-docker-desktop.sh
   chmod +x install-docker-desktop.sh
   ```

3. **Docker Desktop won't start**
   - Check System Preferences > Security & Privacy
   - Allow Docker Desktop in Privacy settings
   - Restart Mac if needed

### Manual Cleanup

If automated uninstall fails:

```bash
# Force quit Docker
sudo pkill -9 "Docker Desktop"

# Remove application manually
sudo rm -rf "/Applications/Docker.app"

# Remove privileged helper
sudo launchctl unload /Library/LaunchDaemons/com.docker.vmnetd.plist
sudo rm -f /Library/LaunchDaemons/com.docker.vmnetd.plist

# Remove user data
rm -rf "$HOME/Library/Group Containers/group.com.docker"
rm -rf "$HOME/.docker"
```

### Performance Tuning

For better performance:

1. **Reduce shared directories** to only what you need
2. **Increase memory allocation** if you have sufficient RAM
3. **Enable Resource Saver** for laptops
4. **Use VirtioFS** on Apple Silicon (enabled by default)

## Integration with CI/CD

Example GitHub Actions integration:

```yaml
- name: Install Docker Desktop
  run: |
    curl -O https://your-server/install-docker-desktop.sh
    chmod +x install-docker-desktop.sh
    ./install-docker-desktop.sh --configure-only
```

---

## Installation Instructions

1. **Download all files** and organize them according to the directory structure shown above
2. **Set execute permissions** on the scripts:
   ```bash
   chmod +x macos/install-docker-desktop.sh
   ```
3. **Run as appropriate for your platform**:
   - Windows: Run PowerShell as Administrator
   - macOS: Run from Terminal with sudo access available

## Features Summary

✅ **Automated Installation**: Downloads and installs Docker Desktop  
✅ **Configuration Management**: Applies custom settings via JSON  
✅ **WSL2 Integration**: Full WSL2 setup and error handling (Windows)  
✅ **Apple Silicon Support**: Optimized for M1/M2 Macs  
✅ **Uninstall Capabilities**: Standard and clean uninstall options  
✅ **Status Monitoring**: Detailed installation status reporting  
✅ **Error Recovery**: Robust error handling and recovery mechanisms  
✅ **Enterprise Ready**: Organization constraints and admin settings  
✅ **Backup & Restore**: Automatic configuration backups  

## Support

For issues or contributions:
1. Check the troubleshooting sections in platform-specific READMEs
2. Review the configuration settings reference
3. Use the status check functions to diagnose problems

This package provides production-ready automation for Docker Desktop deployment across Windows and macOS environments.