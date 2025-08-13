#Requires -Version 5.0
<#
.SYNOPSIS
    Franklin Development Environment - Web Installer for Windows

.DESCRIPTION
    Downloads and runs the Franklin installer without requiring users to deal with SmartScreen warnings.

.PARAMETER Role
    User role: student, educator, or administrator (default: student)

.PARAMETER SkipMiniforge
    Skip Miniforge installation

.PARAMETER SkipPixi
    Skip Pixi installation

.PARAMETER SkipDocker
    Skip Docker Desktop installation

.PARAMETER SkipChrome
    Skip Chrome installation

.PARAMETER SkipFranklin
    Skip Franklin installation

.PARAMETER Force
    Force reinstall all components

.PARAMETER Yes
Auto confirm prompts

.EXAMPLE
    # RECOMMENDED - Most compatible method using WebClient
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1') | iex

.EXAMPLE
    # Alternative using Invoke-WebRequest (iwr) instead of irm
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; iwr -useb https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1 | iex

.EXAMPLE
    # If you must use irm, disable SSL validation (less secure)
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; [Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}; irm https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1 | iex

.NOTES
    Author: Franklin Project
    Version: 1.0.0
#>

[CmdletBinding()]
param(
    [ValidateSet('student', 'educator', 'administrator')]
    [string]$Role = 'student',
    
    [switch]$SkipMiniforge,
    [switch]$SkipPixi,
    [switch]$SkipDocker,
    [switch]$SkipChrome,
    [switch]$SkipFranklin,
    [switch]$Force,
    [switch]$DryRun,
    [switch]$Yes,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Force TLS 1.2 for secure connections (required for GitHub)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Configuration
$RepoOrg = if ($env:FRANKLIN_REPO_ORG) { $env:FRANKLIN_REPO_ORG } else { "munch-group" }
$RepoName = if ($env:FRANKLIN_REPO_NAME) { $env:FRANKLIN_REPO_NAME } else { "franklin" }
$RepoBranch = if ($env:FRANKLIN_REPO_BRANCH) { $env:FRANKLIN_REPO_BRANCH } else { "main" }
$InstallDir = if ($env:FRANKLIN_INSTALL_DIR) { $env:FRANKLIN_INSTALL_DIR } else { "$env:USERPROFILE\.franklin-installer" }

# Determine base URL (GitHub Pages or raw GitHub)
function Get-BaseUrl {
    $ghPagesUrl = "https://$RepoOrg.github.io/$RepoName/installers/scripts"
    $rawGithubUrl = "https://raw.githubusercontent.com/$RepoOrg/$RepoName/$RepoBranch/src/franklin/dependencies"
    
    # Try GitHub Pages first, but handle DNS/network errors gracefully
    try {
        # Use WebClient for better compatibility
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "PowerShell/Installer")
        $testUrl = "$ghPagesUrl/Master-Installer.ps1"
        
        # Try to download just the headers
        $webClient.OpenRead($testUrl).Close()
        return $ghPagesUrl
    }
    catch {
        # Check if it's a DNS error
        if ($_.Exception.Message -match "host|DNS|resolve") {
            Write-ColorOutput "GitHub Pages not accessible, using direct GitHub URL" -Type Warn
        }
        # Fall back to raw GitHub URL
        return $rawGithubUrl
    }
}

# Helper functions
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Type = 'Info'
    )
    
    switch ($Type) {
        'Info' { Write-Host "[INFO] $Message" -ForegroundColor Green }
        'Warn' { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
        'Error' { Write-Host "[ERROR] $Message" -ForegroundColor Red }
        'Step' { Write-Host "[STEP] $Message" -ForegroundColor Cyan }
        'Success' { Write-Host "[OK] $Message" -ForegroundColor Green }
    }
}

function Show-Banner {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "             Franklin Installer             " -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Help {
    Write-Host @"
Franklin Development Environment - Web Installer for Windows

USAGE:
    # RECOMMENDED - Use WebClient to avoid redirect issues
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1') | iex
    
    # Alternative with iwr (Invoke-WebRequest)
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; iwr -useb https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1 | iex

PARAMETERS:
    -Role           User role: student, educator, or administrator (default: student)
    -SkipMiniforge  Skip Miniforge installation
    -SkipPixi       Skip Pixi installation
    -SkipDocker     Skip Docker Desktop installation
    -SkipChrome     Skip Chrome installation
    -SkipFranklin   Skip Franklin installation
    -Force          Force reinstall all components
    -DryRun         Show what would be installed without doing it
    -Yes            Do not prompt for confirmations
    -Help           Show this help message

EXAMPLES:
    # Default installation (student) - RECOMMENDED METHOD
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    (New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1') | iex

    # With parameters - educator role (avoid irm due to redirect issues)
    `$url = 'https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    & ([scriptblock]::Create((New-Object Net.WebClient).DownloadString(`$url))) -Role educator

    # Alternative with iwr (Invoke-WebRequest)
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    iwr -useb https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1 | iex

