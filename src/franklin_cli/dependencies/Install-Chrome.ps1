[CmdletBinding()]
param(
    [string]$InstallPath = "${env:ProgramFiles}\Google\Chrome\Application",
    [switch]$SetAsDefault = $false,
    [switch]$DisableUpdates = $false,
    [switch]$DisableTracking = $true,
    [switch]$EnterpriseMode = $false,
    [string]$HomepageURL = "",
    [switch]$Uninstall = $false,
    [switch]$CleanUninstall = $false,
    [switch]$StatusCheck = $false,
    [switch]$Force = $false,
    [switch]$Quiet = $false
)

function Write-UnlessQuiet {
    param([string]$Message, [string]$Color = "White")
    if (-not $Quiet) {
        Write-Host  $Message -ForegroundColor $Color
    }
}

# Verify administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-UnlessQuiet  ""
    Write-UnlessQuiet  "Administrator privileges required for Chrome installation" Green
    Write-UnlessQuiet  ""
    # Write-UnlessQuiet  "User Password:" Green
    Write-UnlessQuiet  "Please approve the Administrator prompt that will appear..." Cyan
    Write-UnlessQuiet  ""
    
    # Attempt to restart script with elevation
    $arguments = @()
    if ($InstallPath) { $arguments += "-InstallPath", "`"$InstallPath`"" }
    if ($SetAsDefault) { $arguments += "-SetAsDefault" }
    if ($DisableUpdates) { $arguments += "-DisableUpdates" }
    if ($DisableTracking) { $arguments += "-DisableTracking" }
    if ($EnterpriseMode) { $arguments += "-EnterpriseMode" }
    if ($HomepageURL) { $arguments += "-HomepageURL", "`"$HomepageURL`"" }
    if ($Uninstall) { $arguments += "-Uninstall" }
    if ($CleanUninstall) { $arguments += "-CleanUninstall" }
    if ($StatusCheck) { $arguments += "-StatusCheck" }
    if ($Force) { $arguments += "-Force" }
    if ($PSCmdlet.MyInvocation.BoundParameters.ContainsKey('Quiet')) { $arguments += "-Quiet" }
    if ($PSCmdlet.MyInvocation.BoundParameters.ContainsKey('Verbose')) { $arguments += "-Verbose" }
    
    Start-Process PowerShell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $($arguments -join ' ')" -Wait
    exit $LASTEXITCODE
}

