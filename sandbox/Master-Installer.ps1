#Requires -Version 5.1

<#
.SYNOPSIS
    Master Development Environment Installer
    
.DESCRIPTION
    Orchestrates the installation of a complete development environment by running
    multiple installer scripts in sequence, then configures pixi with franklin.
    
.PARAMETER Role
    User role: must be student, educator, or administrator

.PARAMETER SkipMiniforge
    Skip miniforge installation
    
.PARAMETER SkipPixi
    Skip pixi installation
    
.PARAMETER SkipDocker
    Skip Docker Desktop installation
    
.PARAMETER SkipChrome
    Skip Chrome installation
    
.PARAMETER SkipFranklin
    Skip franklin installation via pixi
    
.PARAMETER Force
    Force installation of all components even if already installed
    
.PARAMETER ContinueOnError
    Continue with remaining installations if one fails

.PARAMETER DryRun
    Only show installation plan

.EXAMPLE
    .\Master-Installer.ps1
    
.EXAMPLE
    .\Master-Installer.ps1 -ScriptPath "C:\Installers" -Force
    
.EXAMPLE
    .\Master-Installer.ps1 -SkipDocker -SkipChrome
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
    [switch]$ContinueOnError,
    [switch]$DryRun,
    [switch]$Yes
)

# # Set default for ScriptPath if not provided
# if (-not $ScriptPath) {
#     if ($PSScriptRoot) {
#         $ScriptPath = $PSScriptRoot
#     } else {
#         $ScriptPath = (Get-Location).Path
#     }
# }
$ScriptPath = (Get-Location).Path

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Script execution tracking
$Script:ExecutionLog = @()
$Script:FailedInstallations = @()
$Script:SuccessfulInstallations = @()

# Installer script names
$InstallerScripts = @{
    Miniforge = "Install-Miniforge.ps1"
    Pixi = "Install-Pixi.ps1"
    Docker = "Install-Docker-Desktop.ps1"
    Chrome = "Install-Chrome.ps1"
}