NOTES:
    - Requires PowerShell 5.0 or later
    - Requires Administrator privileges for some components
    - Internet connection required
"@
}

function Test-Administrator {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Requirements {
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        throw "PowerShell 5.0 or later is required. Current version: $($PSVersionTable.PSVersion)"
    }
    
    # Check execution policy
    $executionPolicy = Get-ExecutionPolicy
    if ($executionPolicy -eq 'Restricted') {
        Write-ColorOutput "Execution policy is Restricted. Attempting to bypass for this session..." -Type Warn
        Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
    }
    
    # Check network connectivity
    try {
        Write-ColorOutput "Checking network connectivity..." -Type Info
        $testConnection = Test-NetConnection -ComputerName "github.com" -Port 443 -WarningAction SilentlyContinue -ErrorAction Stop
        if (-not $testConnection.TcpTestSucceeded) {
            throw "Cannot connect to GitHub. Please check your internet connection."
        }
    }
    catch {
        # Fallback for older PowerShell versions
        try {
            $webClient = New-Object System.Net.WebClient
            $webClient.Headers.Add("User-Agent", "PowerShell/Test")
            $webClient.OpenRead("https://github.com").Close()
        }
        catch {
            throw "Cannot connect to GitHub. Please check your internet connection and DNS settings. Error: $_"
        }
    }
    
    # Check Windows version
    $os = Get-CimInstance Win32_OperatingSystem
    Write-ColorOutput "Windows version: $($os.Caption) - $($os.Version)" -Type Info
    
    # # Check if running as admin (warn only)
    # if (-not (Test-Administrator)) {
    #     Write-ColorOutput "Not running as Administrator. Some components may require elevation." -Type Warn
    # }
}

function Get-TempDirectory {
    $tempPath = [System.IO.Path]::GetTempPath()
    $tempDir = Join-Path $tempPath "franklin-installer-$(Get-Random)"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    return $tempDir
}

