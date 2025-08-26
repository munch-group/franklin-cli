#Requires -Version 5.1

<#
.SYNOPSIS
    Pixi Package Manager - Install/Uninstall Script for Windows
    
.DESCRIPTION
    PowerShell script to install or uninstall the pixi package manager on Windows.
    Supports multiple installation methods and automatic PATH configuration.
    
.PARAMETER Command
    The action to perform: Install, Uninstall, or Help
    
.PARAMETER Version
    Specific version of pixi to install (default: latest)
    
.PARAMETER InstallDir
    Installation directory for pixi (default: $env:USERPROFILE\.pixi)
    
.PARAMETER BinDir
    Binary directory for pixi executable (default: $env:USERPROFILE\.local\bin)
    
.PARAMETER Method
    Installation method: Auto, Curl, Cargo, Binary (default: Auto)
    
.PARAMETER Force
    Force installation even if pixi is already installed
    
.EXAMPLE
    .\Install-Pixi.ps1
    
.EXAMPLE
    .\Install-Pixi.ps1 -Command Install -Version "0.7.0" -Force
    
.EXAMPLE
    .\Install-Pixi.ps1 -Command Uninstall
    
.EXAMPLE
    .\Install-Pixi.ps1 -Method Cargo
#>

[CmdletBinding()]
param(
    [ValidateSet("Install", "Uninstall", "Help")]
    [string]$Command = "Install",
    
    [string]$Version = "latest",
    
    [string]$InstallDir = "$env:USERPROFILE\.pixi",
    
    [string]$BinDir = "$env:USERPROFILE\.local\bin",
    
    [ValidateSet("Auto", "Curl", "Cargo", "Binary")]
    [string]$Method = "Auto",
    
    [switch]$Force,
    
    [switch]$Quiet
)

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Logging functions
function Write-Info {
    param([string]$Message)
    if ($VerbosePreference -eq 'Continue') {
        Write-Host "$Message" -ForegroundColor Blue
    } elseif (-not $Quiet) {
        Write-Host "$Message"
    }
}

function Write-Success {
    param([string]$Message)
    if (-not $Quiet) {
        Write-Host "$Message" -ForegroundColor Green
    }
}

function Write-Warning {
    param([string]$Message)
    if (-not $Quiet) {
        if ($VerbosePreference -eq 'Continue') {
            Write-Host "$Message" -ForegroundColor Yellow
        } else {
            Write-Host "Warning: $Message" -ForegroundColor Yellow
        }
    }
}

function Write-Error {
    param([string]$Message)
    # Show errors unless in quiet mode
    if (-not $Quiet) {
        Write-Host "$Message" -ForegroundColor Red
    }
}

