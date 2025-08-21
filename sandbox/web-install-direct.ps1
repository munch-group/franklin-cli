#Requires -Version 5.0
<#
.SYNOPSIS
    Franklin installer - Direct GitHub version (most reliable)
    This version downloads directly from GitHub raw content, avoiding DNS issues
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

# Force TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host ""
Write-Host "Franklin Development Environment Installer (Direct)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# Create temp directory
$tempDir = Join-Path $env:TEMP "franklin-installer-$(Get-Random)"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    # Direct GitHub raw URLs (no DNS redirects)
    $baseUrl = "https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin_cli/dependencies"
    
    Write-Host "[INFO] Downloading from GitHub..." -ForegroundColor Green
    
    # Download function with robust error handling
    function Download-File {
        param($Url, $Path)
        
        $success = $false
        $attempts = 0
        $maxAttempts = 3
        
        while (-not $success -and $attempts -lt $maxAttempts) {
            $attempts++
            try {
                Write-Host "[INFO] Downloading $(Split-Path -Leaf $Path) (attempt $attempts)..." -ForegroundColor Gray
                
                # Method 1: WebClient with proxy support
                $webClient = New-Object System.Net.WebClient
                $webClient.Headers.Add("User-Agent", "PowerShell/Franklin-Installer")
                
                # Configure proxy if system uses one
                $webClient.Proxy = [System.Net.WebRequest]::GetSystemWebProxy()
                $webClient.Proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
                
                $webClient.DownloadFile($Url, $Path)
                $success = $true
                Write-Host "[OK] Downloaded successfully" -ForegroundColor Green
            }
            catch {
                Write-Host "[WARN] Attempt $attempts failed: $_" -ForegroundColor Yellow
                
                if ($attempts -lt $maxAttempts) {
                    Start-Sleep -Seconds 2
                }
                else {
                    # Try one more time with Invoke-WebRequest
                    try {
                        Write-Host "[INFO] Trying alternative download method..." -ForegroundColor Yellow
                        Invoke-WebRequest -Uri $Url -OutFile $Path -UseBasicParsing
                        $success = $true
                        Write-Host "[OK] Downloaded with alternative method" -ForegroundColor Green
                    }
                    catch {
                        throw "Failed to download after $maxAttempts attempts: $_"
                    }
                }
            }
        }
    }
    
    # Download master installer
    $masterPath = Join-Path $tempDir "Master-Installer.ps1"
    Download-File -Url "$baseUrl/Master-Installer.ps1" -Path $masterPath
    
    # Download component installers
    $scripts = @(
        "Install-Miniforge.ps1",
        "Install-Pixi.ps1",
        "Install-Docker-Desktop.ps1",
        "Install-Chrome.ps1"
    )
    
    foreach ($script in $scripts) {
        $scriptPath = Join-Path $tempDir $script
        try {
            Download-File -Url "$baseUrl/$script" -Path $scriptPath
        }
        catch {
            Write-Host "[WARN] Could not download $script (will be skipped)" -ForegroundColor Yellow
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
        
        Write-Host ""
        Write-Host "[SUCCESS] Installation completed!" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}
catch {
    Write-Host ""
    Write-Host "[ERROR] Installation failed: $_" -ForegroundColor Red
    
    # Provide DNS-specific help
    if ($_ -match "host|DNS|resolve|network|download") {
        Write-Host ""
        Write-Host "Network/DNS Troubleshooting:" -ForegroundColor Yellow
        Write-Host "1. Check internet connection" -ForegroundColor White
        Write-Host "2. Try disabling VPN if connected" -ForegroundColor White
        Write-Host "3. Check firewall settings for GitHub access" -ForegroundColor White
        Write-Host "4. Try manual download from:" -ForegroundColor White
        Write-Host "   https://github.com/munch-group/franklin" -ForegroundColor Cyan
    }
    
    exit 1
}
finally {
    # Cleanup
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}