#Requires -Version 5.1
<#
.SYNOPSIS
    Windows GUI Installer with Radio Buttons for Franklin Dependencies
    
.DESCRIPTION
    Creates a native Windows Forms GUI with radio buttons for install/reinstall/uninstall options
#>

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Dependency class definition
Add-Type @"
using System;
public class Dependency {
    public string Name { get; set; }
    public string DisplayName { get; set; }
    public string Description { get; set; }
    public string State { get; set; }
    public string Version { get; set; }
    public string LatestVersion { get; set; }
    public string SelectedAction { get; set; }
    public bool IsRequired { get; set; }
    public string[] Dependencies { get; set; }
    
    public bool CanInstall {
        get { return State == "NotInstalled" || State == "Corrupted"; }
    }
    
    public bool CanReinstall {
        get { return State == "Installed" || State == "Outdated" || State == "Corrupted"; }
    }
    
    public bool CanUninstall {
        get { return (State == "Installed" || State == "Outdated" || State == "Corrupted") && !IsRequired; }
    }
}
"@

# Function to check dependency states
function Get-DependencyState {
    param([string]$Name)
    
    switch ($Name) {
        "miniforge" {
            if (Get-Command conda -ErrorAction SilentlyContinue) {
                $version = & conda --version 2>$null
                if ($version) {
                    return @{State = "Installed"; Version = ($version -split ' ')[-1]}
                }
            }
            return @{State = "NotInstalled"}
        }
        "pixi" {
            if (Get-Command pixi -ErrorAction SilentlyContinue) {
                $version = & pixi --version 2>$null
                if ($version) {
                    return @{State = "Installed"; Version = ($version -split ' ')[-1]}
                }
            }
            return @{State = "NotInstalled"}
        }
        "docker" {
            $dockerPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
            if (Test-Path $dockerPath) {
                if (Get-Command docker -ErrorAction SilentlyContinue) {
                    $version = & docker --version 2>$null
                    if ($version) {
                        return @{State = "Installed"; Version = ($version -split ',')[0] -split ' '[-1]}
                    }
                }
                return @{State = "Installed"}
            }
            return @{State = "NotInstalled"}
        }
        "chrome" {
            $chromePaths = @(
                "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
                "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
                "${env:LocalAppData}\Google\Chrome\Application\chrome.exe"
            )
            foreach ($path in $chromePaths) {
                if (Test-Path $path) {
                    $versionInfo = (Get-Item $path).VersionInfo
                    return @{State = "Installed"; Version = $versionInfo.ProductVersion}
                }
            }
            return @{State = "NotInstalled"}
        }
        "franklin" {
            if (Get-Command franklin -ErrorAction SilentlyContinue) {
                $version = & franklin --version 2>$null
                if ($version) {
                    return @{State = "Installed"; Version = ($version -split ' ')[-1]}
                }
            }
            # Check if installed via pixi global
            if (Get-Command pixi -ErrorAction SilentlyContinue) {
                $pixiList = & pixi global list 2>$null
                if ($pixiList -match "franklin") {
                    return @{State = "Installed"}
                }
            }
            return @{State = "NotInstalled"}
        }
        default {
            return @{State = "NotInstalled"}
        }
    }
}

# Create the main form
$form = New-Object System.Windows.Forms.Form
$form.Text = "Franklin Development Environment Installer"
$form.Size = New-Object System.Drawing.Size(800, 600)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

# Create title label
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Location = New-Object System.Drawing.Point(20, 20)
$titleLabel.Size = New-Object System.Drawing.Size(760, 30)
$titleLabel.Text = "Select Installation Actions for Each Component"
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($titleLabel)

# Create description label
$descLabel = New-Object System.Windows.Forms.Label
$descLabel.Location = New-Object System.Drawing.Point(20, 55)
$descLabel.Size = New-Object System.Drawing.Size(760, 40)
$descLabel.Text = "Choose the action for each component below. Grayed out options are not available based on the current state."
$descLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$form.Controls.Add($descLabel)

# Create dependencies
$dependencies = @(
    [Dependency]@{
        Name = "miniforge"
        DisplayName = "Miniforge"
        Description = "Python distribution and package manager"
        IsRequired = $true
        Dependencies = @()
    },
    [Dependency]@{
        Name = "pixi"
        DisplayName = "Pixi"
        Description = "Modern package manager for scientific computing"
        IsRequired = $true
        Dependencies = @("miniforge")
    },
    [Dependency]@{
        Name = "docker"
        DisplayName = "Docker Desktop"
        Description = "Container platform for development"
        IsRequired = $false
        Dependencies = @()
    },
    [Dependency]@{
        Name = "chrome"
        DisplayName = "Google Chrome"
        Description = "Web browser for development"
        IsRequired = $false
        Dependencies = @()
    },
    [Dependency]@{
        Name = "franklin"
        DisplayName = "Franklin"
        Description = "Educational platform for Jupyter notebooks"
        IsRequired = $false
        Dependencies = @("pixi")
    }
)