function Get-ChromeInstallationStatus {
    Write-UnlessQuiet  "=== Google Chrome Installation Status ===" Cyan
    
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
    
    Write-UnlessQuiet  "Chrome Installed: $chromeInstalled" $(if ($chromeInstalled) { "Green" } else { "Red" })
    
    if ($chromeInstalled) {
        $version = (Get-Item $chromePath).VersionInfo.FileVersion
        Write-UnlessQuiet  "Version: $version" White
        Write-UnlessQuiet  "Location: $chromePath" White
    }
    
    # Check Chrome update service
    $updateService = Get-Service -Name "gupdate" -ErrorAction SilentlyContinue
    if ($updateService) {
        Write-UnlessQuiet  "Update Service: $($updateService.Status)" White
    } else {
        Write-UnlessQuiet  "Update Service: Not found" Red
    }
    
    # Check default browser
    try {
        $defaultBrowser = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice" -Name ProgId -ErrorAction SilentlyContinue
        if ($defaultBrowser -and $defaultBrowser.ProgId -like "*Chrome*") {
            Write-UnlessQuiet  "Default Browser: Chrome" Green
        } else {
            Write-UnlessQuiet  "Default Browser: Not Chrome" Yellow
        }
    } catch {
        Write-UnlessQuiet  "Default Browser: Cannot determine" Red
    }
    
    # Check user profiles
    $profilePath = "$env:LOCALAPPDATA\Google\Chrome\User Data"
    if (Test-Path $profilePath) {
        $profiles = Get-ChildItem $profilePath -Directory | Where-Object { $_.Name -like "Profile*" -or $_.Name -eq "Default" }
        Write-UnlessQuiet  "User Profiles: $($profiles.Count)" White
        
        $totalSize = (Get-ChildItem $profilePath -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $sizeGB = [math]::Round($totalSize / 1GB, 2)
        Write-UnlessQuiet  "Profile Data Size: $sizeGB GB" White
    } else {
        Write-UnlessQuiet  "User Profiles: None found" Red
    }
    
    # Check enterprise policies
    $policyPath = "HKLM:\SOFTWARE\Policies\Google\Chrome"
    if (Test-Path $policyPath) {
        $policies = Get-ChildItem $policyPath -Recurse -ErrorAction SilentlyContinue
        Write-UnlessQuiet  "Enterprise Policies: $($policies.Count) configured" White
    } else {
        Write-UnlessQuiet  "Enterprise Policies: None configured" Yellow
    }
}

function Remove-GoogleChrome {
    param(
        [switch]$KeepUserData = $false
    )
    
    Write-UnlessQuiet  "Starting Google Chrome uninstallation..." Yellow
    
    try {
        # Stop Chrome processes
        Write-UnlessQuiet  "Stopping Chrome processes..." Yellow
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
            Write-UnlessQuiet  "Running Chrome uninstaller..." Yellow
            $uninstallCmd = $chromeApp.UninstallString
            
            # Add silent flags if not present
            if ($uninstallCmd -notlike "*--force-uninstall*") {
                $uninstallCmd += " --force-uninstall"
            }
            if ($uninstallCmd -notlike "*--system-level*") {
                $uninstallCmd += " --system-level"
            }
            
            Write-UnlessQuiet  "Executing: $uninstallCmd" Cyan
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
                Write-UnlessQuiet  "Removing: $path" Yellow
                Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-UnlessQuiet  "Removed: $path" Green
            }
        }
        
        # Remove user data if requested
        if (-not $KeepUserData) {
            Write-UnlessQuiet  "Removing user data..." Yellow
            
            # Get all user profiles
            $users = Get-ChildItem "C:\Users" -Directory -ErrorAction SilentlyContinue
            foreach ($user in $users) {
                $userChromePath = "$($user.FullName)\AppData\Local\Google\Chrome"
                if (Test-Path $userChromePath) {
                    Remove-Item $userChromePath -Recurse -Force -ErrorAction SilentlyContinue
                    Write-UnlessQuiet  "Removed user data for: $($user.Name)" Green
                }
            }
            
            # Remove current user data
            $currentUserPath = "$env:LOCALAPPDATA\Google\Chrome"
            if (Test-Path $currentUserPath) {
                Remove-Item $currentUserPath -Recurse -Force -ErrorAction SilentlyContinue
                Write-UnlessQuiet  "Removed current user Chrome data" Green
            }
        }
        
        # Remove services
        Write-UnlessQuiet  "Removing Chrome services..." Yellow
        $services = @("gupdate", "gupdatem", "GoogleChromeElevationService")
        foreach ($serviceName in $services) {
            $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ($service) {
                Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
                sc.exe delete $serviceName
                Write-UnlessQuiet  "Removed service: $serviceName" Green
            }
        }
        
        # Remove registry entries
        Write-UnlessQuiet  "Cleaning registry entries..." Yellow
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
                Write-UnlessQuiet  "Removed registry: $regPath" Green
            }
        }
        
        # Remove shortcuts
        Write-UnlessQuiet  "Removing shortcuts..." Yellow
        $shortcutPaths = @(
            "$env:PUBLIC\Desktop\Google Chrome.lnk",
            "$env:USERPROFILE\Desktop\Google Chrome.lnk",
            "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Google Chrome.lnk",
            "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Google Chrome.lnk"
        )
        
        foreach ($shortcut in $shortcutPaths) {
            if (Test-Path $shortcut) {
                Remove-Item $shortcut -Force -ErrorAction SilentlyContinue
                Write-UnlessQuiet  "Removed shortcut: $shortcut" Green
            }
        }
        
        Write-UnlessQuiet  "Google Chrome uninstallation completed!" Green
        
    } catch {
        Write-Error "Uninstallation failed: $($_.Exception.Message)"
        return $false
    }
    
    return $true
}

