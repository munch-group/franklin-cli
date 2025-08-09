param(
    [string]$OrganizationName = "",
    [switch]$EnableWSL2 = $true,
    [switch]$DisableAnalytics = $true
)

# Verify administrator privileges
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Administrator privileges required"
    exit 1
}

# Enable Windows features for WSL2
if ($EnableWSL2) {
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    
    # Download and install WSL2 kernel
    $wslKernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
    $wslKernelPath = "$env:TEMP\wsl_update_x64.msi"
    Invoke-WebRequest -Uri $wslKernelUrl -OutFile $wslKernelPath
    Start-Process msiexec.exe -Wait -ArgumentList "/I $wslKernelPath /quiet"
    wsl --set-default-version 2
}

# Download and install Docker Desktop
$dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker Desktop Installer.exe"
$dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller

$installArgs = @('install', '--quiet', '--accept-license', '--backend=wsl-2')
if ($OrganizationName) {
    $installArgs += "--allowed-org=$OrganizationName"
}

Start-Process $dockerInstaller -Wait -ArgumentList $installArgs

# Add current user to docker-users group
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Add-LocalGroupMember -Group "docker-users" -Member $currentUser -ErrorAction SilentlyContinue

# Configure analytics settings if requested
if ($DisableAnalytics) {
    $settingsPath = "$env:APPDATA\Docker\settings-store.json"
    if (Test-Path $settingsPath) {
        $settings = Get-Content $settingsPath | ConvertFrom-Json
        $settings | Add-Member -Type NoteProperty -Name analyticsEnabled -Value $false -Force
        $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath
    }
}

Write-Host "Installation complete. Restart required for group membership changes."