# Check states for all dependencies
foreach ($dep in $dependencies) {
    $stateInfo = Get-DependencyState -Name $dep.Name
    $dep.State = $stateInfo.State
    $dep.Version = $stateInfo.Version
    $dep.SelectedAction = "None"
}

# Create panel for components
$componentPanel = New-Object System.Windows.Forms.Panel
$componentPanel.Location = New-Object System.Drawing.Point(20, 100)
$componentPanel.Size = New-Object System.Drawing.Size(760, 380)
$componentPanel.AutoScroll = $true
$componentPanel.BorderStyle = "FixedSingle"
$form.Controls.Add($componentPanel)

# Create component UI for each dependency
$yPosition = 10
$radioGroups = @{}

foreach ($dep in $dependencies) {
    # Create group box for component
    $groupBox = New-Object System.Windows.Forms.GroupBox
    $groupBox.Location = New-Object System.Drawing.Point(10, $yPosition)
    $groupBox.Size = New-Object System.Drawing.Size(720, 100)
    $groupBox.Text = $dep.DisplayName
    $groupBox.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    
    # Component description
    $descLabel = New-Object System.Windows.Forms.Label
    $descLabel.Location = New-Object System.Drawing.Point(10, 20)
    $descLabel.Size = New-Object System.Drawing.Size(400, 20)
    $descLabel.Text = $dep.Description
    $descLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $groupBox.Controls.Add($descLabel)
    
    # Status label
    $statusLabel = New-Object System.Windows.Forms.Label
    $statusLabel.Location = New-Object System.Drawing.Point(10, 40)
    $statusLabel.Size = New-Object System.Drawing.Size(200, 20)
    $statusLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    
    switch ($dep.State) {
        "Installed" {
            $statusLabel.Text = "Status: [OK] Installed"
            $statusLabel.ForeColor = [System.Drawing.Color]::Green
            if ($dep.Version) {
                $statusLabel.Text += " (v$($dep.Version))"
            }
        }
        "Outdated" {
            $statusLabel.Text = "Status: [UPDATE] Update Available"
            $statusLabel.ForeColor = [System.Drawing.Color]::Orange
        }
        "Corrupted" {
            $statusLabel.Text = "Status: [WARNING] Corrupted"
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
        }
        default {
            $statusLabel.Text = "Status: [X] Not Installed"
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
        }
    }
    $groupBox.Controls.Add($statusLabel)
    
    # Radio buttons
    $radioNone = New-Object System.Windows.Forms.RadioButton
    $radioNone.Location = New-Object System.Drawing.Point(420, 20)
    $radioNone.Size = New-Object System.Drawing.Size(80, 20)
    $radioNone.Text = "No Action"
    $radioNone.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $radioNone.Checked = $true
    $radioNone.Tag = @{Dependency = $dep; Action = "None"}
    
    $radioInstall = New-Object System.Windows.Forms.RadioButton
    $radioInstall.Location = New-Object System.Drawing.Point(420, 40)
    $radioInstall.Size = New-Object System.Drawing.Size(80, 20)
    $radioInstall.Text = "Install"
    $radioInstall.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $radioInstall.Enabled = $dep.CanInstall
    $radioInstall.Tag = @{Dependency = $dep; Action = "Install"}
    
    $radioReinstall = New-Object System.Windows.Forms.RadioButton
    $radioReinstall.Location = New-Object System.Drawing.Point(510, 40)
    $radioReinstall.Size = New-Object System.Drawing.Size(80, 20)
    $radioReinstall.Text = "Reinstall"
    $radioReinstall.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $radioReinstall.Enabled = $dep.CanReinstall
    $radioReinstall.Tag = @{Dependency = $dep; Action = "Reinstall"}
    
    $radioUninstall = New-Object System.Windows.Forms.RadioButton
    $radioUninstall.Location = New-Object System.Drawing.Point(600, 40)
    $radioUninstall.Size = New-Object System.Drawing.Size(80, 20)
    $radioUninstall.Text = "Uninstall"
    $radioUninstall.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $radioUninstall.Enabled = $dep.CanUninstall
    $radioUninstall.Tag = @{Dependency = $dep; Action = "Uninstall"}
    
    # Add tooltips for disabled options
    if (-not $radioInstall.Enabled) {
        $radioInstall.Text = "Install (N/A)"
    }
    if (-not $radioReinstall.Enabled) {
        $radioReinstall.Text = "Reinstall (N/A)"
    }
    if (-not $radioUninstall.Enabled) {
        if ($dep.IsRequired) {
            $radioUninstall.Text = "Uninstall (Req)"
        } else {
            $radioUninstall.Text = "Uninstall (N/A)"
        }
    }
    
    # Add event handlers
    $radioHandler = {
        $tag = $this.Tag
        $tag.Dependency.SelectedAction = $tag.Action
        Update-InstallButton
    }
    
    $radioNone.Add_Click($radioHandler)
    $radioInstall.Add_Click($radioHandler)
    $radioReinstall.Add_Click($radioHandler)
    $radioUninstall.Add_Click($radioHandler)
    
    $groupBox.Controls.Add($radioNone)
    $groupBox.Controls.Add($radioInstall)
    $groupBox.Controls.Add($radioReinstall)
    $groupBox.Controls.Add($radioUninstall)
    
    # Store radio buttons for this dependency
    $radioGroups[$dep.Name] = @{
        None = $radioNone
        Install = $radioInstall
        Reinstall = $radioReinstall
        Uninstall = $radioUninstall
    }
    
    $componentPanel.Controls.Add($groupBox)
    $yPosition += 110
}