function Write-Header {
    param([string]$Message)
    if (-not $Quiet) {
        if ($VerbosePreference -eq 'Continue') {
            Write-Host $Message -ForegroundColor Cyan
        } else {
            Write-Host $Message
        }
    }
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

function Get-Architecture {
    <#
    .SYNOPSIS
        Detect system architecture
    #>
    $arch = $env:PROCESSOR_ARCHITECTURE
    switch ($arch) {
        "AMD64" { return "x86_64" }
        "ARM64" { return "aarch64" }
        default { 
            Write-Error "Unsupported architecture: $arch"
            exit 1
        }
    }
}

# function Get-LatestPixiVersion {
#     <#
#     .SYNOPSIS
#         Get the latest pixi version from GitHub releases
#     #>
#     try {
#         $response = Invoke-RestMethod -Uri "https://api.github.com/repos/prefix-dev/pixi/releases/latest" -UseBasicParsing
#         return $response.tag_name -replace '^v', ''
#     } catch {
#         Write-Error "Could not determine latest version: $($_.Exception.Message)"
#         exit 1
#     }
# }

function Test-ExistingPixi {
    <#
    .SYNOPSIS
        Check if pixi is already installed
    #>
    if (Test-CommandExists "pixi") {
        try {
            $currentVersion = (pixi --version).Split()[1]
            Write-Warning "Pixi is already installed (version: $currentVersion)"
            
            if ($Force) {
                Write-Info "Force flag specified. Proceeding with reinstallation..."
                # Remove existing .pixi folder
                $pixiPath = "$env:USERPROFILE\.pixi"
                if (Test-Path $pixiPath) {
                    Write-Info "Removing existing .pixi folder..."
                    try {
                        Remove-Item -Path $pixiPath -Recurse -Force -ErrorAction Stop
                    } catch {
                        Write-Warning "Could not remove .pixi folder completely. Some files may be in use."
                    }
                }
                return $true
            }
            
            $choice = Read-Host "Do you want to reinstall pixi? (y/N)"
            if ($choice -match '^[Yy]$') {
                return $true
            } else {
                Write-Info "Installation cancelled."
                exit 0
            }
        } catch {
            Write-Warning "Pixi command found but version check failed"
            return $true
        }
    } elseif ($Force) {
        # Even if pixi command doesn't exist, remove .pixi folder if force flag is set
        $pixiPath = "$env:USERPROFILE\.pixi"
        if (Test-Path $pixiPath) {
            Write-Info "Force flag specified. Removing existing .pixi folder..."
            try {
                Remove-Item -Path $pixiPath -Recurse -Force -ErrorAction Stop
            } catch {
                Write-Warning "Could not remove .pixi folder completely. Some files may be in use."
            }
        }
    }
    return $true
}

# function Install-PixiViaCurl {
#     <#
#     .SYNOPSIS
#         Install pixi via official installer script
#     #>
#     Write-Info "Installing pixi via official installer..."
    
#     if (-not (Test-CommandExists "curl")) {
#         Write-Error "curl is required for this installation method"
#         return $false
#     }
    
#     try {
#         # Download and run official installer
#         $installerScript = Invoke-WebRequest -Uri "https://pixi.sh/install.ps1" -UseBasicParsing
#         Invoke-Expression $installerScript.Content
#         return $true
#     } catch {
#         Write-Error "Official installer failed: $($_.Exception.Message)"
#         return $false
#     }
# }

function Install-PixiViaCurl {
    <#
    .SYNOPSIS
        Install pixi via official installer script with no-modify-path option
    #>
    Write-Info "Installing pixi via official installer..."
    
    try {
        # Download installer script
        $installerScript = Invoke-WebRequest -Uri "https://pixi.sh/install.ps1" -UseBasicParsing
        
        # Convert content to string if it's a byte array
        if ($installerScript.Content -is [byte[]]) {
            $scriptContent = [System.Text.Encoding]::UTF8.GetString($installerScript.Content)
        } else {
            $scriptContent = $installerScript.Content
        }
        
        # Modify the script to add --no-modify-path flag
        # We'll need to invoke it with the flag
        $tempFile = [System.IO.Path]::GetTempFileName() + ".ps1"
        Set-Content -Path $tempFile -Value $scriptContent
        
        # Run with no-modify-path flag
        & $tempFile -NoModifyPath
        
        # Clean up temp file
        Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
        
        return $true
    } catch {
        Write-Error "Official installer failed: $($_.Exception.Message)"
        return $false
    }
}


# function Install-PixiViaCargo {
#     <#
#     .SYNOPSIS
#         Install pixi via Rust cargo
#     #>
#     Write-Info "Installing pixi via cargo..."
    
#     if (-not (Test-CommandExists "cargo")) {
#         Write-Error "Rust/Cargo is required for this installation method"
#         Write-Info "Install Rust from: https://rustup.rs/"
#         return $false
#     }
    
#     try {
#         cargo install pixi
#         return $true
#     } catch {
#         Write-Error "Cargo installation failed: $($_.Exception.Message)"
#         return $false
#     }
# }

# function Install-PixiViaBinary {
#     <#
#     .SYNOPSIS
#         Install pixi via direct binary download
#     #>
#     Write-Info "Installing pixi via direct binary download..."
    
#     $architecture = Get-Architecture
#     $targetVersion = $Version
    
#     if ($targetVersion -eq "latest") {
#         $targetVersion = Get-LatestPixiVersion
#         Write-Info "Latest version: $targetVersion"
#     }
    
#     # Construct download URL
#     $baseUrl = "https://github.com/prefix-dev/pixi/releases/download"
#     $filename = "pixi-$architecture-pc-windows-msvc.zip"
#     $downloadUrl = "$baseUrl/v$targetVersion/$filename"
    
#     Write-Info "Downloading from: $downloadUrl"
    
#     # Create temporary directory
#     $tempDir = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_ }
#     $downloadFile = Join-Path $tempDir $filename
    
#     try {
#         # Download the binary
#         Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadFile -UseBasicParsing
        
#         # Create binary directory if it doesn't exist
#         if (-not (Test-Path $BinDir)) {
#             New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
#         }
        
#         # Extract and install
#         Expand-Archive -Path $downloadFile -DestinationPath $tempDir -Force
        
#         # Find the pixi binary in extracted contents
#         $pixiBinary = Get-ChildItem -Path $tempDir -Name "pixi.exe" -Recurse | Select-Object -First 1
        
#         if ($pixiBinary) {
#             $sourcePath = Join-Path $tempDir $pixiBinary
#             $destPath = Join-Path $BinDir "pixi.exe"
#             Copy-Item -Path $sourcePath -Destination $destPath -Force
#             Write-Success "Binary installed to $destPath"
#             return $true
#         } else {
#             Write-Error "Could not find pixi.exe in downloaded archive"
#             return $false
#         }
        
#     } catch {
#         Write-Error "Binary installation failed: $($_.Exception.Message)"
#         return $false
#     } finally {
#         # Clean up
#         if (Test-Path $tempDir) {
#             Remove-Item -Path $tempDir -Recurse -Force
#         }
#     }
# }


function Update-EnvironmentPath {
    <#
    .SYNOPSIS
        Add pixi binary directory to PATH
    #>
    # Get current user PATH
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    
    # Check if BinDir is already in PATH
    if ($currentPath -split ';' -contains $BinDir) {
        Write-Info "PATH already contains $BinDir"
        return
    }
    
    Write-Info "Adding $BinDir to user PATH..."
    
    # Add to PATH
    $newPath = if ($currentPath) { "$currentPath;$BinDir" } else { $BinDir }
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    
    # Update PATH for current session
    $env:PATH = "$env:PATH;$BinDir"
    
    Write-Success "PATH updated successfully"
}

function Test-PixiPath {
    <#
    .SYNOPSIS
        Check if file contains pixi path
    #>
    param([string]$FilePath)
    
    if (Test-Path $FilePath) {
        $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
        return ($content -match '\.pixi\\bin' -or $content -match '\.pixi/bin')
    }
    return $false
}

function Test-CondaInit {
    <#
    .SYNOPSIS
        Check if file contains conda initialization
    #>
    param([string]$FilePath)
    
    if (Test-Path $FilePath) {
        $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
        return ($content -match '#region conda initialize' -or $content -match '>>> conda initialize >>>')
    }
    return $false
}

function Disable-CondaAutoActivate {
    <#
    .SYNOPSIS
        Disable conda auto_activate_base
    #>
    if (Test-CommandExists "conda") {
        Write-Info "Disabling conda auto_activate_base..."
        try {
            & conda config --set auto_activate_base false 2>$null
            Write-Success "Conda auto_activate_base disabled"
        } catch {
            Write-Warning "Could not disable conda auto_activate_base"
        }
    }
}

function Add-PixiBeforeConda {
    <#
    .SYNOPSIS
        Add pixi path before conda initialization in profile
    #>
    param([string]$ProfilePath)
    
    Write-Info "Processing $ProfilePath..."
    
    # Create profile if it doesn't exist
    if (-not (Test-Path $ProfilePath)) {
        Write-Info "Creating profile file..."
        try {
            New-Item -ItemType File -Path $ProfilePath -Force | Out-Null
        } catch {
            Write-Error "Cannot create $ProfilePath (permission denied)"
            return
        }
    }
    
    # Check if file is read-only
    $fileInfo = Get-Item $ProfilePath -ErrorAction SilentlyContinue
    if ($fileInfo -and $fileInfo.IsReadOnly) {
        Write-Warning "File is read-only, attempting to make it writable..."
        try {
            $fileInfo.IsReadOnly = $false
        } catch {
            Write-Error "Cannot modify $ProfilePath (permission denied). You may need to manually add the following to your profile:"
            Write-Host '# Pixi - Added before conda for priority' -ForegroundColor Cyan
            Write-Host '$env:PATH = "$env:USERPROFILE\.pixi\bin;$env:PATH"' -ForegroundColor Cyan
            return
        }
    }
    
    # Check if pixi path already exists
    if (Test-PixiPath $ProfilePath) {
        Write-Success "Pixi path already exists in $ProfilePath"
        return
    }
    
    # Backup the profile
    $backupPath = "$ProfilePath.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    try {
        Copy-Item -Path $ProfilePath -Destination $backupPath -Force
    } catch {
        Write-Warning "Could not create backup of $ProfilePath"
    }
    
    $pixiPath = '$env:PATH = "$env:USERPROFILE\.pixi\bin;$env:PATH"'
    $pixiComment = '# Pixi - Added before conda for priority'
    
    # Check if conda initialization exists
    if (Test-CondaInit $ProfilePath) {
        Write-Info "Found conda initialization, adding pixi before it..."
        
        try {
            $content = Get-Content $ProfilePath -Raw
            
            # Find conda initialization and add pixi before it
            if ($content -match '(#region conda initialize)') {
                $newContent = $content -replace '(#region conda initialize)', "$pixiComment`n$pixiPath`n`n`$1"
            } elseif ($content -match '(>>> conda initialize >>>)') {
                $newContent = $content -replace '(>>> conda initialize >>>)', "$pixiComment`n$pixiPath`n`n`$1"
            } else {
                # Fallback: add at the beginning
                $newContent = "$pixiComment`n$pixiPath`n`n$content"
            }
            
            Set-Content -Path $ProfilePath -Value $newContent
            Write-Success "Added pixi path before conda initialization"
        } catch {
            Write-Error "Failed to update $ProfilePath : $_"
            return
        }
    } else {
        Write-Info "No conda initialization found, adding pixi path at the beginning..."
        
        try {
            # Add pixi at the beginning of the file
            $content = if (Test-Path $ProfilePath) { Get-Content $ProfilePath -Raw } else { "" }
            $newContent = "$pixiComment`n$pixiPath`n`n$content"
            
            Set-Content -Path $ProfilePath -Value $newContent
            Write-Success "Added pixi path at the beginning of file"
        } catch {
            Write-Error "Failed to update $ProfilePath : $_"
            return
        }
    }
}