function Download-Installers {
    param(
        [string]$TempDir,
        [string]$BaseUrl
    )
    
    Write-ColorOutput "Downloading installer scripts from: $BaseUrl" -Type Step
    
    # Ensure TLS 1.2 is set
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    
    # Core installer
    $masterInstaller = Join-Path $TempDir "Master-Installer.ps1"
    $downloadSuccess = $false
    
    # Try direct download with full error handling
    try {
        Write-ColorOutput "Attempting primary download method..." -Type Info
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "PowerShell/WebInstaller")
        
        # Add proxy settings if needed
        $webClient.Proxy = [System.Net.WebRequest]::GetSystemWebProxy()
        $webClient.Proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
        
        $webClient.DownloadFile("$BaseUrl/Master-Installer.ps1", $masterInstaller)
        Write-ColorOutput "Downloaded Master-Installer.ps1" -Type Success
        $downloadSuccess = $true
    }
    catch {
        Write-ColorOutput "Primary download failed: $_" -Type Warn
        
        # Try alternative URL if GitHub Pages failed
        if ($BaseUrl -match "github\.io") {
            Write-ColorOutput "Trying direct GitHub raw URL..." -Type Info
            try {
                $altUrl = "https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/Master-Installer.ps1"
                $webClient = New-Object System.Net.WebClient
                $webClient.Headers.Add("User-Agent", "PowerShell/WebInstaller")
                $webClient.Proxy = [System.Net.WebRequest]::GetSystemWebProxy()
                $webClient.Proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
                $webClient.DownloadFile($altUrl, $masterInstaller)
                Write-ColorOutput "Downloaded from alternative URL" -Type Success
                $downloadSuccess = $true
                
                # Update BaseUrl for subsequent downloads
                $BaseUrl = "https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies"
            }
            catch {
                Write-ColorOutput "Alternative download also failed: $_" -Type Warn
            }
        }
        
        # Final fallback
        if (-not $downloadSuccess) {
            try {
                Write-ColorOutput "Trying Invoke-WebRequest fallback..." -Type Info
                Invoke-WebRequest -Uri "$BaseUrl/Master-Installer.ps1" `
                                 -OutFile $masterInstaller `
                                 -UseBasicParsing `
                                 -MaximumRedirection 5 `
                                 -ErrorAction Stop
                Write-ColorOutput "Downloaded Master-Installer.ps1 (fallback)" -Type Success
                $downloadSuccess = $true
            }
            catch {
                throw "Failed to download master installer. Network error: $_"
            }
        }
    }
    
    # Component installers
    $scripts = @(
        "Install-Miniforge.ps1",
        "Install-Pixi.ps1",
        "Install-Docker-Desktop.ps1",
        "Install-Chrome.ps1"
    )
    
    foreach ($script in $scripts) {
        $scriptPath = Join-Path $TempDir $script
        $componentSuccess = $false
        
        try {
            Write-ColorOutput "Downloading $script..." -Type Info
            # Use WebClient with full configuration
            $webClient = New-Object System.Net.WebClient
            $webClient.Headers.Add("User-Agent", "PowerShell/WebInstaller")
            $webClient.Proxy = [System.Net.WebRequest]::GetSystemWebProxy()
            $webClient.Proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
            
            # First try with current BaseUrl
            try {
                $webClient.DownloadFile("$BaseUrl/$script", $scriptPath)
                $componentSuccess = $true
            }
            catch {
                # If BaseUrl was GitHub Pages and failed, try raw GitHub
                if ($BaseUrl -match "github\.io" -or -not $componentSuccess) {
                    $altUrl = "https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/$script"
                    Write-ColorOutput "Trying alternative URL for $script..." -Type Info
                    $webClient.DownloadFile($altUrl, $scriptPath)
                    $componentSuccess = $true
                }
            }
        }
        catch {
            # Final fallback with Invoke-WebRequest
            if (-not $componentSuccess) {
                try {
                    Write-ColorOutput "Using fallback for $script..." -Type Info
                    $fallbackUrl = if ($BaseUrl -match "github\.io") {
                        "https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/$script"
                    } else {
                        "$BaseUrl/$script"
                    }
                    
                    Invoke-WebRequest -Uri $fallbackUrl `
                                     -OutFile $scriptPath `
                                     -UseBasicParsing `
                                     -MaximumRedirection 5 `
                                     -ErrorAction Stop
                    $componentSuccess = $true
                }
                catch {
                    Write-ColorOutput "Failed to download $script (component may be skipped): $_" -Type Warn
                }
            }
        }
    }
    
    $downloadedCount = (Get-ChildItem -Path $TempDir -Filter "*.ps1").Count
    Write-ColorOutput "Downloaded $downloadedCount installer scripts" -Type Info
}

function Build-Arguments {
    $installArgs = @()
    
    # Pass through all parameters to Master-Installer
    # Always pass the Role parameter
    $installArgs += '-Role', $Role
    
    if ($Yes) { $installArgs += '-Yes' }
    if ($DryRun) { $installArgs += '-DryRun' }
    if ($SkipMiniforge) { $installArgs += '-SkipMiniforge' }
    if ($SkipPixi) { $installArgs += '-SkipPixi' }
    if ($SkipDocker) { $installArgs += '-SkipDocker' }
    if ($SkipChrome) { $installArgs += '-SkipChrome' }
    if ($SkipFranklin) { $installArgs += '-SkipFranklin' }
    if ($Force) { $installArgs += '-Force' }
    
    return $installArgs
}

function Invoke-Installation {
    param(
        [string]$TempDir,
        [array]$Arguments
    )
    
    $masterInstaller = Join-Path $TempDir "Master-Installer.ps1"
    
    if ($DryRun) {
        Write-ColorOutput "Dry run - would execute:" -Type Info
        Write-Host "  Set-Location '$TempDir'"
        Write-Host "  & '$masterInstaller' $($Arguments -join ' ')"
        return
    }
    
    Write-ColorOutput "Starting installation..." -Type Step
    
    # Change to temp directory
    Push-Location $TempDir
    try {
        # Run the master installer with arguments
        if ($Arguments.Count -gt 0) {
            & $masterInstaller @Arguments
        }
        else {
            & $masterInstaller
        }
        
        # Write-Host ""
        # Write-ColorOutput "Installation completed successfully!" -Type Success
        # Write-Host ""
        # Write-Host "Next steps:" -ForegroundColor Cyan
        # Write-Host "  1. Restart your terminal"
        # Write-Host "  2. Verify installation: franklin --version"
        # Write-Host "  3. Get started: franklin --help"
    }
    catch {
        Write-ColorOutput "Installation failed: $_" -Type Error
        throw
    }
    finally {
        Pop-Location
    }
}

