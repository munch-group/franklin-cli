#Requires -Version 5.1

<#
.SYNOPSIS
    Miniforge Python Installer for Windows
    
.DESCRIPTION
    Cross-platform PowerShell installer for miniforge conda distribution.
    Supports Windows with automatic download, installation, and configuration.
    
.PARAMETER InstallDir
    Installation directory for miniforge (default: $env:USERPROFILE\miniforge3)
    
.PARAMETER Version
    Miniforge version to install (default: latest)
    
.PARAMETER NoCondaForgeOnly
    Don't restrict to conda-forge channel only
    
.PARAMETER NoAutoActivate
    Disable auto-activation of base environment
    
.PARAMETER NoProfileUpdate
    Don't update PowerShell profile
    
.PARAMETER Force
    Force reinstallation if miniforge already exists
    
.EXAMPLE
    .\Install-Miniforge.ps1
    
.EXAMPLE
    .\Install-Miniforge.ps1 -InstallDir "C:\miniforge3" -Force
    
.EXAMPLE
    .\Install-Miniforge.ps1 -NoAutoActivate -NoCondaForgeOnly
#>

[CmdletBinding()]
param(
    [string]$InstallDir = "$env:USERPROFILE\miniforge3",
    [string]$Version = "latest",
    [switch]$NoCondaForgeOnly,
    [switch]$NoAutoActivate,
    [switch]$NoProfileUpdate,
    [switch]$Force
)

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Script variables
$CondaForgeOnly = -not $NoCondaForgeOnly
$AutoActivate = -not $NoAutoActivate
$UpdateProfile = -not $NoProfileUpdate

# Logging functions
function Write-Info {
    param([string]$Message)
    Write-Host "$Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "$Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "$Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "$Message" -ForegroundColor Red
}

function Get-Architecture {
    <#
    .SYNOPSIS
        Detect system architecture
    #>
    $arch = $env:PROCESSOR_ARCHITECTURE
    switch ($arch) {
        "AMD64" { return "x86_64" }
        "ARM64" { return "arm64" }
        default { 
            Write-Error "Unsupported architecture: $arch"
            exit 1
        }
    }
}

function Get-DownloadUrl {
    <#
    .SYNOPSIS
        Get the download URL for miniforge Windows installer
    #>
    param([string]$Architecture)
    
    $baseUrl = "https://github.com/conda-forge/miniforge/releases/latest/download"
    return "$baseUrl/Miniforge3-Windows-$Architecture.exe"
}

function Test-ExistingInstallation {
    <#
    .SYNOPSIS
        Check if miniforge is already installed
    #>
    if (Test-Path $InstallDir) {
        Write-Warning "Miniforge installation found at $InstallDir"
        
        if ($Force) {
            Write-Info "Force flag specified. Removing existing installation..."
            Remove-Item -Path $InstallDir -Recurse -Force
            return $false
        }
        
        $choice = Read-Host "Do you want to remove the existing installation and reinstall? (y/N)"
        if ($choice -match '^[Yy]$') {
            Write-Info "Removing existing installation..."
            Remove-Item -Path $InstallDir -Recurse -Force
            return $false
        } else {
            Write-Info "Keeping existing installation. Exiting."
            return $true
        }
    }
    return $false
}

function Install-Miniforge {
    <#
    .SYNOPSIS
        Download and install miniforge
    #>
    $architecture = Get-Architecture
    $downloadUrl = Get-DownloadUrl -Architecture $architecture
    $installerPath = Join-Path $env:TEMP "miniforge_installer.exe"
    
    Write-Info "Detected architecture: $architecture"
    Write-Info "Download URL: $downloadUrl"
    
    try {
        # Download installer
        Write-Info "Downloading miniforge installer..."
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($downloadUrl, $installerPath)
        
        # Verify download
        if (-not (Test-Path $installerPath)) {
            throw "Failed to download installer"
        }
        
        $fileSize = (Get-Item $installerPath).Length
        Write-Info "Downloaded installer ($([math]::Round($fileSize / 1MB, 2)) MB)"
        
        # Run installer
        Write-Info "Installing miniforge to $InstallDir..."
        $installArgs = @(
            "/S",                    # Silent installation
            "/InstallationType=JustMe",  # Install for current user only
            "/RegisterPython=0",     # Don't register as default Python
            "/AddToPath=0",         # Don't add to PATH (we'll handle this)
            "/D=$InstallDir"        # Installation directory
        )
        
        $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
        
        if ($process.ExitCode -ne 0) {
            throw "Installation failed with exit code: $($process.ExitCode)"
        }
        
        Write-Success "Miniforge installed successfully!"
        
    } catch {
        Write-Error "Installation failed: $($_.Exception.Message)"
        exit 1
    } finally {
        # Clean up installer
        if (Test-Path $installerPath) {
            Remove-Item -Path $installerPath -Force
        }
    }
}

function Initialize-Conda {
    <#
    .SYNOPSIS
        Configure conda settings
    #>
    $condaExe = Join-Path $InstallDir "Scripts\conda.exe"
    
    if (-not (Test-Path $condaExe)) {
        Write-Error "Conda executable not found at $condaExe"
        exit 1
    }
    
    Write-Info "Configuring conda..."
    
    try {
        # Initialize conda for PowerShell
        Write-Info "Initializing conda for PowerShell..."
        & $condaExe "init" "powershell" 2>$null
        
        # Set conda-forge as default and only channel if requested
        if ($CondaForgeOnly) {
            Write-Info "Setting conda-forge as the only channel..."
            & $condaExe "config" "--set" "channels" "conda-forge"
            & $condaExe "config" "--set" "channel_priority" "strict"
        }
        
        # Configure auto activation of base environment
        if (-not $AutoActivate) {
            Write-Info "Disabling auto-activation of base environment..."
            & $condaExe "config" "--set" "auto_activate_base" "false"
        }
        
        # Update conda to latest version
        Write-Info "Updating conda to latest version..."
        & $condaExe "update" "-n" "base" "-c" "conda-forge" "conda" "-y"
        
        Write-Success "Conda configuration completed!"
        
    } catch {
        Write-Error "Conda configuration failed: $($_.Exception.Message)"
        exit 1
    }
}