function Update-PowerShellProfile {
    <#
    .SYNOPSIS
        Update PowerShell profile to include pixi in PATH with conda priority handling
    #>
    $profilePath = $PROFILE.CurrentUserCurrentHost
    $profileDir = Split-Path $profilePath -Parent
    
    # Create profile directory if it doesn't exist
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    
    # Add pixi before conda
    Add-PixiBeforeConda -ProfilePath $profilePath
    
    # Also update AllUsers profile if it exists and has conda
    $allUsersProfile = $PROFILE.AllUsersCurrentHost
    if ((Test-Path $allUsersProfile) -and (Test-CondaInit $allUsersProfile)) {
        Write-Info "Found conda in AllUsers profile, updating it too..."
        Add-PixiBeforeConda -ProfilePath $allUsersProfile
    }
}

function Install-Pixi {
    <#
    .SYNOPSIS
        Main pixi installation function
    #>
    # Write-Header "Installing Pixi Package Manager"
    
    if (-not (Test-ExistingPixi)) {
        return
    }
    
    $installSuccess = $false
    
    switch ($Method) {
        "Curl" {
            $installSuccess = Install-PixiViaCurl
        }
        # "Cargo" {
        #     $installSuccess = Install-PixiViaCargo
        # }
        # "Binary" {
        #     $installSuccess = Install-PixiViaBinary
        #     if ($installSuccess) {
        #         Update-EnvironmentPath
        #         Update-PowerShellProfile
        #     }
        # }
        "Auto" {

            # Try methods in order of preference
            if (Install-PixiViaCurl) {
                $installSuccess = $true
            } 

            # # Try methods in order of preference
            # if (Install-PixiViaCurl) {
            #     $installSuccess = $true
            # } elseif (Install-PixiViaBinary) {
            #     $installSuccess = $true
            #     Update-EnvironmentPath
            #     Update-PowerShellProfile
            # } elseif (Install-PixiViaCargo) {
            #     $installSuccess = $true
            # } else {
            #     Write-Error "All installation methods failed"
            #     exit 1
            # }
        }
        default {
            Write-Error "Unknown installation method: $Method"
            exit 1
        }
    }
    
    if ($installSuccess) {
        # Update PowerShell profile with pixi path prioritization
        Update-PowerShellProfile
        
        # Update environment PATH
        Update-EnvironmentPath
        
        # Disable conda auto-activation
        Disable-CondaAutoActivate
        
        # Test the installation
        Test-PixiInstallation
    } else {
        Write-Error "Installation failed"
        exit 1
    }
}

