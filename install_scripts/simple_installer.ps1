#!/usr/bin/env powershell

<#
.SYNOPSIS
    Simple Development Environment Installer
    
.DESCRIPTION
    Calls installer scripts in sequence and installs Franklin via pixi.
    
.PARAMETER ScriptPath
    Directory containing the installer scripts (default: current directory)
    
.EXAMPLE
    .\Simple-Installer.ps1
    
.EXAMPLE
    .\Simple-Installer.ps1 -ScriptPath "C:\Installers"
#>

[CmdletBinding()]
param(
    [string]$ScriptPath = $PSScriptRoot
)

Write-Host "Development Environment Installer" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# List of scripts to run in order
$Scripts = @(
    "Install-Miniforge.ps1",
    "Install-Pixi.ps1", 
    "Install-Docker-Desktop.ps1",
    "Install-Chrome.ps1"
)

# Run each installer script
foreach ($script in $Scripts) {
    $scriptFullPath = Join-Path $ScriptPath $script
    
    Write-Host "Running: $script" -ForegroundColor Yellow
    
    if (Test-Path $scriptFullPath) {
        try {
            & $scriptFullPath
            Write-Host "✓ $script completed" -ForegroundColor Green
        }
        catch {
            Write-Host "✗ $script failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    else {
        Write-Host "✗ Script not found: $scriptFullPath" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Install Franklin via pixi
Write-Host "Installing Franklin via pixi..." -ForegroundColor Yellow

try {
    pixi global install -c munch-group -c conda-forge franklin
    Write-Host "✓ Franklin installation completed" -ForegroundColor Green
}
catch {
    Write-Host "✗ Franklin installation failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Installation process completed!" -ForegroundColor Cyan