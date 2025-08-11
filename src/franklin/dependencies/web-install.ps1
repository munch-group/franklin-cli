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

.PARAMETER DryRun
    Show what would be installed without doing it

.EXAMPLE
    # Default installation (PowerShell) - using TLS 1.2
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://munch-group.org/installers/install.ps1 | iex

.EXAMPLE
    # With parameters (PowerShell)
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; & ([scriptblock]::Create((irm https://munch-group.org/installers/install.ps1))) -Role educator

.EXAMPLE
    # Alternative syntax with WebClient for better compatibility
    (New-Object Net.WebClient).DownloadString('https://munch-group.org/installers/install.ps1') | iex

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
    [switch]$Help
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Force TLS 1.2 for secure connections (required for GitHub)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Configuration
$RepoOrg = if ($env:FRANKLIN_REPO_ORG) { $env:FRANKLIN_REPO_ORG } else { "franklin-project" }
$RepoName = if ($env:FRANKLIN_REPO_NAME) { $env:FRANKLIN_REPO_NAME } else { "franklin" }
$RepoBranch = if ($env:FRANKLIN_REPO_BRANCH) { $env:FRANKLIN_REPO_BRANCH } else { "main" }
$InstallDir = if ($env:FRANKLIN_INSTALL_DIR) { $env:FRANKLIN_INSTALL_DIR } else { "$env:USERPROFILE\.franklin-installer" }

# Determine base URL (GitHub Pages or raw GitHub)
function Get-BaseUrl {
    $ghPagesUrl = "https://$RepoOrg.github.io/$RepoName/installers/scripts"
    $rawGithubUrl = "https://raw.githubusercontent.com/$RepoOrg/$RepoName/$RepoBranch/src/franklin/dependencies"
    
    try {
        # Try GitHub Pages URL first with redirect handling
        $response = Invoke-WebRequest -Uri "$ghPagesUrl/Master-Installer.ps1" `
                                     -Method Head `
                                     -UseBasicParsing `
                                     -MaximumRedirection 5 `
                                     -ErrorAction Stop
        return $ghPagesUrl
    }
    catch {
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
        'Success' { Write-Host "✓ $Message" -ForegroundColor Green }
    }
}

function Show-Banner {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║     Franklin Development Environment Installer        ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Help {
    Write-Host @"
Franklin Development Environment - Web Installer for Windows

USAGE:
    # Basic installation (with TLS 1.2 for security)
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://munch-group.org/installers/install.ps1 | iex
    
    # With parameters
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; & ([scriptblock]::Create((irm https://munch-group.org/installers/install.ps1))) -Role educator

PARAMETERS:
    -Role           User role: student, educator, or administrator (default: student)
    -SkipMiniforge  Skip Miniforge installation
    -SkipPixi       Skip Pixi installation
    -SkipDocker     Skip Docker Desktop installation
    -SkipChrome     Skip Chrome installation
    -SkipFranklin   Skip Franklin installation
    -Force          Force reinstall all components
    -DryRun         Show what would be installed without doing it
    -Help           Show this help message

EXAMPLES:
    # Default installation (student) - recommended
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://munch-group.org/installers/install.ps1 | iex

    # Educator installation
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; iex "& { `$(irm https://munch-group.org/installers/install.ps1) } -Role educator"

    # Alternative using WebClient (most compatible)
    (New-Object Net.WebClient).DownloadString('https://munch-group.org/installers/install.ps1') | iex

    # Skip Docker and Chrome
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; iex "& { `$(irm https://munch-group.org/installers/install.ps1) } -SkipDocker -SkipChrome"

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
    
    # Check Windows version
    $os = Get-CimInstance Win32_OperatingSystem
    Write-ColorOutput "Windows version: $($os.Caption) - $($os.Version)" -Type Info
    
    # Check if running as admin (warn only)
    if (-not (Test-Administrator)) {
        Write-ColorOutput "Not running as Administrator. Some components may require elevation." -Type Warn
    }
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
    
    # Core installer
    $masterInstaller = Join-Path $TempDir "Master-Installer.ps1"
    try {
        # Download with redirect handling for PowerShell 5.1 compatibility
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "PowerShell/WebInstaller")
        $webClient.DownloadFile("$BaseUrl/Master-Installer.ps1", $masterInstaller)
        Write-ColorOutput "Downloaded Master-Installer.ps1" -Type Success
    }
    catch {
        # Fallback to Invoke-WebRequest with proper parameters
        try {
            Invoke-WebRequest -Uri "$BaseUrl/Master-Installer.ps1" `
                             -OutFile $masterInstaller `
                             -UseBasicParsing `
                             -MaximumRedirection 5
            Write-ColorOutput "Downloaded Master-Installer.ps1 (fallback)" -Type Success
        }
        catch {
            throw "Failed to download master installer: $_"
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
        try {
            Write-ColorOutput "Downloading $script..." -Type Info
            # Use WebClient for better compatibility
            $webClient = New-Object System.Net.WebClient
            $webClient.Headers.Add("User-Agent", "PowerShell/WebInstaller")
            $webClient.DownloadFile("$BaseUrl/$script", $scriptPath)
        }
        catch {
            # Try fallback with Invoke-WebRequest
            try {
                Invoke-WebRequest -Uri "$BaseUrl/$script" `
                                 -OutFile $scriptPath `
                                 -UseBasicParsing `
                                 -MaximumRedirection 5
            }
            catch {
                Write-ColorOutput "Failed to download $script (component may be skipped)" -Type Warn
            }
        }
    }
    
    $downloadedCount = (Get-ChildItem -Path $TempDir -Filter "*.ps1").Count
    Write-ColorOutput "Downloaded $downloadedCount installer scripts" -Type Info
}

function Build-Arguments {
    $args = @()
    
    if ($Role -and $Role -ne 'student') {
        $args += '--role', $Role
    }
    
    if ($SkipMiniforge) { $args += '--skip-miniforge' }
    if ($SkipPixi) { $args += '--skip-pixi' }
    if ($SkipDocker) { $args += '--skip-docker' }
    if ($SkipChrome) { $args += '--skip-chrome' }
    if ($SkipFranklin) { $args += '--skip-franklin' }
    if ($Force) { $args += '--force' }
    
    return $args
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
        
        Write-Host ""
        Write-ColorOutput "Installation completed successfully!" -Type Success
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Restart your terminal"
        Write-Host "  2. Verify installation: franklin --version"
        Write-Host "  3. Get started: franklin --help"
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
            if (-not $SkipMiniforge) { Write-Host "  • Miniforge (Python environment manager)" }
            if (-not $SkipPixi) { Write-Host "  • Pixi (Fast package manager)" }
            if (-not $SkipDocker) { Write-Host "  • Docker Desktop (Container platform)" }
            if (-not $SkipChrome) { Write-Host "  • Google Chrome (Web browser)" }
            if (-not $SkipFranklin) { Write-Host "  • Franklin $Role (Development environment)" }
            Write-Host ""
            Write-Host "Installation directory: $InstallDir"
            Write-Host ""
            
            # Confirm installation (if interactive)
            if (-not $env:CI -and -not $env:FRANKLIN_NONINTERACTIVE) {
                $response = Read-Host "Continue with installation? (Y/n)"
                if ($response -and $response -ne 'Y' -and $response -ne 'y') {
                    Write-ColorOutput "Installation cancelled" -Type Info
                    return
                }
            }
            else {
                Write-ColorOutput "Running in non-interactive mode" -Type Info
            }
        }
        
        # Determine base URL
        $baseUrl = Get-BaseUrl
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
        Write-Host ""
        Write-Host "For help, run:" -ForegroundColor Yellow
        Write-Host '  & ([scriptblock]::Create((irm https://munch-group.org/installers/install.ps1))) -Help'
        exit 1
    }
}

# Run main function
Main