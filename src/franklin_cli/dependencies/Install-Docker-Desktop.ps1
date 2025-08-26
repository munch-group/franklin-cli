[CmdletBinding()]
param(
    [string]$OrganizationName = "",
    [switch]$EnableWSL2 = $true,
    [switch]$DisableAnalytics = $true,
    [switch]$AutoRepairWSL = $true,
    [switch]$Force = $false,
    [switch]$Uninstall = $false,
    [switch]$CleanUninstall = $false,
    [switch]$Quiet = $false
)

# Optimize download performance
$ProgressPreference = 'SilentlyContinue'

# Conditional write - suppressed in quiet mode unless colored
function Write-UnlessQuiet {
    param([string]$Message, [string]$Color = "White")
    if (-not $Quiet) {
        Write-Host  $Message -ForegroundColor $Color
    }
}

# Logging functions
function Write-VerboseMessage {
    param([string]$Message, [string]$Color = "White")
    if ($VerbosePreference -eq 'Continue') {
        Write-UnlessQuiet  $Message $Color
    }
}

function Write-InfoMessage {
    param([string]$Message)
    if ($VerbosePreference -eq 'Continue') {
        Write-UnlessQuiet  "$Message" Cyan
    }
}

function Write-ErrorMessage {
    param([string]$Message)
    # Suppressed in quiet mode
    if (-not $Quiet) {
        Write-UnlessQuiet  "$Message" Red
    }
}

# Always show green text even in quiet mode
function Write-Green {
    param([string]$Message)
    Write-UnlessQuiet  $Message Green
}

# Always show blue text even in quiet mode  
function Write-Blue {
    param([string]$Message)
    Write-UnlessQuiet  $Message Blue
}

# Verify administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-UnlessQuiet ""
    Write-Green "Administrator privileges required for Docker Desktop installation"
    Write-UnlessQuiet ""
    # Write-Green "User Password:"
    Write-Green "When prompted, please allow the app to make changes to your device..."
    Write-UnlessQuiet ""
    
    # Attempt to restart script with elevation
    $arguments = @()
    if ($OrganizationName) { $arguments += "-OrganizationName", $OrganizationName }
    if ($EnableWSL2) { $arguments += "-EnableWSL2" }
    if ($DisableAnalytics) { $arguments += "-DisableAnalytics" }
    if ($AutoRepairWSL) { $arguments += "-AutoRepairWSL" }
    if ($Force) { $arguments += "-Force" }
    if ($Uninstall) { $arguments += "-Uninstall" }
    if ($CleanUninstall) { $arguments += "-CleanUninstall" }
    if ($PSCmdlet.MyInvocation.BoundParameters.ContainsKey('Quiet')) { $arguments += "-Quiet" }
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
                Write-Green "[OK] Removed: $path"
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
                    Write-Green "[OK] Removed: $path"
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
                Write-Green "[OK] Removed registry: $regPath"
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
        if (-not $Silent -and -not $Quiet) {
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
        
        Write-Green "[OK] Docker Desktop uninstallation completed successfully!"
        Write-Blue "A system restart is recommended to complete the removal process."
        
    } catch {
        Write-Error "Uninstallation failed: $($_.Exception.Message)"
        return $false
    }
    
    return $true
}

function Get-DockerInstallationStatus {
    Write-UnlessQuiet "=== Docker Desktop Installation Status ===" "Cyan"
    
    # Check if Docker Desktop is installed
    $dockerExe = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    $dockerInstalled = Test-Path $dockerExe
    
    if ($dockerInstalled) {
        Write-Green "[OK] Docker Desktop: Installed"
    } else {
        Write-UnlessQuiet "[FAILED] Docker Desktop: Not installed" "Red"
    }
    
    if ($dockerInstalled) {
        $version = (Get-Item $dockerExe).VersionInfo.FileVersion
        Write-UnlessQuiet "Version: $version" "White"
    }
    
    # Check Docker service
    $service = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
    if ($service) {
        if ($service.Status -eq "Running") {
            Write-Green "[OK] Docker Service Status: $($service.Status)"
        } else {
            Write-UnlessQuiet "[WARNING] Docker Service Status: $($service.Status)" "Yellow"
        }
        Write-UnlessQuiet "Docker Service Startup: $($service.StartType)" "White"
    } else {
        Write-UnlessQuiet "[FAILED] Docker Service: Not found" "Red"
    }
    
    # Check WSL distros
    Write-UnlessQuiet "`nWSL Docker Distros:" "Yellow"
    try {
        $distros = wsl --list --quiet 2>$null
        $dockerDistros = $distros | Where-Object { $_ -match "docker" }
        if ($dockerDistros) {
            $dockerDistros | ForEach-Object { Write-Green "  [OK] $_" }
        } else {
            Write-UnlessQuiet "  [FAILED] No Docker WSL distros found" "Red"
        }
    } catch {
        Write-UnlessQuiet "  [FAILED] WSL not available" "Red"
    }
    
    # Check user groups
    try {
        $group = Get-LocalGroup -Name "docker-users" -ErrorAction SilentlyContinue
        if ($group) {
            $members = Get-LocalGroupMember -Group "docker-users" -ErrorAction SilentlyContinue
            Write-UnlessQuiet "`nDocker Users Group Members:" "Yellow"
            if ($members) {
                $members | ForEach-Object { Write-Green "  [OK] $($_.Name)" }
            } else {
                Write-UnlessQuiet "  [WARNING] No members" "Yellow"
            }
        } else {
            Write-UnlessQuiet "`n[FAILED] Docker Users Group: Not found" "Red"
        }
    } catch {
        Write-UnlessQuiet "`n[WARNING] Docker Users Group: Could not check" "Yellow"
    }
    
    # Check data directories
    Write-UnlessQuiet "`nData Directories:" "Yellow"
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
        
        if ($exists) {
            Write-Green "  [OK] $path : $exists ($size)"
        } else {
            Write-UnlessQuiet "  [FAILED] $path : $exists" "Red"
        }
    }
}