function Uninstall-Pixi {
    <#
    .SYNOPSIS
        Uninstall pixi package manager
    #>
    Write-Header "Uninstalling Pixi Package Manager"
    
    if (-not (Test-CommandExists "pixi")) {
        Write-Warning "Pixi is not installed or not in PATH"
        return
    }
    
    $pixiPath = (Get-Command pixi).Source
    Write-Info "Found pixi at: $pixiPath"
    
    # Confirm uninstallation
    $choice = Read-Host "Are you sure you want to uninstall pixi? (y/N)"
    if ($choice -notmatch '^[Yy]$') {
        Write-Info "Uninstallation cancelled."
        return
    }
    
    # Remove pixi binary
    if (Test-Path $pixiPath) {
        Write-Info "Removing pixi binary..."
        Remove-Item -Path $pixiPath -Force
        Write-Success "Pixi binary removed"
    }
    
    # Remove pixi directory if it exists
    if (Test-Path $InstallDir) {
        $choice = Read-Host "Remove pixi cache and configuration directory ($InstallDir)? (y/N)"
        if ($choice -match '^[Yy]$') {
            Write-Info "Removing pixi directory..."
            Remove-Item -Path $InstallDir -Recurse -Force
            Write-Success "Pixi directory removed"
        }
    }
    
    # Clean up environment PATH
    $choice = Read-Host "Remove pixi from system PATH? (y/N)"
    if ($choice -match '^[Yy]$') {
        Remove-PixiFromPath
    }
    
    # Clean up PowerShell profile
    $choice = Read-Host "Remove pixi entries from PowerShell profile? (y/N)"
    if ($choice -match '^[Yy]$') {
        Remove-PixiFromProfile
    }
    
    Write-Success "Pixi uninstallation completed!"
}