# Create refresh button
$refreshButton = New-Object System.Windows.Forms.Button
$refreshButton.Location = New-Object System.Drawing.Point(20, 490)
$refreshButton.Size = New-Object System.Drawing.Size(100, 30)
$refreshButton.Text = "Refresh"
$refreshButton.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$refreshButton.Add_Click({
    # Refresh dependency states
    foreach ($dep in $dependencies) {
        $stateInfo = Get-DependencyState -Name $dep.Name
        $dep.State = $stateInfo.State
        $dep.Version = $stateInfo.Version
    }
    # Update UI would go here
    [System.Windows.Forms.MessageBox]::Show("States refreshed!", "Refresh", "OK", "Information")
})
$form.Controls.Add($refreshButton)

# Create install button
$installButton = New-Object System.Windows.Forms.Button
$installButton.Location = New-Object System.Drawing.Point(580, 490)
$installButton.Size = New-Object System.Drawing.Size(200, 40)
$installButton.Text = "Execute Selected Actions"
$installButton.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$installButton.BackColor = [System.Drawing.Color]::FromArgb(0, 120, 215)
$installButton.ForeColor = [System.Drawing.Color]::White
$installButton.FlatStyle = "Flat"

# Function to update install button
function Update-InstallButton {
    $actionCount = 0
    foreach ($dep in $dependencies) {
        if ($dep.SelectedAction -ne "None") {
            $actionCount++
        }
    }
    
    if ($actionCount -gt 0) {
        $installButton.Text = "Execute $actionCount Action$(if ($actionCount -gt 1) {'s'} else {''})"
        $installButton.Enabled = $true
    } else {
        $installButton.Text = "No Actions Selected"
        $installButton.Enabled = $false
    }
}

