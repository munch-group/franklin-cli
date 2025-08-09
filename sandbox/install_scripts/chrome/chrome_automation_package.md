# Google Chrome Automation Package

Complete collection of scripts and documentation for automated Google Chrome installation, configuration, and management on Windows and macOS.

## Package Contents

```
chrome-automation/
├── README.md                          # This file - overview and instructions
├── windows/
│   ├── install-chrome.ps1             # Windows PowerShell script
│   └── README-Windows.md               # Windows-specific documentation
├── macos/
│   ├── install-chrome.sh               # macOS bash script
│   └── README-macOS.md                 # macOS-specific documentation
├── docs/
│   ├── Configuration-Guide.md          # Comprehensive configuration guide
│   ├── Privacy-Settings.md             # Privacy and security settings
│   └── Enterprise-Deployment.md        # Enterprise deployment guide
└── examples/
    ├── enterprise-config.txt           # Example enterprise configuration
    ├── privacy-focused-config.txt      # Example privacy-focused setup
    └── basic-config.txt                # Example basic configuration
```

## Quick Start

### Windows
```powershell
# Run as Administrator
.\windows\install-chrome.ps1

# Privacy-focused installation
.\windows\install-chrome.ps1 -DisableTracking -DisableUpdates

# Enterprise installation
.\windows\install-chrome.ps1 -EnterpriseMode -HomepageURL "https://company.com"

# Uninstall
.\windows\install-chrome.ps1 -CleanUninstall
```

### macOS
```bash
# Standard installation
./macos/install-chrome.sh

# Privacy-focused installation
./macos/install-chrome.sh --disable-updates --enterprise

# Custom homepage
./macos/install-chrome.sh --homepage "https://company.com"

# Clean uninstall
./macos/install-chrome.sh --clean-uninstall
```

---

## File: windows/install-chrome.ps1