function Remove-PixiFromPath {
    <#
    .SYNOPSIS
        Remove pixi binary directory from PATH
    #>
    Write-Info "Removing pixi from system PATH..."
    
    # Get current user PATH
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    
    if ($currentPath) {
        # Remove BinDir from PATH
        $pathItems = $currentPath -split ';' | Where-Object { $_ -ne $BinDir }
        $newPath = $pathItems -join ';'
        
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        Write-Success "Removed pixi from system PATH"
    }
}

function Remove-PixiFromProfile {
    <#
    .SYNOPSIS
        Remove pixi entries from PowerShell profile
    #>
    $profilePath = $PROFILE.CurrentUserCurrentHost
    
    if (Test-Path $profilePath) {
        Write-Info "Cleaning up PowerShell profile..."
        
        $profileContent = Get-Content $profilePath -Raw
        
        # Remove both old and new pixi-related entries
        $cleanedContent = $profileContent -replace '(?s)\r?\n# Added by pixi installer.*?(?=\r?\n#|\r?\n\S|\Z)', ''
        $cleanedContent = $cleanedContent -replace '(?s)\r?\n# Pixi - Added before conda for priority.*?\$env:PATH[^\r\n]+\.pixi\\bin[^\r\n]+\r?\n?', ''
        
        Set-Content -Path $profilePath -Value $cleanedContent
        Write-Success "Cleaned up PowerShell profile"
    }
    
    # Also clean AllUsers profile if it exists
    $allUsersProfile = $PROFILE.AllUsersCurrentHost
    if (Test-Path $allUsersProfile) {
        Write-Info "Cleaning up AllUsers PowerShell profile..."
        
        $profileContent = Get-Content $allUsersProfile -Raw
        
        # Remove both old and new pixi-related entries
        $cleanedContent = $profileContent -replace '(?s)\r?\n# Added by pixi installer.*?(?=\r?\n#|\r?\n\S|\Z)', ''
        $cleanedContent = $cleanedContent -replace '(?s)\r?\n# Pixi - Added before conda for priority.*?\$env:PATH[^\r\n]+\.pixi\\bin[^\r\n]+\r?\n?', ''
        
        Set-Content -Path $allUsersProfile -Value $cleanedContent
        Write-Success "Cleaned up AllUsers PowerShell profile"
    }
}