# Handle uninstall operations
if ($Uninstall -or $CleanUninstall) {
    Write-UnlessQuiet "Docker Desktop Uninstallation" "Red"
    Write-UnlessQuiet "==============================" "Red"
    
    # Show current installation status
    Get-DockerInstallationStatus
    
    Write-UnlessQuiet "`nUninstall Options:" "Yellow"
    Write-UnlessQuiet "- Standard uninstall: Removes Docker Desktop but keeps user data and WSL distros" "White"
    Write-UnlessQuiet "- Clean uninstall: Removes everything including user data and WSL distros" "White"
    
    if ($Quiet) {
        Write-Blue "Proceed with uninstallation? (yes/no):"
        $confirmUninstall = Read-Host
    } else {
        $confirmUninstall = Read-Host "`nProceed with uninstallation? (yes/no)"
    }
    if ($confirmUninstall -ne "yes") {
        Write-UnlessQuiet "Uninstallation cancelled" "Yellow"
        exit 0
    }
    
    if ($CleanUninstall) {
        $result = Remove-DockerDesktop
    } else {
        $result = Remove-DockerDesktop -KeepUserData -KeepWSLDistros
    }
    
    if ($result) {
        Write-UnlessQuiet "`nFinal status check:" "Cyan"
        Get-DockerInstallationStatus
    }
    
    exit $(if ($result) { 0 } else { 1 })
}

# If Force flag is set and Docker Desktop is installed, uninstall first
if ($Force) {
    $dockerInstalled = Test-Path "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if ($dockerInstalled) {
        Write-UnlessQuiet "Force flag specified. Uninstalling existing Docker Desktop first..." "Yellow"
        $uninstallResult = Remove-DockerDesktop -KeepUserData -KeepWSLDistros -Silent  # Keep user data, silent mode for force reinstall
        if (-not $uninstallResult) {
            Write-Error "Failed to uninstall existing Docker Desktop"
            exit 1
        }
        Write-Green "[OK] Existing installation removed. Proceeding with fresh installation..."
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
if ($Quiet) {
    Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller -UseBasicParsing
} else {
    Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller -UseBasicParsing
}

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
    Write-Green "[OK] Docker Desktop configuration applied"
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
            Write-Green "[OK] Analytics disabled"
        } catch {
            Write-Warning "Could not disable analytics in settings file"
        }
    }
}

# Stop Docker Desktop completely after installation
Write-UnlessQuiet "`nStopping Docker Desktop to complete installation..." "Yellow"

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
        Write-VerboseMessage "Stopping $processName..." "Cyan"
        $processes | Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

# Stop Docker service if running
$dockerService = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
if ($dockerService -and $dockerService.Status -eq 'Running') {
    Write-VerboseMessage "Stopping Docker service..." "Cyan"
    Stop-Service -Name "com.docker.service" -Force -ErrorAction SilentlyContinue
}

# Wait to ensure complete shutdown
Start-Sleep -Seconds 3

# Verify Docker is stopped
$stillRunning = Get-Process -Name "Docker*" -ErrorAction SilentlyContinue
if ($stillRunning) {
    Write-VerboseMessage "Force stopping remaining Docker processes..." "Yellow"
    $stillRunning | Stop-Process -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

# Update WSL if enabled
if ($EnableWSL2) {
    Write-UnlessQuiet "`nUpdating WSL..." "Yellow"
    try {
        $wslUpdateProcess = Start-Process -FilePath "wsl" -ArgumentList "--update" -Wait -PassThru -NoNewWindow
        if ($wslUpdateProcess.ExitCode -eq 0) {
            Write-Green "[OK] WSL updated successfully"
        } else {
            Write-Warning "WSL update completed with exit code $($wslUpdateProcess.ExitCode)"
        }
    } catch {
        Write-Warning "Could not update WSL: $($_.Exception.Message)"
    }
}

Write-Green "`n[OK] Installation and configuration complete!"
Write-UnlessQuiet ""
# Write-UnlessQuiet  "Docker Desktop has been installed and configured." Green
# Write-UnlessQuiet  "Docker Desktop has been stopped and is NOT currently running." Cyan
# Write-UnlessQuiet  ""
# Write-UnlessQuiet  "Next steps:" Yellow
# Write-UnlessQuiet  "1. Restart your computer to ensure group membership takes effect" White
# Write-UnlessQuiet  "2. Start Docker Desktop from the Start Menu when needed" White
# Write-UnlessQuiet  "3. Docker will be available in the system tray when running" White

if ($EnableWSL2) {
    Write-Blue "3. Verify WSL2 integration by running: docker run hello-world"
    
    # Show current WSL status
    Write-UnlessQuiet "`nCurrent WSL status:" "Cyan"
    try {
        wsl --list --verbose
    } catch {
        Write-UnlessQuiet "Could not retrieve WSL status. This is normal if WSL was just installed." "Yellow"
    }
}

Write-Blue "`nTo uninstall Docker Desktop later, run this script with -Uninstall or -CleanUninstall"