```powershell
param(
    [string]$InstallPath = "${env:ProgramFiles}\Google\Chrome\Application",
    [switch]$SetAsDefault = $true,
    [switch]$DisableUpdates = $false,
    [switch]$DisableTracking = $true,
    [switch]$EnterpriseMode = $false,
    [string]$HomepageURL = "",
    [switch]$Uninstall = $false,
    [switch]$CleanUninstall = $false,
    [switch]$StatusCheck = $false
)

# Verify administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Administrator privileges required"
    exit 1
}

function Get-ChromeInstallationStatus {
    Write-Host "=== Google Chrome Installation Status ===" -ForegroundColor Cyan
    
    # Check if Chrome is installed
    $chromeExe = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
    $chromeExe32 = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
    $chromeInstalled = $false
    $chromePath = ""
    
    if (Test-Path $chromeExe) {
        $chromeInstalled = $true
        $chromePath = $chromeExe
    } elseif (Test-Path $chromeExe32) {
        $chromeInstalled = $true
        $chromePath = $chromeExe32
    }
    
    Write-Host "Chrome Installed: $chromeInstalled" -ForegroundColor $(if ($chromeInstalled) { "Green" } else { "Red" })
    
    if ($chromeInstalled) {
        $version = (Get-Item $chromePath).VersionInfo.FileVersion
        Write-Host "Version: $version" -ForegroundColor White
        Write-Host "Location: $chromePath" -ForegroundColor White
    }
    
    # Check Chrome update service
    $updateService = Get-Service -Name "gupdate" -ErrorAction SilentlyContinue
    if ($updateService) {
        Write-Host "Update Service: $($updateService.Status)" -ForegroundColor White
    } else {
        Write-Host "Update Service: Not found" -ForegroundColor Red
    }
    
    # Check default browser
    try {
        $defaultBrowser = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice" -Name ProgId -ErrorAction SilentlyContinue
        if ($defaultBrowser -and $defaultBrowser.ProgId -like "*Chrome*") {
            Write-Host "Default Browser: Chrome" -ForegroundColor Green
        } else {
            Write-Host "Default Browser: Not Chrome" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Default Browser: Cannot determine" -ForegroundColor Red
    }
    
    # Check user profiles
    $profilePath = "$env:LOCALAPPDATA\Google\Chrome\User Data"
    if (Test-Path $profilePath) {
        $profiles = Get-ChildItem $profilePath -Directory | Where-Object { $_.Name -like "Profile*" -or $_.Name -eq "Default" }
        Write-Host "User Profiles: $($profiles.Count)" -ForegroundColor White
        
        $totalSize = (Get-ChildItem $profilePath -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $sizeGB = [math]::Round($totalSize / 1GB, 2)
        Write-Host "Profile Data Size: $sizeGB GB" -ForegroundColor White
    } else {
        Write-Host "User Profiles: None found" -ForegroundColor Red
    }
    
    # Check enterprise policies
    $policyPath = "HKLM:\SOFTWARE\Policies\Google\Chrome"
    if (Test-Path $policyPath) {
        $policies = Get-ChildItem $policyPath -Recurse -ErrorAction SilentlyContinue
        Write-Host "Enterprise Policies: $($policies.Count) configured" -ForegroundColor White
    } else {
        Write-Host "Enterprise Policies: None configured" -ForegroundColor Yellow
    }
}

function Remove-GoogleChrome {
    param(
        [switch]$KeepUserData = $false
    )
    
    Write-Host "Starting Google Chrome uninstallation..." -ForegroundColor Yellow
    
    try {
        # Stop Chrome processes
        Write-Host "Stopping Chrome processes..." -ForegroundColor Yellow
        Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
        Get-Process -Name "GoogleUpdate" -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 3
        
        # Find Chrome installation via registry
        $uninstallKeys = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
        )
        
        $chromeApp = $null
        foreach ($keyPath in $uninstallKeys) {
            $apps = Get-ItemProperty $keyPath -ErrorAction SilentlyContinue
            $chromeApp = $apps | Where-Object { $_.DisplayName -like "*Google Chrome*" } | Select-Object -First 1
            if ($chromeApp) { break }
        }
        
        # Uninstall Chrome
        if ($chromeApp -and $chromeApp.UninstallString) {
            Write-Host "Running Chrome uninstaller..." -ForegroundColor Yellow
            $uninstallCmd = $chromeApp.UninstallString
            
            # Add silent flags if not present
            if ($uninstallCmd -notlike "*--force-uninstall*") {
                $uninstallCmd += " --force-uninstall"
            }
            if ($uninstallCmd -notlike "*--system-level*") {
                $uninstallCmd += " --system-level"
            }
            
            Write-Host "Executing: $uninstallCmd" -ForegroundColor Cyan
            Invoke-Expression "& $uninstallCmd"
            Start-Sleep -Seconds 5
        } else {
            Write-Warning "Chrome uninstaller not found in registry, attempting manual removal"
        }
        
        # Manual removal of installation directories
        $installPaths = @(
            "${env:ProgramFiles}\Google",
            "${env:ProgramFiles(x86)}\Google",
            "${env:LOCALAPPDATA}\Google\Update",
            "${env:ProgramData}\Google"
        )
        
        foreach ($path in $installPaths) {
            if (Test-Path $path) {
                Write-Host "Removing: $path" -ForegroundColor Yellow
                Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "✅ Removed: $path" -ForegroundColor Green
            }
        }
        
        # Remove user data if requested
        if (-not $KeepUserData) {
            Write-Host "Removing user data..." -ForegroundColor Yellow
            
            # Get all user profiles
            $users = Get-ChildItem "C:\Users" -Directory -ErrorAction SilentlyContinue
            foreach ($user in $users) {
                $userChromePath = "$($user.FullName)\AppData\Local\Google\Chrome"
                if (Test-Path $userChromePath) {
                    Remove-Item $userChromePath -Recurse -Force -ErrorAction SilentlyContinue
                    Write-Host "✅ Removed user data for: $($user.Name)" -ForegroundColor Green
                }
            }
            
            # Remove current user data
            $currentUserPath = "$env:LOCALAPPDATA\Google\Chrome"
            if (Test-Path $currentUserPath) {
                Remove-Item $currentUserPath -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "✅ Removed current user Chrome data" -ForegroundColor Green
            }
        }
        
        # Remove services
        Write-Host "Removing Chrome services..." -ForegroundColor Yellow
        $services = @("gupdate", "gupdatem", "GoogleChromeElevationService")
        foreach ($serviceName in $services) {
            $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ($service) {
                Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
                sc.exe delete $serviceName
                Write-Host "✅ Removed service: $serviceName" -ForegroundColor Green
            }
        }
        
        # Remove registry entries
        Write-Host "Cleaning registry entries..." -ForegroundColor Yellow
        $registryPaths = @(
            "HKLM:\SOFTWARE\Google",
            "HKLM:\SOFTWARE\WOW6432Node\Google",
            "HKCU:\SOFTWARE\Google",
            "HKLM:\SOFTWARE\Policies\Google",
            "HKLM:\SOFTWARE\Classes\ChromeHTML",
            "HKLM:\SOFTWARE\Classes\Applications\chrome.exe"
        )
        
        foreach ($regPath in $registryPaths) {
            if (Test-Path $regPath) {
                Remove-Item $regPath -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "✅ Removed registry: $regPath" -ForegroundColor Green
            }
        }
        
        # Remove shortcuts
        Write-Host "Removing shortcuts..." -ForegroundColor Yellow
        $shortcutPaths = @(
            "$env:PUBLIC\Desktop\Google Chrome.lnk",
            "$env:USERPROFILE\Desktop\Google Chrome.lnk",
            "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Google Chrome.lnk",
            "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Google Chrome.lnk"
        )
        
        foreach ($shortcut in $shortcutPaths) {
            if (Test-Path $shortcut) {
                Remove-Item $shortcut -Force -ErrorAction SilentlyContinue
                Write-Host "✅ Removed shortcut: $shortcut" -ForegroundColor Green
            }
        }
        
        Write-Host "Google Chrome uninstallation completed!" -ForegroundColor Green
        
    } catch {
        Write-Error "Uninstallation failed: $($_.Exception.Message)"
        return $false
    }
    
    return $true
}

function Install-GoogleChrome {
    Write-Host "Starting Google Chrome installation..." -ForegroundColor Green
    
    # Download Chrome installer
    $installerUrl = "https://dl.google.com/chrome/install/latest/chrome_installer.exe"
    $installerPath = "$env:TEMP\chrome_installer.exe"
    
    Write-Host "Downloading Chrome installer..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Error "Failed to download Chrome installer: $($_.Exception.Message)"
        return $false
    }
    
    # Install Chrome silently
    Write-Host "Installing Chrome..." -ForegroundColor Yellow
    $installArgs = @("/silent", "/install")
    
    try {
        $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
        if ($process.ExitCode -eq 0) {
            Write-Host "✅ Chrome installed successfully" -ForegroundColor Green
        } else {
            Write-Error "Chrome installation failed with exit code: $($process.ExitCode)"
            return $false
        }
    } catch {
        Write-Error "Failed to run Chrome installer: $($_.Exception.Message)"
        return $false
    }
    
    # Clean up installer
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    
    return $true
}

function Set-ChromeConfiguration {
    Write-Host "Configuring Google Chrome..." -ForegroundColor Yellow
    
    # Create Chrome policies registry path
    $policyPath = "HKLM:\SOFTWARE\Policies\Google\Chrome"
    if (!(Test-Path $policyPath)) {
        New-Item $policyPath -Force | Out-Null
    }
    
    # Configure based on parameters
    if ($DisableUpdates) {
        Write-Host "Disabling Chrome updates..." -ForegroundColor Yellow
        Set-ItemProperty -Path $policyPath -Name "UpdateDefault" -Value 0 -Type DWord
        
        # Stop and disable update services
        $services = @("gupdate", "gupdatem")
        foreach ($serviceName in $services) {
            $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ($service) {
                Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
                Set-Service -Name $serviceName -StartupType Disabled
            }
        }
    }
    
    if ($DisableTracking) {
        Write-Host "Configuring privacy settings..." -ForegroundColor Yellow
        
        # Disable various tracking and data collection features
        $privacySettings = @{
            "MetricsReportingEnabled" = 0
            "SearchSuggestEnabled" = 0
            "NetworkPredictionOptions" = 2  # No network prediction
            "SafeBrowsingProtectionLevel" = 1  # Standard protection
            "PasswordManagerEnabled" = 0
            "AutofillAddressEnabled" = 0
            "AutofillCreditCardEnabled" = 0
            "SyncDisabled" = 1
            "SigninAllowed" = 0
            "BrowserGuestModeEnabled" = 0
            "PromotionalTabsEnabled" = 0
            "WelcomePageOnOSUpgradeEnabled" = 0
        }
        
        foreach ($setting in $privacySettings.GetEnumerator()) {
            Set-ItemProperty -Path $policyPath -Name $setting.Key -Value $setting.Value -Type DWord
        }
    }
    
    if ($HomepageURL) {
        Write-Host "Setting homepage to: $HomepageURL" -ForegroundColor Yellow
        Set-ItemProperty -Path $policyPath -Name "HomepageLocation" -Value $HomepageURL -Type String
        Set-ItemProperty -Path $policyPath -Name "HomepageIsNewTabPage" -Value 0 -Type DWord
    }
    
    if ($EnterpriseMode) {
        Write-Host "Configuring enterprise settings..." -ForegroundColor Yellow
        
        $enterpriseSettings = @{
            "DeveloperToolsDisabled" = 1
            "IncognitoModeAvailability" = 1  # Disable incognito mode
            "BookmarkBarEnabled" = 1
            "ShowHomeButton" = 1
            "DefaultBrowserSettingEnabled" = 0
            "HideWebStoreIcon" = 1
            "ExtensionInstallBlocklist" = "*"  # Block all extensions
        }
        
        foreach ($setting in $enterpriseSettings.GetEnumerator()) {
            if ($setting.Key -eq "ExtensionInstallBlocklist") {
                # Handle array values
                $blocklistPath = "$policyPath\ExtensionInstallBlocklist"
                if (!(Test-Path $blocklistPath)) {
                    New-Item $blocklistPath -Force | Out-Null
                }
                Set-ItemProperty -Path $blocklistPath -Name "1" -Value "*" -Type String
            } else {
                Set-ItemProperty -Path $policyPath -Name $setting.Key -Value $setting.Value -Type DWord
            }
        }
    }
    
    Write-Host "✅ Chrome configuration applied" -ForegroundColor Green
}

function Set-ChromeAsDefault {
    Write-Host "Setting Chrome as default browser..." -ForegroundColor Yellow
    
    try {
        # Use Chrome's built-in method to set as default
        $chromePath = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
        if (!(Test-Path $chromePath)) {
            $chromePath = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
        }
        
        if (Test-Path $chromePath) {
            Start-Process -FilePath $chromePath -ArgumentList "--make-default-browser" -Wait
            Write-Host "✅ Chrome set as default browser" -ForegroundColor Green
        } else {
            Write-Warning "Chrome executable not found, cannot set as default"
        }
    } catch {
        Write-Warning "Failed to set Chrome as default browser: $($_.Exception.Message)"
    }
}

# Main execution logic
if ($StatusCheck) {
    Get-ChromeInstallationStatus
    exit 0
}

if ($Uninstall -or $CleanUninstall) {
    Write-Host "Google Chrome Uninstallation" -ForegroundColor Red
    Write-Host "=============================" -ForegroundColor Red
    
    # Show current status
    Get-ChromeInstallationStatus
    
    Write-Host "`nUninstall Options:" -ForegroundColor Yellow
    if ($CleanUninstall) {
        Write-Host "- Clean uninstall: Removes Chrome and ALL user data (bookmarks, history, etc.)" -ForegroundColor White
    } else {
        Write-Host "- Standard uninstall: Removes Chrome but keeps user data" -ForegroundColor White
    }
    
    $confirmUninstall = Read-Host "`nProceed with uninstallation? (yes/no)"
    if ($confirmUninstall -ne "yes") {
        Write-Host "Uninstallation cancelled" -ForegroundColor Yellow
        exit 0
    }
    
    if ($CleanUninstall) {
        $result = Remove-GoogleChrome
    } else {
        $result = Remove-GoogleChrome -KeepUserData
    }
    
    if ($result) {
        Write-Host "`nFinal status check:" -ForegroundColor Cyan
        Get-ChromeInstallationStatus
    }
    
    exit $(if ($result) { 0 } else { 1 })
}