# Logging functions
function Write-Info {
    param([string]$Message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [INFO] $Message" -ForegroundColor Blue
    $Script:ExecutionLog += "[$timestamp] [INFO] $Message"
}

function Write-Success {
    param([string]$Message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [SUCCESS] $Message" -ForegroundColor Green
    $Script:ExecutionLog += "[$timestamp] [SUCCESS] $Message"
}

function Write-Warning {
    param([string]$Message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [WARNING] $Message" -ForegroundColor Yellow
    $Script:ExecutionLog += "[$timestamp] [WARNING] $Message"
}

function Write-Error {
    param([string]$Message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [ERROR] $Message" -ForegroundColor Red
    $Script:ExecutionLog += "[$timestamp] [ERROR] $Message"
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-StepHeader {
    param([string]$Step, [string]$Description)
    Write-Host ""
    Write-Host ">>> STEP ${Step}: $Description" -ForegroundColor Magenta
    Write-Host ("-" * 50) -ForegroundColor Gray
}

function Test-ScriptExists {
    <#
    .SYNOPSIS
        Check if an installer script exists
    #>
    param([string]$ScriptName)
    
    $scriptFullPath = Join-Path $ScriptPath $ScriptName
    if (Test-Path $scriptFullPath) {
        return $scriptFullPath
    }
    
    Write-Warning "Script not found: $scriptFullPath"
    return $null
}

function Test-CommandExists {
    <#
    .SYNOPSIS
        Check if a command exists in the system
    #>
    param([string]$Command)
    
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Invoke-InstallerScript {
    <#
    .SYNOPSIS
        Execute an installer script with error handling
    #>
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string[]]$Arguments = @()
    )
    
    Write-Info "Starting $Name installation..."
    
    try {
        # Build argument list
        $argList = @()
        if ($Force) {
            $argList += "-Force"
        }
        $argList += $Arguments
        
        # Execute the script
        $allArgs = @("-ExecutionPolicy", "Bypass", "-File", $ScriptPath) + $argList
        $process = Start-Process -FilePath "powershell.exe" -ArgumentList $allArgs -Wait -PassThru -NoNewWindow
        
        if ($process.ExitCode -eq 0) {
            Write-Success "$Name installation completed successfully"
            $Script:SuccessfulInstallations += $Name
            return $true
        } else {
            Write-Error "$Name installation failed with exit code: $($process.ExitCode)"
            $Script:FailedInstallations += $Name
            return $false
        }
        
    } catch {
        Write-Error "$Name installation failed: $($_.Exception.Message)"
        $Script:FailedInstallations += $Name
        return $false
    }
}

function Install-Miniforge {
    <#
    .SYNOPSIS
        Install miniforge conda distribution
    #>
    Write-StepHeader "1" "Installing Miniforge Python Distribution"
    
    if ($SkipMiniforge) {
        Write-Info "Skipping miniforge installation (SkipMiniforge flag)"
        return $true
    }
    
    # Check if already installed
    if ((Test-CommandExists "conda") -and (-not $Force)) {
        Write-Info "Miniforge/Conda already installed. Use -Force to reinstall."
        $Script:SuccessfulInstallations += "Miniforge"
        return $true
    }
    
    $scriptPath = Test-ScriptExists $InstallerScripts.Miniforge
    if (-not $scriptPath) {
        if ($ContinueOnError) {
            Write-Warning "Miniforge installer script not found. Continuing..."
            $Script:FailedInstallations += "Miniforge"
            return $false
        } else {
            throw "Miniforge installer script not found: $($InstallerScripts.Miniforge)"
        }
    }
    
    return Invoke-InstallerScript -Name "Miniforge" -ScriptPath $scriptPath
}

function Install-Pixi {
    <#
    .SYNOPSIS
        Install pixi package manager
    #>
    Write-StepHeader "2" "Installing Pixi Package Manager"
    
    if ($SkipPixi) {
        Write-Info "Skipping pixi installation (SkipPixi flag)"
        return $true
    }
    
    # Check if already installed
    if ((Test-CommandExists "pixi") -and (-not $Force)) {
        Write-Info "Pixi already installed. Use -Force to reinstall."
        $Script:SuccessfulInstallations += "Pixi"
        return $true
    }
    
    $scriptPath = Test-ScriptExists $InstallerScripts.Pixi
    if (-not $scriptPath) {
        if ($ContinueOnError) {
            Write-Warning "Pixi installer script not found. Continuing..."
            $Script:FailedInstallations += "Pixi"
            return $false
        } else {
            throw "Pixi installer script not found: $($InstallerScripts.Pixi)"
        }
    }
    
    return Invoke-InstallerScript -Name "Pixi" -ScriptPath $scriptPath -Arguments @("-Command", "Install")
}

function Install-DockerDesktop {
    <#
    .SYNOPSIS
        Install Docker Desktop
    #>
    Write-StepHeader "3" "Installing Docker Desktop"
    
    if ($SkipDocker) {
        Write-Info "Skipping Docker Desktop installation (SkipDocker flag)"
        return $true
    }
    
    # Check if already installed
    if ((Test-CommandExists "docker") -and (-not $Force)) {
        Write-Info "Docker already installed. Use -Force to reinstall."
        $Script:SuccessfulInstallations += "Docker Desktop"
        return $true
    }
    
    $scriptPath = Test-ScriptExists $InstallerScripts.Docker
    if (-not $scriptPath) {
        if ($ContinueOnError) {
            Write-Warning "Docker Desktop installer script not found. Continuing..."
            $Script:FailedInstallations += "Docker Desktop"
            return $false
        } else {
            throw "Docker Desktop installer script not found: $($InstallerScripts.Docker)"
        }
    }
    
    # Docker requires administrator privileges - provide clear prompt
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Host ""
        Write-Host "Docker Desktop requires Administrator privileges" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Type your user password and press enter:" -ForegroundColor Green
        Write-Host "An Administrator prompt will appear when the Docker installer starts..." -ForegroundColor Cyan
        Write-Host ""
    }
    
    return Invoke-InstallerScript -Name "Docker Desktop" -ScriptPath $scriptPath
}

function Install-Chrome {
    <#
    .SYNOPSIS
        Install Google Chrome
    #>
    Write-StepHeader "4" "Installing Google Chrome"
    
    if ($SkipChrome) {
        Write-Info "Skipping Chrome installation (SkipChrome flag)"
        return $true
    }
    
    # Check if already installed (Chrome might be in different locations)
    $chromeLocations = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
    )
    
    $chromeInstalled = $chromeLocations | Where-Object { Test-Path $_ } | Select-Object -First 1
    
    if ($chromeInstalled -and (-not $Force)) {
        Write-Info "Chrome already installed at: $chromeInstalled. Use -Force to reinstall."
        $Script:SuccessfulInstallations += "Chrome"
        return $true
    }
    
    $scriptPath = Test-ScriptExists $InstallerScripts.Chrome
    if (-not $scriptPath) {
        if ($ContinueOnError) {
            Write-Warning "Chrome installer script not found. Continuing..."
            $Script:FailedInstallations += "Chrome"
            return $false
        } else {
            throw "Chrome installer script not found: $($InstallerScripts.Chrome)"
        }
    }
    
    return Invoke-InstallerScript -Name "Chrome" -ScriptPath $scriptPath
}

function Install-Franklin {
    <#
    .SYNOPSIS
        Install Franklin via pixi global
    #>
    Write-StepHeader "5" "Installing Franklin via Pixi Global"
    
    if ($SkipFranklin) {
        Write-Info "Skipping Franklin installation (SkipFranklin flag)"
        return $true
    }
    
    # Check if pixi is available
    if (-not (Test-CommandExists "pixi")) {
        Write-Error "Pixi is not available. Cannot install Franklin."
        if ($ContinueOnError) {
            $Script:FailedInstallations += "Franklin"
            return $false
        } else {
            throw "Pixi is required to install Franklin"
        }
    }
    
    # Write-Info "Installing Franklin using pixi global..."
    
    try {
        # Refresh environment to ensure pixi is in PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
        
        # Run pixi global install command
        # Install the appropriate franklin package based on role
        $franklinPackage = switch ($Role) {
            'administrator' { 'franklin-admin' }
            'educator' { 'franklin-educator' }
            default { 'franklin' }
        }
        
        $pixiArgs = @(
            "global", "install",
            "-c", "munch-group",
            "-c", "conda-forge",
            "python",
            $franklinPackage
        )
        
        # Write-Info "Executing: pixi $($pixiArgs -join ' ')"
        
        $process = Start-Process -FilePath "pixi" -ArgumentList $pixiArgs -Wait -PassThru -NoNewWindow
        
        if ($process.ExitCode -eq 0) {
            Write-Success "$franklinPackage installed successfully via pixi global"
            $Script:SuccessfulInstallations += "Franklin"
            return $true
        } else {
            Write-Error "$franklinPackage installation failed with exit code: $($process.ExitCode)"
            $Script:FailedInstallations += "Franklin"
            return $false
        }
        
    } catch {
        Write-Error "$franklinPackage installation failed: $($_.Exception.Message)"
        $Script:FailedInstallations += "Franklin"
        return $false
    }
}

function Test-Prerequisites {
    <#
    .SYNOPSIS
        Check prerequisites and system requirements
    #>
    Write-Info "Checking prerequisites..."
    
    # Check PowerShell version
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -lt 5) {
        throw "PowerShell 5.1 or higher is required. Current version: $psVersion"
    }
    Write-Info "PowerShell version: $psVersion [OK]"
    
    # Check if running as administrator (recommended but not required)
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if ($isAdmin) {
        Write-Info "Running as Administrator [OK]"
    } else {
        Write-Warning "Not running as Administrator. Some installations may require elevation."
    }
    
    # Check script directory
    if (-not (Test-Path $ScriptPath)) {
        throw "Script directory not found: $ScriptPath"
    }
    Write-Info "Script directory: $ScriptPath [OK]"
    
    # Check for available installer scripts
    $availableScripts = @()
    $missingScripts = @()
    
    foreach ($script in $InstallerScripts.GetEnumerator()) {
        $scriptFullPath = Join-Path $ScriptPath $script.Value
        if (Test-Path $scriptFullPath) {
            $availableScripts += $script.Key
        } else {
            $missingScripts += $script.Key
        }
    }
    
    Write-Info "Available installer scripts: $($availableScripts -join ', ')"
    if ($missingScripts.Count -gt 0) {
        Write-Warning "Missing installer scripts: $($missingScripts -join ', ')"
    }
}

function Show-InstallationPlan {
    <#
    .SYNOPSIS
        Display the installation plan to the user
    #>
    Write-Header "INSTALLATION PLAN"
    
    $steps = @()
    if (-not $SkipMiniforge) { $steps += "1. Miniforge Python Distribution" }
    if (-not $SkipPixi) { $steps += "2. Pixi Package Manager" }
    if (-not $SkipDocker) { $steps += "3. Docker Desktop" }
    if (-not $SkipChrome) { $steps += "4. Google Chrome" }
    if (-not $SkipFranklin) { $steps += "5. Franklin (via pixi global)" }
    
    foreach ($step in $steps) {
        Write-Host "  $step" -ForegroundColor White
    }
    
    # Write-Host ""
    # Write-Info "Script directory: $ScriptPath"
    # Write-Info "Force reinstall: $Force"
    # Write-Info "Continue on error: $ContinueOnError"

    if ($DryRun) {
        exit 0
    }

    # if (-not $Force -and -not $Yes) {
    if (-not $Yes) {
        Write-Host ""
        $confirm = Read-Host "Do you want to proceed with the installation? (y/N)"
        if ($confirm -notmatch '^[Yy]$') {
            Write-Info "Installation cancelled by user."
            exit 0
        }
    }
}

function Show-InstallationSummary {
    <#
    .SYNOPSIS
        Display installation summary and results
    #>
    Write-Header "INSTALLATION SUMMARY"
    
    if ($Script:SuccessfulInstallations -and $Script:SuccessfulInstallations.Count -gt 0) {
        Write-Success "Installation status:"
        foreach ($item in $Script:SuccessfulInstallations) {
            Write-Host "  [OK] $item" -ForegroundColor Green
        }
    }
    
    if ($Script:FailedInstallations -and $Script:FailedInstallations.Count -gt 0) {
        Write-Warning "Failed installations:"
        foreach ($item in $Script:FailedInstallations) {
            Write-Host "  [FAILED] $item" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    if (-not $Script:FailedInstallations -or $Script:FailedInstallations.Count -eq 0) {
        Write-Success "All installations completed successfully!"
        Write-Info "Your development environment is ready to use."
    } else {
        Write-Warning "Some installations failed. Check the error messages above."
        Write-Info "You may need to install the failed components manually."
    }

    # # Show next steps
    # Write-Host ""
    # Write-Info "NEXT STEPS:"
    # Write-Info "1. Restart your PowerShell session to refresh environment variables"
    # Write-Info "2. Verify installations:"
    # Write-Info "   - conda --version"
    # Write-Info "   - pixi --version"
    # Write-Info "   - docker --version"
    # Write-Info "   - franklin --version (if installed)"
    # Write-Info "3. Check that Franklin is available via 'franklin' command"
}

function Save-InstallationLog {
    <#
    .SYNOPSIS
        Save the installation log to a file
    #>
    $logFile = Join-Path $env:TEMP "master-installer-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
    
    try {
        $Script:ExecutionLog | Out-File -FilePath $logFile -Encoding UTF8
        Write-Info "Installation log saved to: $logFile"
    } catch {
        Write-Warning "Could not save installation log: $($_.Exception.Message)"
    }
}

# Main installation orchestrator
function Start-MasterInstallation {
    <#
    .SYNOPSIS
        Main function that orchestrates the entire installation process
    #>
    $startTime = Get-Date
    
    try {
        # Show header
        Write-Header "MASTER DEVELOPMENT ENVIRONMENT INSTALLER"
        Write-Info "Starting installation process at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        
        # Check prerequisites
        Test-Prerequisites
        
        # Show installation plan
        Show-InstallationPlan
        
        # Execute installations in sequence
        $installationResults = @()
        
        $installationResults += Install-Miniforge
        $installationResults += Install-Pixi
        $installationResults += Install-DockerDesktop
        $installationResults += Install-Chrome
        $installationResults += Install-Franklin
        
        # Show summary
        Show-InstallationSummary
        
        # Save log
        Save-InstallationLog
        
        $endTime = Get-Date
        $duration = $endTime - $startTime
        Write-Info "Total installation time: $($duration.ToString('hh\:mm\:ss'))"
        
        # Determine exit code
        if (-not $Script:FailedInstallations -or $Script:FailedInstallations.Count -eq 0) {
            Write-Success "Master installation completed successfully!"
            Write-Host ""
            Write-Success "YOU MUST NOW RESTART YOUR COMPUTER TO ACTIVATE INSTALLED COMPONENTS"
            Write-Host ""
            exit 0
        } elseif ($ContinueOnError) {
            Write-Warning "Master installation completed with some failures."
            exit 2
        } else {
            Write-Error "Master installation failed."
            exit 1
        }
        
    } catch {
        Write-Error "Master installation failed with error: $($_.Exception.Message)"
        Save-InstallationLog
        exit 1
    }
}

# Script entry point
Write-Host "Master Development Environment Installer" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Validate script path parameter
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script path does not exist: $ScriptPath"
    exit 1
}

# Start the installation process
Start-MasterInstallation