$installButton.Add_Click({
    # Build command arguments
    $scriptArgs = @()
    $uninstallActions = @()
    
    foreach ($dep in $dependencies) {
        switch ($dep.SelectedAction) {
            "None" {
                $scriptArgs += "--skip-$($dep.Name)"
            }
            "Install" {
                # Default action, no skip needed
            }
            "Reinstall" {
                $scriptArgs += "--force"
            }
            "Uninstall" {
                $uninstallActions += $dep
            }
        }
    }
    
    # Ask for user role if Franklin is being installed
    $franklinDep = $dependencies | Where-Object { $_.Name -eq "franklin" }
    $userRole = "student"
    
    if ($franklinDep -and ($franklinDep.SelectedAction -eq "Install" -or $franklinDep.SelectedAction -eq "Reinstall")) {
        # Create role selection dialog
        $roleForm = New-Object System.Windows.Forms.Form
        $roleForm.Text = "Select User Role"
        $roleForm.Size = New-Object System.Drawing.Size(400, 200)
        $roleForm.StartPosition = "CenterParent"
        
        $roleLabel = New-Object System.Windows.Forms.Label
        $roleLabel.Location = New-Object System.Drawing.Point(20, 20)
        $roleLabel.Size = New-Object System.Drawing.Size(360, 30)
        $roleLabel.Text = "Select your Franklin user role:"
        $roleForm.Controls.Add($roleLabel)
        
        $roleCombo = New-Object System.Windows.Forms.ComboBox
        $roleCombo.Location = New-Object System.Drawing.Point(20, 60)
        $roleCombo.Size = New-Object System.Drawing.Size(360, 30)
        $roleCombo.DropDownStyle = "DropDownList"
        $roleCombo.Items.AddRange(@("Student (standard Franklin)", "Educator (franklin-educator)", "Administrator (franklin-admin)"))
        $roleCombo.SelectedIndex = 0
        $roleForm.Controls.Add($roleCombo)
        
        $roleOK = New-Object System.Windows.Forms.Button
        $roleOK.Location = New-Object System.Drawing.Point(150, 110)
        $roleOK.Size = New-Object System.Drawing.Size(100, 30)
        $roleOK.Text = "OK"
        $roleOK.DialogResult = [System.Windows.Forms.DialogResult]::OK
        $roleForm.Controls.Add($roleOK)
        
        if ($roleForm.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            switch ($roleCombo.SelectedIndex) {
                0 { $userRole = "student" }
                1 { $userRole = "educator" }
                2 { $userRole = "administrator" }
            }
            $scriptArgs += "--role", $userRole
        }
    }
    
    # Confirm actions
    $message = "The following actions will be performed:`n`n"
    foreach ($dep in $dependencies) {
        if ($dep.SelectedAction -ne "None") {
            $displayText = $dep.DisplayName
            if ($dep.Name -eq "franklin" -and ($dep.SelectedAction -eq "Install" -or $dep.SelectedAction -eq "Reinstall")) {
                $displayText = "Franklin ($userRole)"
            }
            $message += "- ${displayText}: $($dep.SelectedAction)`n"
        }
    }
    $message += "`nDo you want to proceed?"
    
    $result = [System.Windows.Forms.MessageBox]::Show($message, "Confirm Actions", "YesNo", "Question")
    
    if ($result -eq "Yes") {
        # Handle uninstalls first
        foreach ($dep in $uninstallActions) {
            switch ($dep.Name) {
                "docker" {
                    Write-Host "Uninstalling Docker Desktop..."
                    Stop-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
                    $uninstallPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop Installer.exe"
                    if (Test-Path $uninstallPath) {
                        Start-Process -FilePath $uninstallPath -ArgumentList "uninstall" -Wait
                    }
                }
                "chrome" {
                    Write-Host "Uninstalling Google Chrome..."
                    $uninstallString = Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" | 
                        Where-Object { $_.DisplayName -like "*Google Chrome*" } | 
                        Select-Object -ExpandProperty UninstallString
                    if ($uninstallString) {
                        Start-Process -FilePath $uninstallString -Wait
                    }
                }
                "franklin" {
                    Write-Host "Uninstalling Franklin..."
                    & pixi global uninstall franklin
                }
            }
        }
        
        # Execute installation script
        $scriptPath = Join-Path $PSScriptRoot "Master-Installer.ps1"
        if (Test-Path $scriptPath) {
            # Show progress window
            $progressForm = New-Object System.Windows.Forms.Form
            $progressForm.Text = "Installation in Progress"
            $progressForm.Size = New-Object System.Drawing.Size(500, 200)
            $progressForm.StartPosition = "CenterParent"
            
            $progressLabel = New-Object System.Windows.Forms.Label
            $progressLabel.Location = New-Object System.Drawing.Point(20, 20)
            $progressLabel.Size = New-Object System.Drawing.Size(460, 60)
            $progressLabel.Text = "Installing components...`nPlease wait, this may take several minutes."
            $progressForm.Controls.Add($progressLabel)
            
            $progressBar = New-Object System.Windows.Forms.ProgressBar
            $progressBar.Location = New-Object System.Drawing.Point(20, 90)
            $progressBar.Size = New-Object System.Drawing.Size(460, 30)
            $progressBar.Style = "Marquee"
            $progressForm.Controls.Add($progressBar)
            
            $progressForm.Show()
            
            # Run the installer
            Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptPath`" $($scriptArgs -join ' ')" -Wait
            
            $progressForm.Close()
            
            [System.Windows.Forms.MessageBox]::Show("Installation completed! Please check the console for details.", "Complete", "OK", "Information")
            
            # Refresh states
            $refreshButton.PerformClick()
        } else {
            [System.Windows.Forms.MessageBox]::Show("Installer script not found: $scriptPath", "Error", "OK", "Error")
        }
    }
})
$form.Controls.Add($installButton)

# Create status bar
$statusBar = New-Object System.Windows.Forms.StatusStrip
$statusLabel = New-Object System.Windows.Forms.ToolStripStatusLabel
$statusLabel.Text = "Ready"
$statusBar.Items.Add($statusLabel)
$form.Controls.Add($statusBar)

# Initialize button state
Update-InstallButton

# Show the form
[System.Windows.Forms.Application]::EnableVisualStyles()
$form.ShowDialog()