# Normal installation flow
Write-Host "Google Chrome Installation and Configuration" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

# Check if Chrome is already installed
$chromeExe = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
$chromeExe32 = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"

if ((Test-Path $chromeExe) -or (Test-Path $chromeExe32)) {
    Write-Host "Chrome is already installed. Applying configuration..." -ForegroundColor Yellow
} else {
    # Install Chrome
    $installResult = Install-GoogleChrome
    if (-not $installResult) {
        Write-Error "Chrome installation failed"
        exit 1
    }
}

# Apply configuration
Set-ChromeConfiguration

# Set as default browser if requested
if ($SetAsDefault) {
    Set-ChromeAsDefault
}

Write-Host "`nInstallation and configuration complete!" -ForegroundColor Green
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "- To check status: $($MyInvocation.MyCommand.Name) -StatusCheck" -ForegroundColor White
Write-Host "- To uninstall: $($MyInvocation.MyCommand.Name) -Uninstall" -ForegroundColor White
Write-Host "- To clean uninstall: $($MyInvocation.MyCommand.Name) -CleanUninstall" -ForegroundColor White

# Show final status
Write-Host "`nFinal installation status:" -ForegroundColor Cyan
Get-ChromeInstallationStatus
```

---

## File: macos/install-chrome.sh

```bash
#!/bin/bash
set -euo pipefail