function Update-PowerShellProfile {
    <#
    .SYNOPSIS
        Update PowerShell profile with conda initialization
    #>
    if (-not $UpdateProfile) {
        return
    }
    
    # Determine profile path
    $profilePath = $PROFILE.CurrentUserCurrentHost
    $profileDir = Split-Path $profilePath -Parent
    
    # Create profile directory if it doesn't exist
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    
    # Create profile file if it doesn't exist
    if (-not (Test-Path $profilePath)) {
        New-Item -ItemType File -Path $profilePath -Force | Out-Null
    }
    
    Write-Info "Updating PowerShell profile: $profilePath"
    
    # Read existing profile content
    $profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    if (-not $profileContent) {
        $profileContent = ""
    }
    
    # Check if conda initialization already exists
    if ($profileContent -notmatch "conda initialize") {
        $condaInit = @"

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
`$Env:CONDA_EXE = "$InstallDir\Scripts\conda.exe"
`$Env:_CE_M = ""
`$Env:_CE_CONDA = ""
`$Env:_CONDA_ROOT = "$InstallDir"
`$Env:_CONDA_EXE = "$InstallDir\Scripts\conda.exe"
`$CondaModuleArgs = @{ChangePs1 = `$True}
Import-Module "$InstallDir\shell\condabin\Conda.psm1" -ArgumentList `$CondaModuleArgs
Remove-Variable CondaModuleArgs
# <<< conda initialize <<<
"@
        
        Add-Content -Path $profilePath -Value $condaInit
        Write-Success "Added conda initialization to PowerShell profile"
    } else {
        Write-Info "Conda initialization already exists in PowerShell profile"
    }
}

function Update-Environment {
    <#
    .SYNOPSIS
        Update environment variables for current session
    #>
    Write-Info "Updating environment for current session..."
    
    # Add conda to PATH for current session
    $condaScripts = Join-Path $InstallDir "Scripts"
    $condaCondabin = Join-Path $InstallDir "condabin"
    
    if ($env:PATH -notlike "*$condaScripts*") {
        $env:PATH = "$condaScripts;$condaCondabin;$env:PATH"
    }
    
    # Set conda environment variables
    $env:CONDA_EXE = Join-Path $InstallDir "Scripts\conda.exe"
    $env:_CONDA_ROOT = $InstallDir
    $env:_CONDA_EXE = Join-Path $InstallDir "Scripts\conda.exe"
}

function Test-Installation {
    <#
    .SYNOPSIS
        Verify the installation
    #>
    $condaExe = Join-Path $InstallDir "Scripts\conda.exe"
    
    if (Test-Path $condaExe) {
        Write-Info "Verifying installation..."
        
        try {
            $version = & $condaExe "--version" 2>$null
            Write-Success "Installation verified! $version"
            
            Write-Info "Available environments:"
            & $condaExe "env" "list"
            
            Write-Info "Conda configuration:"
            & $condaExe "config" "--show" "channels"
            
            return $true
        } catch {
            Write-Error "Installation verification failed: $($_.Exception.Message)"
            return $false
        }
    } else {
        Write-Error "Installation verification failed! Conda executable not found."
        return $false
    }
}

function Show-CompletionMessage {
    <#
    .SYNOPSIS
        Display completion message with usage instructions
    #>
    Write-Host ""
    Write-Success "Miniforge installation completed successfully!"
    Write-Host ""
    Write-Info "To start using conda, either:"
    Write-Info "1. Restart PowerShell, or"
    Write-Info "2. Run: . `$PROFILE (reload your PowerShell profile)"
    Write-Host ""
    Write-Info "Quick start commands:"
    Write-Info "  conda --version                    # Check conda version"
    Write-Info "  conda create -n myenv python=3.11  # Create new environment"
    Write-Info "  conda activate myenv               # Activate environment"
    Write-Info "  conda install numpy pandas         # Install packages"
    Write-Host ""
    
    if ($UpdateProfile) {
        Write-Info "PowerShell profile updated: $($PROFILE.CurrentUserCurrentHost)"
    }
}

# Main installation function
function Main {
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "       Miniforge Python Installer (Windows)"      -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Info "Starting miniforge installation..."
    Write-Info "Installation directory: $InstallDir"
    Write-Info "Version: $Version"
    Write-Info "Conda-forge only: $CondaForgeOnly"
    Write-Info "Auto-activate base: $AutoActivate"
    Write-Info "Update profile: $UpdateProfile"
    Write-Host ""
    
    # Check for existing installation
    if (Test-ExistingInstallation) {
        exit 0
    }
    
    # Install miniforge
    Install-Miniforge
    
    # Configure conda
    Initialize-Conda
    
    # Update PowerShell profile
    Update-PowerShellProfile
    
    # Update environment for current session
    Update-Environment
    
    # Verify installation
    if (Test-Installation) {
        Show-CompletionMessage
    } else {
        Write-Error "Installation failed!"
        exit 1
    }
}

# Check if running as administrator (optional warning)
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Running without administrator privileges. This is usually fine for user-level installation."
}

# Run main function
try {
    Main
} catch {
    Write-Error "Unexpected error: $($_.Exception.Message)"
    Write-Error "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}