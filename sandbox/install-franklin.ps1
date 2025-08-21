#Requires -Version 5.0
<#
.SYNOPSIS
    Franklin Installer Launcher - Download and run this script locally
    
.DESCRIPTION
    This script downloads and runs the Franklin installer without redirect issues.
    Save this file locally and run it from PowerShell.
    
.EXAMPLE
    # Save this file as install-franklin.ps1 and run:
    .\install-franklin.ps1
    
.EXAMPLE
    # With parameters:
    .\install-franklin.ps1 -Role educator
    .\install-franklin.ps1 -SkipDocker -SkipChrome
#>

param(
    [ValidateSet('student', 'educator', 'administrator')]
    [string]$Role = 'student',
    [switch]$SkipMiniforge,
    [switch]$SkipPixi,
    [switch]$SkipDocker,
    [switch]$SkipChrome,
    [switch]$SkipFranklin,
    [switch]$Force,
    [switch]$Help
)

# Set up TLS 1.2 for secure connections
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host ""
Write-Host "Franklin Development Environment Installer Launcher" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

if ($Help) {
    Write-Host @"
USAGE:
    .\install-franklin.ps1 [OPTIONS]
    
OPTIONS:
    -Role           User role: student, educator, or administrator (default: student)
    -SkipMiniforge  Skip Miniforge installation
    -SkipPixi       Skip Pixi installation
    -SkipDocker     Skip Docker Desktop installation
    -SkipChrome     Skip Chrome installation
    -SkipFranklin   Skip Franklin installation
    -Force          Force reinstall all components
    -Help           Show this help message
    
EXAMPLES:
    .\install-franklin.ps1                    # Default student installation
    .\install-franklin.ps1 -Role educator     # Educator installation
    .\install-franklin.ps1 -SkipDocker        # Skip Docker
"@
    exit 0
}

Write-Host "Downloading Franklin installer..." -ForegroundColor Green

try {
    # Direct URL to avoid any redirects
    $installerUrl = "https://raw.githubusercontent.com/munch-group/franklin-cli/main/src/franklin_cli/dependencies/web-install.ps1"
    
    # Download using WebClient (most reliable)
    $webClient = New-Object System.Net.WebClient
    $webClient.Headers.Add("User-Agent", "PowerShell/Franklin-Launcher")
    
    # Add proxy support if needed
    $webClient.Proxy = [System.Net.WebRequest]::GetSystemWebProxy()
    $webClient.Proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
    
    Write-Host "Fetching installer from GitHub..." -ForegroundColor Gray
    $installerScript = $webClient.DownloadString($installerUrl)
    
    Write-Host "Installer downloaded successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Create script block from downloaded content
    $scriptBlock = [scriptblock]::Create($installerScript)
    
    # Build parameters to pass
    $parameters = @{}
    if ($Role -ne 'student') { $parameters['Role'] = $Role }
    if ($SkipMiniforge) { $parameters['SkipMiniforge'] = $true }
    if ($SkipPixi) { $parameters['SkipPixi'] = $true }
    if ($SkipDocker) { $parameters['SkipDocker'] = $true }
    if ($SkipChrome) { $parameters['SkipChrome'] = $true }
    if ($SkipFranklin) { $parameters['SkipFranklin'] = $true }
    if ($Force) { $parameters['Force'] = $true }
    
    # Run the installer with parameters
    Write-Host "Starting installation..." -ForegroundColor Green
    & $scriptBlock @parameters
}
catch {
    Write-Host ""
    Write-Host "ERROR: Failed to download or run installer" -ForegroundColor Red
    Write-Host "Error details: $_" -ForegroundColor Yellow
    Write-Host ""
    
    if ($_.Exception.Message -match "host|DNS|resolve|connect") {
        Write-Host "This appears to be a network issue. Please check:" -ForegroundColor Yellow
        Write-Host "  1. Your internet connection" -ForegroundColor White
        Write-Host "  2. Firewall settings (allow access to github.com)" -ForegroundColor White
        Write-Host "  3. Proxy settings if behind a corporate firewall" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "Alternative: Download the installer manually from:" -ForegroundColor Cyan
    Write-Host "  https://github.com/munch-group/franklin" -ForegroundColor White
    
    exit 1
}