# Configuration
USERNAME=$(whoami)
LOG_FILE="/tmp/chrome_install.log"
CHROME_APP="/Applications/Google Chrome.app"
CHROME_PREFERENCES="$HOME/Library/Preferences/com.google.Chrome.plist"
CHROME_USER_DATA="$HOME/Library/Application Support/Google/Chrome"

# Command line options
UNINSTALL=false
CLEAN_UNINSTALL=false
STATUS_CHECK=false
SET_AS_DEFAULT=true
DISABLE_TRACKING=true
DISABLE_UPDATES=false
ENTERPRISE_MODE=false
HOMEPAGE_URL=""

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
        --no-default)
            SET_AS_DEFAULT=false
            shift
            ;;
        --enable-tracking)
            DISABLE_TRACKING=false
            shift
            ;;
        --disable-updates)
            DISABLE_UPDATES=true
            shift
            ;;
        --enterprise)
            ENTERPRISE_MODE=true
            shift
            ;;
        --homepage)
            HOMEPAGE_URL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --uninstall        Remove Chrome (keep user data)"
            echo "  --clean-uninstall  Remove Chrome and all data"
            echo "  --status          Show installation status"
            echo "  --no-default      Don't set Chrome as default browser"
            echo "  --enable-tracking  Don't disable tracking features"
            echo "  --disable-updates  Disable automatic updates"
            echo "  --enterprise      Apply enterprise security settings"
            echo "  --homepage URL    Set custom homepage"
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
    
    if [[ $MAJOR_VERSION -lt 11 ]]; then
        log "ERROR: macOS 11.0 (Big Sur) or later required"
        exit 1
    fi
    
    AVAILABLE_SPACE=$(df -g / | tail -1 | awk '{print $4}')
    if [[ $AVAILABLE_SPACE -lt 5 ]]; then
        log "ERROR: Insufficient disk space (5GB required)"
        exit 1
    fi
}

get_installation_status() {
    echo "=== Google Chrome Installation Status ==="
    
    # Check if Chrome is installed
    if [[ -d "$CHROME_APP" ]]; then
        echo "✅ Chrome: Installed"
        
        # Get version info
        local version_plist="$CHROME_APP/Contents/Info.plist"
        if [[ -f "$version_plist" ]]; then
            local version=$(defaults read "$version_plist" CFBundleShortVersionString 2>/dev/null || echo "Unknown")
            echo "   Version: $version"
        fi
        
        local bundle_id=$(defaults read "$version_plist" CFBundleIdentifier 2>/dev/null || echo "Unknown")
        echo "   Bundle ID: $bundle_id"
    else
        echo "❌ Chrome: Not installed"
    fi
    
    # Check if Chrome is running
    if pgrep -x "Google Chrome" > /dev/null; then
        echo "✅ Chrome: Running"
    else
        echo "⚠️  Chrome: Not running"
    fi
    
    # Check default browser
    local default_browser=$(defaults read ~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure | grep -A 1 "https" | grep "LSHandlerRoleAll" -A 1 | grep "com.google.chrome" || echo "")
    if [[ -n "$default_browser" ]]; then
        echo "✅ Default Browser: Chrome"
    else
        echo "⚠️  Default Browser: Not Chrome"
    fi
    
    # Check user data
    echo ""
    echo "User Data:"
    if [[ -d "$CHROME_USER_DATA" ]]; then
        local profiles=$(ls "$CHROME_USER_DATA" | grep -E "^(Default|Profile)" | wc -l | tr -d ' ')
        echo "✅ User profiles: $profiles"
        
        local size=$(du -sh "$CHROME_USER_DATA" 2>/dev/null | cut -f1 || echo "Unknown")
        echo "   Data size: $size"
    else
        echo "❌ User data: Not found"
    fi
    
    # Check preferences
    if [[ -f "$CHROME_PREFERENCES" ]]; then
        echo "✅ Preferences: Configured"
    else
        echo "⚠️  Preferences: Default"
    fi
    
    # Check for managed policies
    local managed_prefs="/Library/Managed Preferences/$USERNAME/com.google.Chrome.plist"
    if [[ -f "$managed_prefs" ]]; then
        echo "✅ Managed policies: Active"
    else
        echo "⚠️  Managed policies: None"
    fi
    
    # Check updates
    local update_plist="$HOME/Library/Google/GoogleSoftwareUpdate/GoogleSoftwareUpdate.bundle/Contents/Info.plist"
    if [[ -f "$update_plist" ]]; then
        echo "✅ Auto-update: Enabled"
    else
        echo "⚠️  Auto-update: Disabled/Not found"
    fi
}

