#Requires -Version 5.0
<#
.SYNOPSIS
    Franklin Development Environment - Simplified Web Installer for Windows
    This version is optimized for the irm | iex pattern
#>

param(
    [string]$Role = 'student',
    [switch]$SkipMiniforge,
    [switch]$SkipPixi,
    [switch]$SkipDocker,
    [switch]$SkipChrome,
    [switch]$SkipFranklin,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

# Use TLS 1.2 for secure connections
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host ""
Write-Host "Franklin Development Environment Installer" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Download the main installer using WebClient for better compatibility
$tempDir = Join-Path $env:TEMP "franklin-installer-$(Get-Random)"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    # Determine URLs
    $baseUrl = "https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin_cli/dependencies"
    
    # Try GitHub Pages first
    try {
        $testUrl = "https://munch-group.github.io/franklin/installers/scripts/Master-Installer.ps1"
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "PowerShell")
        $testContent = $webClient.DownloadString($testUrl)
        if ($testContent -match "Franklin") {
            $baseUrl = "https://munch-group.github.io/franklin/installers/scripts"
        }
    } catch {
        # Use raw GitHub as fallback
    }
    
    Write-Host "[INFO] Using base URL: $baseUrl" -ForegroundColor Green
    
    # Download master installer
    $masterPath = Join-Path $tempDir "Master-Installer.ps1"
    Write-Host "[INFO] Downloading master installer..." -ForegroundColor Green
    
    $webClient = New-Object System.Net.WebClient
    $webClient.Headers.Add("User-Agent", "PowerShell/Franklin")
    $webClient.DownloadFile("$baseUrl/Master-Installer.ps1", $masterPath)
    
    # Download component installers
    $scripts = @(
        "Install-Miniforge.ps1",
        "Install-Pixi.ps1", 
        "Install-Docker-Desktop.ps1",
        "Install-Chrome.ps1"
    )
    
    foreach ($script in $scripts) {
        try {
            Write-Host "[INFO] Downloading $script..." -ForegroundColor Green
            $scriptPath = Join-Path $tempDir $script
            $webClient.DownloadFile("$baseUrl/$script", $scriptPath)
        }
        catch {
            Write-Host "[WARN] Could not download $script" -ForegroundColor Yellow
        }
    }
    
    # Build arguments
    $args = @()
    if ($Role -ne 'student') { $args += '--role', $Role }
    if ($SkipMiniforge) { $args += '--skip-miniforge' }
    if ($SkipPixi) { $args += '--skip-pixi' }
    if ($SkipDocker) { $args += '--skip-docker' }
    if ($SkipChrome) { $args += '--skip-chrome' }
    if ($SkipFranklin) { $args += '--skip-franklin' }
    if ($Force) { $args += '--force' }
    
    # Run installer
    Write-Host ""
    Write-Host "[INFO] Starting installation for role: $Role" -ForegroundColor Green
    Write-Host ""
    
    Push-Location $tempDir
    try {
        if ($args.Count -gt 0) {
            & $masterPath @args
        } else {
            & $masterPath
        }
    }
    finally {
        Pop-Location
    }
}
catch {
    Write-Host "[ERROR] Installation failed: $_" -ForegroundColor Red
    exit 1
}
finally {
    # Cleanup
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}