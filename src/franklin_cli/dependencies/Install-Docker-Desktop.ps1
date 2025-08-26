[CmdletBinding()]
param(
    [string]$OrganizationName = "",
    [switch]$EnableWSL2 = $true,
    [switch]$DisableAnalytics = $true,
    [switch]$AutoRepairWSL = $true,
    [switch]$Force = $false,
    [switch]$Uninstall = $false,
    [switch]$CleanUninstall = $false
)

# Optimize download performance
$ProgressPreference = 'SilentlyContinue'

# Logging functions
function Write-VerboseMessage {
    param([string]$Message, [string]$Color = "White")
    if ($VerbosePreference -eq 'Continue') {
        Write-Host $Message -ForegroundColor $Color
    }
}

function Write-InfoMessage {
    param([string]$Message)
    if ($VerbosePreference -eq 'Continue') {
        Write-Host "[INFO] $Message" -ForegroundColor Cyan
    }
}

function Write-ErrorMessage {
    param([string]$Message)
    # Always show errors regardless of verbose mode
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Verify administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host ""
    Write-Host "Administrator privileges required for Docker Desktop installation" -ForegroundColor Green
    Write-Host ""
    # Write-Host "User Password:" -ForegroundColor Green
    Write-Host "When prompted, please allow the app to make changes to your device..." -ForegroundColor Green
    Write-Host ""
    
    # Attempt to restart script with elevation
    $arguments = @()
    if ($OrganizationName) { $arguments += "-OrganizationName", $OrganizationName }
    if ($EnableWSL2) { $arguments += "-EnableWSL2" }
    if ($DisableAnalytics) { $arguments += "-DisableAnalytics" }
    if ($AutoRepairWSL) { $arguments += "-AutoRepairWSL" }
    if ($Force) { $arguments += "-Force" }
    if ($Uninstall) { $arguments += "-Uninstall" }
    if ($CleanUninstall) { $arguments += "-CleanUninstall" }
    if ($PSCmdlet.MyInvocation.BoundParameters.ContainsKey('Verbose')) { $arguments += "-Verbose" }
    
    Start-Process PowerShell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $($arguments -join ' ')" -Wait
    exit $LASTEXITCODE
}

function Remove-DockerDesktop {
    param(
        [switch]$KeepUserData = $false,
        [switch]$KeepWSLDistros = $false,
        [switch]$Silent = $false
    )
    
    Write-VerboseMessage "Starting Docker Desktop uninstallation..." "Yellow"
    
    try {
        # Stop Docker Desktop and related services
        Write-VerboseMessage "Stopping Docker Desktop services..." "Yellow"
        
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
            Write-VerboseMessage "Removing Docker WSL distros..." "Yellow"
            wsl --unregister docker-desktop 2>$null
            wsl --unregister docker-desktop-data 2>$null
        }
        
        # Uninstall Docker Desktop
        Write-VerboseMessage "Uninstalling Docker Desktop..." "Yellow"
        
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
                        Write-VerboseMessage "Running uninstaller: $($app.UninstallString)" "Cyan"
                        $uninstallArgs = $app.UninstallString -replace "msiexec.exe", "" -replace "/I", "/X"
                        Start-Process "msiexec.exe" -ArgumentList "$uninstallArgs /quiet /norestart" -Wait
                    }
                }
            }
        }
        
        # Remove installation directories
        Write-VerboseMessage "Removing Docker Desktop files..." "Yellow"
        
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
            Write-VerboseMessage "Removing user data..." "Yellow"
            
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
        Write-VerboseMessage "Cleaning registry entries..." "Yellow"
        
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
        Write-VerboseMessage "Removing users from docker-users group..." "Yellow"
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
        if (-not $Silent) {
            $confirmation = Read-Host "Remove Hyper-V and Virtual Machine Platform features? This may affect other virtualization software (y/N)"
            if ($confirmation -eq "y" -or $confirmation -eq "Y") {
                Write-VerboseMessage "Disabling Windows virtualization features..." "Yellow"
                dism.exe /online /disable-feature /featurename:Microsoft-Hyper-V-All /norestart
                dism.exe /online /disable-feature /featurename:VirtualMachinePlatform /norestart
                dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart
            }
        } else {
            Write-VerboseMessage "Skipping Windows feature removal (silent mode)" "Yellow"
        }
        
        # Clean up firewall rules
        Write-VerboseMessage "Removing Docker firewall rules..." "Yellow"
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