uninstall_chrome() {
    local keep_user_data=${1:-false}
    
    log "Starting Google Chrome uninstallation..."
    
    # Stop Chrome processes
    log "Stopping Chrome processes..."
    osascript -e 'quit app "Google Chrome"' 2>/dev/null || true
    
    # Wait for processes to stop
    local count=0
    while pgrep -x "Google Chrome" > /dev/null && [[ $count -lt 30 ]]; do
        sleep 1
        ((count++))
    done
    
    # Force kill if still running
    if pgrep -x "Google Chrome" > /dev/null; then
        log "Force killing Chrome processes..."
        pkill -9 "Google Chrome" 2>/dev/null || true
    fi
    
    # Remove application
    if [[ -d "$CHROME_APP" ]]; then
        log "Removing Chrome application..."
        rm -rf "$CHROME_APP"
        echo "✅ Removed: $CHROME_APP"
    fi
    
    # Remove Google Software Update
    local update_paths=(
        "$HOME/Library/Google"
        "/Library/Google"
        "$HOME/Library/Application Support/Google"
        "$HOME/Library/Caches/com.google.SoftwareUpdate"
    )
    
    for path in "${update_paths[@]}"; do
        if [[ -d "$path" ]] && [[ "$keep_user_data" != "true" || "$path" == *"Library/Google"* || "$path" == *"SoftwareUpdate"* ]]; then
            rm -rf "$path" 2>/dev/null || true
            echo "✅ Removed: $path"
        fi
    done
    
    # Remove user data if requested
    if [[ "$keep_user_data" != "true" ]]; then
        log "Removing user data..."
        
        local user_paths=(
            "$CHROME_USER_DATA"
            "$CHROME_PREFERENCES"
            "$HOME/Library/Caches/com.google.Chrome"
            "$HOME/Library/Caches/com.google.Chrome.helper"
            "$HOME/Library/Saved Application State/com.google.Chrome.savedState"
            "$HOME/Library/WebKit/com.google.Chrome"
            "$HOME/Library/Cookies/com.google.Chrome.binarycookies"
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
    
    # Remove managed preferences
    local managed_prefs="/Library/Managed Preferences/$USERNAME/com.google.Chrome.plist"
    if [[ -f "$managed_prefs" ]]; then
        sudo rm -f "$managed_prefs" 2>/dev/null || true
        echo "✅ Removed managed preferences"
    fi
    
    # Remove system-wide preferences
    local system_prefs="/Library/Preferences/com.google.Chrome.plist"
    if [[ -f "$system_prefs" ]]; then
        sudo rm -f "$system_prefs" 2>/dev/null || true
        echo "✅ Removed system preferences"
    fi
    
    # Remove LaunchAgents
    local launch_agents=(
        "$HOME/Library/LaunchAgents/com.google.keystone.agent.plist"
        "/Library/LaunchAgents/com.google.keystone.agent.plist"
        "/Library/LaunchDaemons/com.google.keystone.daemon.plist"
    )
    
    for agent in "${launch_agents[@]}"; do
        if [[ -f "$agent" ]]; then
            if [[ "$agent" == "/Library/"* ]]; then
                sudo launchctl unload "$agent" 2>/dev/null || true
                sudo rm -f "$agent"
            else
                launchctl unload "$agent" 2>/dev/null || true
                rm -f "$agent"
            fi
            echo "✅ Removed launch agent: $agent"
        fi
    done
    
    # Reset default browser if Chrome was default
    defaults delete ~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure 2>/dev/null || true
    
    log "Google Chrome uninstallation completed!"
    echo ""
    echo "Uninstallation Summary:"
    echo "✅ Chrome application removed"
    echo "✅ Google Update services removed"
    echo "✅ Launch agents removed"
    
    if [[ "$keep_user_data" != "true" ]]; then
        echo "✅ User data removed"
    else
        echo "⚠️  User data preserved"
    fi
}

install_chrome() {
    log "Starting Google Chrome installation..."
    
    # Determine architecture
    ARCH=$(uname -m)
    if [[ $ARCH == "arm64" ]]; then
        DOWNLOAD_URL="https://dl.google.com/chrome/mac/universal/stable/GGRO/googlechrome.dmg"
    else
        DOWNLOAD_URL="https://dl.google.com/chrome/mac/stable/GGRO/googlechrome.dmg"
    fi
    
    log "Downloading Chrome for $ARCH..."
    curl -L -o /tmp/GoogleChrome.dmg "$DOWNLOAD_URL"
    
    if [[ ! -f "/tmp/GoogleChrome.dmg" ]]; then
        log "ERROR: Failed to download Chrome"
        exit 1
    fi
    
    log "Installing Chrome..."
    
    # Mount the DMG
    hdiutil attach /tmp/GoogleChrome.dmg -nobrowse -quiet
    
    # Copy the app
    cp -R "/Volumes/Google Chrome/Google Chrome.app" /Applications/
    
    # Unmount the DMG
    hdiutil detach "/Volumes/Google Chrome" -quiet
    
    # Clean up
    rm -f /tmp/GoogleChrome.dmg
    
    log "✅ Chrome installation completed"
}

configure_chrome() {
    log "Configuring Google Chrome..."
    
    # Ensure Chrome preferences directory exists
    local prefs_dir=$(dirname "$CHROME_PREFERENCES")
    mkdir -p "$prefs_dir"
    
    # Create base preferences if they don't exist
    if [[ ! -f "$CHROME_PREFERENCES" ]]; then
        defaults write com.google.Chrome NSInitialToolTip -bool false
    fi
    
    # Configure privacy settings
    if [[ "$DISABLE_TRACKING" == "true" ]]; then
        log "Configuring privacy settings..."
        
        # Disable various tracking features
        defaults write com.google.Chrome MetricsReportingEnabled -bool false
        defaults write com.google.Chrome SearchSuggestEnabled -bool false
        defaults write com.google.Chrome NetworkPredictionOptions -int 2
        defaults write com.google.Chrome SafeBrowsingProtectionLevel -int 1
        defaults write com.google.Chrome PasswordManagerEnabled -bool false
        defaults write com.google.Chrome AutofillAddressEnabled -bool false
        defaults write com.google.Chrome AutofillCreditCardEnabled -bool false
        defaults write com.google.Chrome SyncDisabled -bool true
        defaults write com.google.Chrome SigninAllowed -bool false
        defaults write com.google.Chrome BrowserGuestModeEnabled -bool false
        defaults write com.google.Chrome PromotionalTabsEnabled -bool false
        defaults write com.google.Chrome WelcomePageOnOSUpgradeEnabled -bool false
        defaults write com.google.Chrome DefaultBrowserSettingEnabled -bool false
    fi
    
    # Configure updates
    if [[ "$DISABLE_UPDATES" == "true" ]]; then
        log "Disabling automatic updates..."
        defaults write com.google.Chrome UpdateDefault -int 0
        
        # Remove Google Software Update if present
        if [[ -d "$HOME/Library/Google/GoogleSoftwareUpdate" ]]; then
            rm -rf "$HOME/Library/Google/GoogleSoftwareUpdate"
        fi
        
        # Disable update services
        launchctl unload "$HOME/Library/LaunchAgents/com.google.keystone.agent.plist" 2>/dev/null || true
    fi
    
    # Set homepage
    if [[ -n "$HOMEPAGE_URL" ]]; then
        log "Setting homepage to: $HOMEPAGE_URL"
        defaults write com.google.Chrome HomepageLocation -string "$HOMEPAGE_URL"
        defaults write com.google.Chrome HomepageIsNewTabPage -bool false
        defaults write com.google.Chrome ShowHomeButton -bool true
    fi
    
    # Enterprise mode settings
    if [[ "$ENTERPRISE_MODE" == "true" ]]; then
        log "Applying enterprise security settings..."
        
        # Create managed preferences (requires admin rights for system-wide)
        local managed_prefs_dir="/Library/Managed Preferences/$USERNAME"
        
        if [[ -w "/Library/Managed Preferences" ]] || sudo -n true 2>/dev/null; then
            sudo mkdir -p "$managed_prefs_dir"
            
            # Create enterprise policy file
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" DeveloperToolsDisabled -bool true
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" IncognitoModeAvailability -int 1
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" BookmarkBarEnabled -bool true
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" ExtensionInstallBlacklist -array "*"
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" HideWebStoreIcon -bool true
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" BrowserGuestModeEnabled -bool false
            
            sudo chown root:wheel "$managed_prefs_dir/com.google.Chrome.plist"
            sudo chmod 644 "$managed_prefs_dir/com.google.Chrome.plist"
        else
            log "WARNING: Cannot apply enterprise settings - admin rights required"
        fi
    fi
    
    log "✅ Chrome configuration completed"
}

set_chrome_as_default() {
    if [[ "$SET_AS_DEFAULT" == "true" ]]; then
        log "Setting Chrome as default browser..."
        
        # Use Chrome's built-in method
        if [[ -f "$CHROME_APP/Contents/MacOS/Google Chrome" ]]; then
            "$CHROME_APP/Contents/MacOS/Google Chrome" --make-default-browser &
            sleep 2
            pkill "Google Chrome" 2>/dev/null || true
            
            log "✅ Chrome set as default browser"
        else
            log "WARNING: Chrome executable not found"
        fi
    fi
}

# Main execution logic
main() {
    if [[ "$STATUS_CHECK" == "true" ]]; then
        get_installation_status
        exit 0
    fi
    
    if [[ "$UNINSTALL" == "true" ]] || [[ "$CLEAN_UNINSTALL" == "true" ]]; then
        echo "Google Chrome Uninstallation"
        echo "============================="
        echo ""
        
        # Show current status
        get_installation_status
        echo ""
        
        local keep_data="true"
        if [[ "$CLEAN_UNINSTALL" == "true" ]]; then
            keep_data="false"
            echo "⚠️  CLEAN UNINSTALL: This will remove ALL Chrome data including:"
            echo "   - Bookmarks and browsing history"
            echo "   - Saved passwords and autofill data"
            echo "   - Extensions and their data"
            echo "   - All user preferences and settings"
        else
            echo "Standard uninstall: Chrome will be removed but user data preserved"
        fi
        
        echo ""
        read -p "Proceed with uninstallation? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            echo "Uninstallation cancelled"
            exit 0
        fi
        
        uninstall_chrome "$keep_data"
        
        echo ""
        echo "Final status:"
        get_installation_status
        exit 0
    fi
    
    # Normal installation flow
    log "Starting Chrome installation and configuration..."
    check_requirements
    
    # Check if Chrome is already installed
    if [[ -d "$CHROME_APP" ]]; then
        log "Chrome is already installed. Applying configuration..."
    else
        install_chrome
    fi
    
    # Apply configuration
    configure_chrome
    
    # Set as default browser
    set_chrome_as_default
    
    log "Installation and configuration complete!"
    
    echo ""
    echo "🌐 Google Chrome installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Launch Chrome from Applications folder"
    echo "2. Complete any initial setup if needed"
    echo "3. Import bookmarks and settings if desired"
    echo ""
    echo "Management commands:"
    echo "- Check status: $0 --status"
    echo "- Uninstall: $0 --uninstall"
    echo "- Clean uninstall: $0 --clean-uninstall"
    
    # Show final status
    echo ""
    echo "Final installation status:"
    get_installation_status
}

# Run main function
main "$@"
```

---

## File: examples/enterprise-config.txt

**Windows Enterprise Configuration:**
```powershell
# Enterprise installation with strict security
.\install-chrome.ps1 -EnterpriseMode -DisableUpdates -DisableTracking -HomepageURL "https://company.com/portal"

# Registry policies applied:
# - Developer tools disabled
# - Incognito mode disabled  
# - All extensions blocked
# - Password manager disabled
# - Sync disabled
# - Guest mode disabled
```

**macOS Enterprise Configuration:**
```bash
# Enterprise installation with managed policies
./install-chrome.sh --enterprise --disable-updates --homepage "https://company.com/portal"

# Managed preferences applied:
# - Developer tools disabled
# - Incognito mode disabled
# - Extension install blocked
# - Privacy features configured
# - Automatic updates disabled
```

---

## File: examples/privacy-focused-config.txt

**Windows Privacy-Focused Setup:**
```powershell
# Maximum privacy configuration
.\install-chrome.ps1 -DisableTracking -DisableUpdates -SetAsDefault:$false

# Privacy settings applied:
# - Metrics reporting disabled
# - Search suggestions disabled  
# - Network prediction disabled
# - Password manager disabled
# - Autofill disabled
# - Sync disabled
# - Sign-in disabled
```

**macOS Privacy-Focused Setup:**
```bash
# Maximum privacy configuration
./install-chrome.sh --disable-updates --no-default

# Privacy settings applied:
# - All tracking features disabled
# - Google services minimized
# - Data collection disabled
# - User privacy maximized
```

---

## File: examples/basic-config.txt

**Windows Basic Installation:**
```powershell
# Standard installation with minimal configuration
.\install-chrome.ps1

# Default configuration:
# - Set as default browser
# - Basic privacy settings
# - Automatic updates enabled
# - Standard security settings
```

**macOS Basic Installation:**
```bash
# Standard installation with minimal configuration
./install-chrome.sh

# Default configuration:
# - Set as default browser
# - Basic privacy settings enabled
# - Automatic updates enabled
# - Standard security settings
```

---

## File: docs/Configuration-Guide.md

# Chrome Configuration Guide

## Privacy Settings

### Tracking Protection
Both scripts disable tracking by default, including:
- **Metrics reporting**: Prevents usage data collection
- **Search suggestions**: Disables query sharing with Google
- **Network prediction**: Stops DNS prefetching
- **Autofill**: Prevents form data collection
- **Sync**: Disables Google account synchronization

### Data Collection Controls
- **Password manager**: Can be disabled to prevent credential storage
- **Safe browsing**: Configurable protection levels
- **Promotional content**: Disabled to reduce Google promotions

## Enterprise Features

### Policy Management
- **Windows**: Uses Group Policy registry entries
- **macOS**: Implements managed preferences system
- **Extension control**: Can block all extensions
- **Developer tools**: Can be disabled for security

### Security Restrictions
- **Incognito mode**: Can be disabled
- **Guest browsing**: Can be prevented
- **Download restrictions**: Configurable security policies
- **Site access**: URL allowlists/blocklists supported

## Update Management

### Automatic Updates
- **Disable updates**: Prevents automatic Chrome updates
- **Service management**: Stops Google Update services
- **Manual control**: Allows administrator-controlled updates

### Version Control
- **Update channels**: Can configure stable/beta/dev channels
- **Rollback protection**: Prevents automatic downgrades
- **Enterprise deployment**: Supports centralized update management

## Browser Defaults

### Default Browser Setting
- **Automatic**: Sets Chrome as system default browser
- **User choice**: Allows users to maintain current default
- **File associations**: Configures HTTP/HTTPS handling

### Homepage Configuration
- **Custom homepage**: Set organizational landing pages
- **New tab behavior**: Control new tab page content
- **Startup options**: Configure browser startup behavior

---

## File: docs/Privacy-Settings.md

# Chrome Privacy Settings Reference

## Data Collection Settings

| Setting | Purpose | Impact | Recommendation |
|---------|---------|---------|----------------|
| MetricsReportingEnabled | Usage statistics | High | Disable for privacy |
| SearchSuggestEnabled | Query suggestions | Medium | Disable for privacy |
| NetworkPredictionOptions | DNS prefetching | Medium | Set to 2 (disabled) |
| PasswordManagerEnabled | Password storage | Low | User preference |
| AutofillAddressEnabled | Address autofill | Low | Disable for security |
| AutofillCreditCardEnabled | Payment autofill | High | Disable for security |
| SyncDisabled | Google account sync | High | Enable for privacy |
| SigninAllowed | Google sign-in | High | Disable for privacy |

## Security Settings

| Setting | Purpose | Risk Level | Enterprise Use |
|---------|---------|------------|----------------|
| SafeBrowsingProtectionLevel | Malware protection | Low | Standard (1) |
| DeveloperToolsDisabled | Developer access | Medium | Disable for security |
| IncognitoModeAvailability | Private browsing | Low | Disable if needed |
| BrowserGuestModeEnabled | Guest access | Medium | Disable for security |
| ExtensionInstallBlocklist | Extension control | High | Block all (*) |

## Notification Settings

| Setting | Purpose | User Impact | Default |
|---------|---------|-------------|---------|
| PromotionalTabsEnabled | Google promotions | Low | Disable |
| WelcomePageOnOSUpgradeEnabled | OS upgrade messages | Low | Disable |
| ShowAnnouncementNotifications | Feature announcements | Low | User choice |

---

## File: docs/Enterprise-Deployment.md

# Enterprise Chrome Deployment Guide

## Deployment Methods

### Windows Deployment
1. **Group Policy**: Deploy via Active Directory
2. **SCCM**: System Center Configuration Manager
3. **Intune**: Microsoft Endpoint Manager
4. **PowerShell DSC**: Desired State Configuration

### macOS Deployment
1. **Jamf Pro**: macOS device management
2. **Munki**: Open-source management
3. **Apple Configurator**: iOS/macOS deployment
4. **Manual deployment**: Script-based installation

## Policy Templates

### Windows Registry Policies
```reg
[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Google\Chrome]
"MetricsReportingEnabled"=dword:00000000
"DeveloperToolsDisabled"=dword:00000001
"IncognitoModeAvailability"=dword:00000001
"ExtensionInstallBlocklist"=REG_MULTI_SZ:"*"
```

### macOS Managed Preferences
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>MetricsReportingEnabled</key>
    <false/>
    <key>DeveloperToolsDisabled</key>
    <true/>
    <key>IncognitoModeAvailability</key>
    <integer>1</integer>
</dict>
</plist>
```

## Centralized Management

### Configuration Distribution
- **Master golden image**: Pre-configured installations
- **Script deployment**: Automated configuration application
- **Policy inheritance**: Hierarchical policy application
- **User overrides**: Controlled user customization

### Monitoring and Compliance
- **Policy verification**: Automated compliance checking
- **Usage reporting**: Deployment success metrics
- **Security auditing**: Policy adherence monitoring
- **Update management**: Controlled version deployment

---

## Installation Instructions

1. **Download the scripts** and organize them according to the directory structure
2. **Set appropriate permissions**:
   - Windows: Run PowerShell as Administrator
   - macOS: `chmod +x macos/install-chrome.sh`
3. **Customize settings** by modifying script parameters
4. **Test in development** environment before production deployment
5. **Deploy to target systems** using your preferred method

## Features Summary

✅ **Automated Installation**: Downloads and installs Chrome silently  
✅ **Privacy Configuration**: Comprehensive tracking protection  
✅ **Enterprise Policies**: Business security and compliance  
✅ **Uninstall Capabilities**: Clean removal with data options  
✅ **Status Monitoring**: Detailed installation status reporting  
✅ **Default Browser**: Automatic browser configuration  
✅ **Update Management**: Configurable automatic updates  
✅ **Cross-Platform**: Windows and macOS support  

## Support and Troubleshooting

### Common Issues
- **Permission errors**: Ensure administrator/sudo access
- **Download failures**: Check internet connectivity and firewalls
- **Policy conflicts**: Review existing browser management systems
- **Default browser**: May require user confirmation on some systems

### Diagnostic Commands
- **Status check**: Use `--status` flag to verify installation
- **Log files**: Check installation logs for detailed error information
- **Policy verification**: Confirm enterprise policies are applied correctly

This package provides enterprise-ready Chrome deployment automation with comprehensive privacy and security controls.