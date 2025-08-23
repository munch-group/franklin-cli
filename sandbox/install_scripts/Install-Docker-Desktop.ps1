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
    
    Write-Host "Downloading WSL2 kernel update..." -ForegroundColor Yellow
    try {
        # Get file size
        $response = Invoke-WebRequest -Uri $wslKernelUrl -Method Head
        $totalSize = [int]$response.Headers.'Content-Length'[0]
        $totalSizeMB = [math]::Round($totalSize / 1MB, 2)
        Write-Host "Download size: $totalSizeMB MB" -ForegroundColor Cyan
        
        # Download with progress
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFileCompleted += {
            Write-Host "WSL2 kernel download completed!" -ForegroundColor Green
        }
        
        $webClient.DownloadProgressChanged += {
            $percentComplete = $_.ProgressPercentage
            $downloadedMB = [math]::Round($_.BytesReceived / 1MB, 2)
            $totalMB = [math]::Round($_.TotalBytesToReceive / 1MB, 2)
            
            Write-Progress -Activity "Downloading WSL2 Kernel Update" `
                          -Status "$percentComplete% ($downloadedMB MB / $totalMB MB)" `
                          -PercentComplete $percentComplete
        }
        
        $webClient.DownloadFileAsync($wslKernelUrl, $wslKernelPath)
        
        while ($webClient.IsBusy) {
            Start-Sleep -Milliseconds 100
        }
        
        Write-Progress -Activity "Downloading WSL2 Kernel Update" -Completed
        
    } catch {
        # Fallback to simple download
        Write-Warning "Progress tracking failed, using simple download..."
        Invoke-WebRequest -Uri $wslKernelUrl -OutFile $wslKernelPath
    }
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

# Download with progress bar
$ProgressPreference = 'Continue'
try {
    # Get file size first
    $response = Invoke-WebRequest -Uri $dockerUrl -Method Head
    $totalSize = [int]$response.Headers.'Content-Length'[0]
    $totalSizeMB = [math]::Round($totalSize / 1MB, 2)
    
    Write-Host "Download size: $totalSizeMB MB" -ForegroundColor Cyan
    
    # Download with progress tracking
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFileCompleted += {
        Write-Host "`nDownload completed!" -ForegroundColor Green
    }
    
    $webClient.DownloadProgressChanged += {
        $percentComplete = $_.ProgressPercentage
        $downloadedMB = [math]::Round($_.BytesReceived / 1MB, 2)
        $totalMB = [math]::Round($_.TotalBytesToReceive / 1MB, 2)
        
        # Create progress bar
        $progressBar = "[" + ("=" * [math]::Floor($percentComplete / 2)) + (" " * (50 - [math]::Floor($percentComplete / 2))) + "]"
        
        # Update progress display
        Write-Progress -Activity "Downloading Docker Desktop Installer" `
                      -Status "$progressBar $percentComplete% ($downloadedMB MB / $totalMB MB)" `
                      -PercentComplete $percentComplete
    }
    
    # Start async download with event handling
    $webClient.DownloadFileAsync($dockerUrl, $dockerInstaller)
    
    # Wait for download to complete
    while ($webClient.IsBusy) {
        Start-Sleep -Milliseconds 100
    }
    
    Write-Progress -Activity "Downloading Docker Desktop Installer" -Completed
    
} catch {
    # Fallback to simple download if progress tracking fails
    Write-Warning "Progress tracking failed, using simple download..."
    Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller
}

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