function Install-GoogleChrome {
    Write-UnlessQuiet  "Starting Google Chrome installation..." Green
    
    # Download Chrome installer
    $installerUrl = "https://dl.google.com/chrome/install/latest/chrome_installer.exe"
    $installerPath = "$env:TEMP\chrome_installer.exe"
    
    Write-UnlessQuiet  "Downloading Chrome installer..." Yellow
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Error "Failed to download Chrome installer: $($_.Exception.Message)"
        return $false
    }
    
    # Install Chrome silently
    Write-UnlessQuiet  "Installing Chrome..." Yellow
    $installArgs = @("/silent", "/install")
    
    try {
        $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
        if ($process.ExitCode -eq 0) {
            Write-UnlessQuiet  "Chrome installed successfully" Green
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
    Write-UnlessQuiet  "Configuring Google Chrome..." Yellow
    
    # Create Chrome policies registry path
    $policyPath = "HKLM:\SOFTWARE\Policies\Google\Chrome"
    if (!(Test-Path $policyPath)) {
        New-Item $policyPath -Force | Out-Null
    }
    
    # Configure based on parameters
    if ($DisableUpdates) {
        Write-UnlessQuiet  "Disabling Chrome updates..." Yellow
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
        Write-UnlessQuiet  "Configuring privacy settings..." Yellow
        
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
        Write-UnlessQuiet  "Setting homepage to: $HomepageURL" Yellow
        Set-ItemProperty -Path $policyPath -Name "HomepageLocation" -Value $HomepageURL -Type String
        Set-ItemProperty -Path $policyPath -Name "HomepageIsNewTabPage" -Value 0 -Type DWord
    }
    
    if ($EnterpriseMode) {
        Write-UnlessQuiet  "Configuring enterprise settings..." Yellow
        
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
    
    Write-UnlessQuiet  "Chrome configuration applied" Green
}

function Set-ChromeAsDefault {
    Write-UnlessQuiet  "Setting Chrome as default browser..." Yellow
    
    try {
        # Use Chrome's built-in method to set as default
        $chromePath = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
        if (!(Test-Path $chromePath)) {
            $chromePath = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
        }
        
        if (Test-Path $chromePath) {
            Start-Process -FilePath $chromePath -ArgumentList "--make-default-browser" -Wait
            Write-UnlessQuiet  "Chrome set as default browser" Green
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
    Write-UnlessQuiet  "Google Chrome Uninstallation" Red
    Write-UnlessQuiet  "=============================" Red
    
    # Show current status
    Get-ChromeInstallationStatus
    
    Write-UnlessQuiet  "`nUninstall Options:" Yellow
    if ($CleanUninstall) {
        Write-UnlessQuiet  "- Clean uninstall: Removes Chrome and ALL user data (bookmarks, history, etc.)" White
    } else {
        Write-UnlessQuiet  "- Standard uninstall: Removes Chrome but keeps user data" White
    }
    
    $confirmUninstall = Read-Host "`nProceed with uninstallation? (yes/no)"
    if ($confirmUninstall -ne "yes") {
        Write-UnlessQuiet  "Uninstallation cancelled" Yellow
        exit 0
    }
    
    if ($CleanUninstall) {
        $result = Remove-GoogleChrome
    } else {
        $result = Remove-GoogleChrome -KeepUserData
    }
    
    if ($result) {
        Write-UnlessQuiet  "`nFinal status check:" Cyan
        Get-ChromeInstallationStatus
    }
    
    exit $(if ($result) { 0 } else { 1 })
}

# Normal installation flow
Write-UnlessQuiet  "Google Chrome Installation and Configuration" Green
Write-UnlessQuiet  "===========================================" Green

# Check if Chrome is already installed
$chromeExe = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
$chromeExe32 = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"

if ((Test-Path $chromeExe) -or (Test-Path $chromeExe32)) {
    Write-UnlessQuiet  "Chrome is already installed. Applying configuration..." Yellow
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

Write-UnlessQuiet  "`nInstallation and configuration complete!" Green
Write-UnlessQuiet  "Usage:" Yellow
Write-UnlessQuiet  "- To check status: $($MyInvocation.MyCommand.Name) -StatusCheck" White
Write-UnlessQuiet  "- To uninstall: $($MyInvocation.MyCommand.Name) -Uninstall" White
Write-UnlessQuiet  "- To clean uninstall: $($MyInvocation.MyCommand.Name) -CleanUninstall" White

# Show final status
Write-UnlessQuiet  "`nFinal installation status:" Cyan
Get-ChromeInstallationStatus