# Main execution
function Main {
    try {
        # Show help if requested
        if ($Help) {
            Show-Help
            return
        }
        
        Show-Banner
        
        Write-ColorOutput "Starting Franklin web installer for Windows" -Type Info
        Write-ColorOutput "User role: $Role" -Type Info
        
        # Check requirements
        Test-Requirements
        
        # Show what will be installed
        if (-not $DryRun) {
            Write-Host ""
            Write-Host "This script will install:" -ForegroundColor Cyan
            if (-not $SkipMiniforge) { Write-Host "  - Miniforge (Python environment manager)" }
            if (-not $SkipPixi) { Write-Host "  - Pixi (Fast package manager)" }
            if (-not $SkipDocker) { Write-Host "  - Docker Desktop (Container platform)" }
            if (-not $SkipChrome) { Write-Host "  - Google Chrome (Web browser)" }
            if (-not $SkipFranklin) { Write-Host "  - Franklin $Role (Development environment)" }
            Write-Host ""
            Write-Host "Installation directory: $InstallDir"
            Write-Host ""
            
            # Confirm installation (if interactive and not using -Yes)
            if (-not $Yes -and -not $env:CI -and -not $env:FRANKLIN_NONINTERACTIVE) {
                $response = Read-Host "Continue with installation? (Y/n)"
                if ($response -and $response -ne 'Y' -and $response -ne 'y') {
                    Write-ColorOutput "Installation cancelled" -Type Info
                    return
                }
            }
            elseif ($Yes) {
                Write-ColorOutput "Auto-accepting installation (Yes flag specified)" -Type Info
            }
            else {
                Write-ColorOutput "Running in non-interactive mode" -Type Info
            }
        }
        
        # Determine base URL with fallback
        $baseUrl = $null
        try {
            $baseUrl = Get-BaseUrl
        }
        catch {
            Write-ColorOutput "Could not determine optimal URL, using direct GitHub" -Type Warn
            $baseUrl = "https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies"
        }
        
        Write-ColorOutput "Using base URL: $baseUrl" -Type Info
        
        # Create temp directory
        $tempDir = Get-TempDirectory
        Write-ColorOutput "Using temporary directory: $tempDir" -Type Info
        
        try {
            # Download installers
            Download-Installers -TempDir $tempDir -BaseUrl $baseUrl
            
            # Build arguments
            $installArgs = Build-Arguments
            
            # Run installation
            Invoke-Installation -TempDir $tempDir -Arguments $installArgs
        }
        finally {
            # Cleanup
            if (Test-Path $tempDir) {
                Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }
    catch {
        Write-ColorOutput $_.Exception.Message -Type Error
        
        # Provide specific help for common errors
        if ($_.Exception.Message -match "host|DNS|resolve") {
            Write-Host ""
            Write-Host "DNS Resolution Error Detected!" -ForegroundColor Red
            Write-Host "This usually means:" -ForegroundColor Yellow
            Write-Host "  1. No internet connection" -ForegroundColor White
            Write-Host "  2. DNS server issues" -ForegroundColor White
            Write-Host "  3. Firewall/proxy blocking GitHub access" -ForegroundColor White
            Write-Host ""
            Write-Host "Try these solutions:" -ForegroundColor Cyan
            Write-Host "  - Check your internet connection" -ForegroundColor White
            Write-Host "  - Try using Google DNS (8.8.8.8) or Cloudflare DNS (1.1.1.1)" -ForegroundColor White
            Write-Host "  - Disable VPN if connected" -ForegroundColor White
            Write-Host "  - Check corporate firewall settings" -ForegroundColor White
        }
        elseif ($_.Exception.Message -match "connect|network|timeout") {
            Write-Host ""
            Write-Host "Network Connection Error!" -ForegroundColor Red
            Write-Host "Cannot reach GitHub servers." -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host "For help, use this command:" -ForegroundColor Yellow
        Write-Host "  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12" -ForegroundColor White
        Write-Host "  (New-Object Net.WebClient).DownloadString('https://raw.githubusercontent.com/munch-group/franklin/main/src/franklin/dependencies/web-install.ps1') | iex" -ForegroundColor White
        exit 1
    }
}

# Run main function
Main