param(
    [string]$InstallPath = "${env:ProgramFiles}\Google\Chrome\Application",
    [switch]$SetAsDefault = $false,
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
    Write-Host ""
    Write-Host "Administrator privileges required for Chrome installation" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "User Password:" -ForegroundColor Green
    Write-Host "Please approve the Administrator prompt that will appear..." -ForegroundColor Cyan
    Write-Host ""
    
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
    
    Start-Process PowerShell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $($arguments -join ' ')" -Wait
    exit $LASTEXITCODE
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
                Write-Host "[OK] Removed: $path" -ForegroundColor Green
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
                    Write-Host "[OK] Removed user data for: $($user.Name)" -ForegroundColor Green
                }
            }
            
            # Remove current user data
            $currentUserPath = "$env:LOCALAPPDATA\Google\Chrome"
            if (Test-Path $currentUserPath) {
                Remove-Item $currentUserPath -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "[OK] Removed current user Chrome data" -ForegroundColor Green
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
                Write-Host "[OK] Removed service: $serviceName" -ForegroundColor Green
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
                Write-Host "[OK] Removed registry: $regPath" -ForegroundColor Green
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
                Write-Host "[OK] Removed shortcut: $shortcut" -ForegroundColor Green
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
            Write-Host "[OK] Chrome installed successfully" -ForegroundColor Green
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
    
    Write-Host "[OK] Chrome configuration applied" -ForegroundColor Green
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
            Write-Host "[OK] Chrome set as default browser" -ForegroundColor Green
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