# If Force flag is set and Docker Desktop is installed, uninstall first
if ($Force) {
    $dockerInstalled = Test-Path "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if ($dockerInstalled) {
        Write-Host "Force flag specified. Uninstalling existing Docker Desktop first..." -ForegroundColor Yellow
        $uninstallResult = Remove-DockerDesktop -KeepUserData -KeepWSLDistros -Silent  # Keep user data, silent mode for force reinstall
        if (-not $uninstallResult) {
            Write-Error "Failed to uninstall existing Docker Desktop"
            exit 1
        }
        Write-Host "Existing installation removed. Proceeding with fresh installation..." -ForegroundColor Green
    }
}

# Enable Windows features for WSL2
if ($EnableWSL2) {
    Write-VerboseMessage "Enabling WSL2 features..." "Yellow"
    
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    
    # Download and install WSL2 kernel
    $wslKernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
    $wslKernelPath = "$env:TEMP\wsl_update_x64.msi"
    Invoke-WebRequest -Uri $wslKernelUrl -OutFile $wslKernelPath -UseBasicParsing
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
Write-VerboseMessage "Downloading Docker Desktop..." "Yellow"
$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker Desktop Installer.exe"
$dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller -UseBasicParsing

$installArgs = @('install', '--quiet', '--accept-license', '--backend=wsl-2')
if ($OrganizationName) {
    $installArgs += "--allowed-org=$OrganizationName"
}

Write-VerboseMessage "Installing Docker Desktop..." "Yellow"
Start-Process $dockerInstaller -Wait -ArgumentList $installArgs

# Add current user to docker-users group
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Add-LocalGroupMember -Group "docker-users" -Member $currentUser -ErrorAction SilentlyContinue

# Configure Docker Desktop settings
Write-VerboseMessage "Configuring Docker Desktop settings..." "Yellow"

$dockerConfig = @{
    AutoDownloadUpdates = $true
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

# Apply Docker Desktop configuration
$settingsPath = "$env:APPDATA\Docker\settings-store.json"
try {
    # Create Docker settings directory if it doesn't exist
    $dockerDir = Split-Path $settingsPath -Parent
    if (-not (Test-Path $dockerDir)) {
        New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null
    }
    
    # Write the configuration to the settings file
    $dockerConfig | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
    Write-Host "Docker Desktop configuration applied" -ForegroundColor Green
} catch {
    Write-Warning "Could not apply Docker Desktop configuration: $($_.Exception.Message)"
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

# Stop Docker Desktop completely after installation
Write-Host "`nStopping Docker Desktop to complete installation..." -ForegroundColor Yellow

# Stop all Docker-related processes
$dockerProcesses = @(
    "Docker Desktop",
    "com.docker.backend",
    "com.docker.proxy",
    "com.docker.helper",
    "vpnkit",
    "Docker"
)

foreach ($processName in $dockerProcesses) {
    $processes = Get-Process -Name $processName -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "Stopping $processName..." -ForegroundColor Cyan
        $processes | Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

# Stop Docker service if running
$dockerService = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
if ($dockerService -and $dockerService.Status -eq 'Running') {
    Write-Host "Stopping Docker service..." -ForegroundColor Cyan
    Stop-Service -Name "com.docker.service" -Force -ErrorAction SilentlyContinue
}

# Wait to ensure complete shutdown
Start-Sleep -Seconds 3

# Verify Docker is stopped
$stillRunning = Get-Process -Name "Docker*" -ErrorAction SilentlyContinue
if ($stillRunning) {
    Write-Host "Force stopping remaining Docker processes..." -ForegroundColor Yellow
    $stillRunning | Stop-Process -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

# Update WSL if enabled
if ($EnableWSL2) {
    Write-Host "`nUpdating WSL..." -ForegroundColor Yellow
    try {
        $wslUpdateProcess = Start-Process -FilePath "wsl" -ArgumentList "--update" -Wait -PassThru -NoNewWindow
        if ($wslUpdateProcess.ExitCode -eq 0) {
            Write-Host "WSL updated successfully" -ForegroundColor Green
        } else {
            Write-Warning "WSL update completed with exit code $($wslUpdateProcess.ExitCode)"
        }
    } catch {
        Write-Warning "Could not update WSL: $($_.Exception.Message)"
    }
}

Write-Host "`nInstallation and configuration complete!" -ForegroundColor Green
Write-Host ""
# Write-Host "Docker Desktop has been installed and configured." -ForegroundColor Green
# Write-Host "Docker Desktop has been stopped and is NOT currently running." -ForegroundColor Cyan
# Write-Host ""
# Write-Host "Next steps:" -ForegroundColor Yellow
# Write-Host "1. Restart your computer to ensure group membership takes effect" -ForegroundColor White
# Write-Host "2. Start Docker Desktop from the Start Menu when needed" -ForegroundColor White
# Write-Host "3. Docker will be available in the system tray when running" -ForegroundColor White

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