function Test-PixiInstallation {
    <#
    .SYNOPSIS
        Verify pixi installation
    #>
    Write-Info "Verifying pixi installation..."
    
    # Refresh PATH for current session
    $env:PATH = "$BinDir;$env:PATH"
    
    if (Test-CommandExists "pixi") {
        try {
            $version = (pixi --version).Split()[1]
            Write-Success "Pixi installed successfully! Version: $version"
            
            $pixiLocation = (Get-Command pixi).Source
            Write-Info "Installation location: $pixiLocation"
            
            Write-Info "Testing pixi functionality..."
            $null = pixi --help
            Write-Success "Pixi is working correctly!"
            
            return $true
        } catch {
            Write-Warning "Pixi installed but may not be working correctly: $($_.Exception.Message)"
            return $false
        }
    } else {
        Write-Error "Pixi installation verification failed!"
        Write-Info "Try restarting PowerShell or running: . `$PROFILE"
        return $false
    }
}

function Show-Usage {
    <#
    .SYNOPSIS
        Display usage information
    #>
    @"
Pixi Package Manager - Install/Uninstall Script for Windows

Usage: .\Install-Pixi.ps1 [PARAMETERS]

Parameters:
    -Command <Install|Uninstall|Help>   Action to perform (default: Install)
    -Version <VERSION>                  Specific version to install (default: latest)
    -InstallDir <PATH>                  Installation directory (default: $env:USERPROFILE\.pixi)
    -BinDir <PATH>                     Binary directory (default: $env:USERPROFILE\.local\bin)
    -Method <Auto|Curl|Cargo|Binary>   Installation method (default: Auto)
    -Force                             Force installation even if already installed
    -Verbose                           Show detailed logging information

Examples:
    .\Install-Pixi.ps1                                    # Install with default settings
    .\Install-Pixi.ps1 -Version "0.7.0"                 # Install specific version
    .\Install-Pixi.ps1 -Method Cargo                    # Install via cargo
    .\Install-Pixi.ps1 -Force                           # Force reinstall
    .\Install-Pixi.ps1 -Command Uninstall               # Uninstall pixi

Installation Methods:
    Auto    - Try official installer, then binary, then cargo
    Curl    - Use official pixi installer script
    Cargo   - Install via Rust cargo (requires Rust)
    Binary  - Download and install binary directly

"@ | Write-Host
}

function Show-CompletionMessage {
    <#
    .SYNOPSIS
        Display completion message with usage instructions
    #>
    # Write-Host ""
    # Write-Success "Operation completed!"
    # Write-Host ""
    # Write-Info "Quick start with pixi:"
    # Write-Info "  pixi --version                     # Check version"
    # Write-Info "  pixi init my-project              # Initialize new project"
    # Write-Info "  pixi add python=3.11              # Add Python dependency"
    # Write-Info "  pixi run python --version         # Run command in environment"
    # Write-Info "  pixi shell                        # Activate project environment"
    # Write-Host ""
    # Write-Info "For more information, visit: https://pixi.sh/"
    # Write-Host ""
}

# Main execution
function Main {
    # Write-Host "==================================================" -ForegroundColor Cyan
    # Write-Host "       Pixi Package Manager Installer (Windows)"   -ForegroundColor Cyan
    # Write-Host "==================================================" -ForegroundColor Cyan
    # Write-Host ""
    
    switch ($Command) {
        "Install" {
            Install-Pixi
            Show-CompletionMessage
        }
        "Uninstall" {
            Uninstall-Pixi
            Show-CompletionMessage
        }
        "Help" {
            Show-Usage
        }
        default {
            Write-Error "Unknown command: $Command"
            Show-Usage
            exit 1
        }
    }
}

# Run main function
try {
    Main
} catch {
    Write-Error "Unexpected error: $($_.Exception.Message)"
    Write-Error "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}