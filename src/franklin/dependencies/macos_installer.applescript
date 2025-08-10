#!/usr/bin/osascript
-- macOS Installer with Radio Button UI using AppleScript
-- This creates a native dialog with radio button options for each dependency

on run
    -- Initialize dependency checker
    set dependencyStates to checkAllDependencies()
    
    -- Create the main dialog
    set dialogResult to showMainDialog(dependencyStates)
    
    if dialogResult is not false then
        -- Process the selected actions
        processInstallation(dialogResult)
    end if
end run

-- Check the state of all dependencies
on checkAllDependencies()
    set dependencies to {}
    
    -- Check Miniforge
    set miniforgeState to checkCommand("conda")
    set end of dependencies to {name:"Miniforge", state:miniforgeState, required:true, action:"none"}
    
    -- Check Pixi
    set pixiState to checkCommand("pixi")
    set end of dependencies to {name:"Pixi", state:pixiState, required:true, action:"none"}
    
    -- Check Docker
    set dockerState to checkDockerInstalled()
    set end of dependencies to {name:"Docker Desktop", state:dockerState, required:false, action:"none"}
    
    -- Check Chrome
    set chromeState to checkAppInstalled("Google Chrome")
    set end of dependencies to {name:"Google Chrome", state:chromeState, required:false, action:"none"}
    
    -- Check Franklin
    set franklinState to checkCommand("franklin")
    set end of dependencies to {name:"Franklin", state:franklinState, required:false, action:"none"}
    
    return dependencies
end checkAllDependencies

-- Check if a command exists
on checkCommand(commandName)
    try
        do shell script "which " & commandName
        -- Check version to determine if update available
        if commandName is "pixi" then
            set versionOutput to do shell script commandName & " --version 2>/dev/null" 
            if versionOutput contains "0." then
                -- Simple check - could be enhanced
                return "installed"
            end if
        end if
        return "installed"
    on error
        return "not_installed"
    end try
end checkCommand

-- Check if Docker is installed
on checkDockerInstalled()
    tell application "System Events"
        if exists (application process "Docker") then
            return "installed"
        else if exists file "/Applications/Docker.app" then
            return "installed"
        else
            return "not_installed"
        end if
    end tell
end checkDockerInstalled

-- Check if an app is installed
on checkAppInstalled(appName)
    tell application "System Events"
        if exists file ("/Applications/" & appName & ".app") then
            return "installed"
        else
            return "not_installed"
        end if
    end tell
end checkAppInstalled

-- Show the main dialog with radio buttons
on showMainDialog(dependencies)
    set dialogText to "Select actions for each component:" & return & return
    set componentChoices to {}
    
    -- Build the dialog text and choices
    repeat with dep in dependencies
        set depName to name of dep
        set depState to state of dep
        set depRequired to required of dep
        
        -- Add component status to dialog
        if depState is "installed" then
            set statusText to depName & " (✓ Installed)"
        else if depState is "outdated" then
            set statusText to depName & " (⚠ Update Available)"
        else
            set statusText to depName & " (✗ Not Installed)"
        end if
        
        set dialogText to dialogText & statusText & return
        
        -- Create action choices based on state
        set actions to {}
        set end of actions to "No Action"
        
        if depState is "not_installed" then
            set end of actions to "Install"
        else if depState is "installed" or depState is "outdated" then
            set end of actions to "Reinstall"
            if not depRequired then
                set end of actions to "Uninstall"
            end if
        end if
        
        -- Show action selection dialog for this component
        set actionChoice to choose from list actions with prompt ("Select action for " & depName & ":") default items {"No Action"} without multiple selections allowed
        
        if actionChoice is false then
            return false -- User cancelled
        end if
        
        set end of componentChoices to {name:depName, action:(item 1 of actionChoice)}
    end repeat
    
    -- Confirm the selections
    set summaryText to "Selected actions:" & return & return
    set hasActions to false
    
    repeat with choice in componentChoices
        set choiceName to name of choice
        set choiceAction to action of choice
        
        if choiceAction is not "No Action" then
            set summaryText to summaryText & "• " & choiceName & ": " & choiceAction & return
            set hasActions to true
        end if
    end repeat
    
    if not hasActions then
        display dialog "No actions selected. Nothing to do." buttons {"OK"} default button "OK" with icon note
        return false
    end if
    
    set summaryText to summaryText & return & "Proceed with installation?"
    
    set confirmResult to display dialog summaryText buttons {"Cancel", "Proceed"} default button "Proceed" with icon caution
    
    if button returned of confirmResult is "Cancel" then
        return false
    end if
    
    return componentChoices
end showMainDialog

-- Process the installation based on selected actions
on processInstallation(selections)
    set scriptPath to (path to me as text) & "::master-installer.sh"
    set scriptArgs to ""
    
    -- Build script arguments based on selections
    repeat with selection in selections
        set componentName to name of selection
        set componentAction to action of selection
        
        if componentAction is "No Action" then
            -- Add skip flag
            if componentName is "Miniforge" then
                set scriptArgs to scriptArgs & " --skip-miniforge"
            else if componentName is "Pixi" then
                set scriptArgs to scriptArgs & " --skip-pixi"
            else if componentName is "Docker Desktop" then
                set scriptArgs to scriptArgs & " --skip-docker"
            else if componentName is "Google Chrome" then
                set scriptArgs to scriptArgs & " --skip-chrome"
            else if componentName is "Franklin" then
                set scriptArgs to scriptArgs & " --skip-franklin"
            end if
        else if componentAction is "Reinstall" then
            -- Add force flag for specific component
            if componentName is "Miniforge" then
                set scriptArgs to scriptArgs & " --force-miniforge"
            else if componentName is "Pixi" then
                set scriptArgs to scriptArgs & " --force-pixi"
            else if componentName is "Docker Desktop" then
                set scriptArgs to scriptArgs & " --force-docker"
            else if componentName is "Google Chrome" then
                set scriptArgs to scriptArgs & " --force-chrome"
            else if componentName is "Franklin" then
                set scriptArgs to scriptArgs & " --force-franklin"
            end if
        else if componentAction is "Uninstall" then
            -- Handle uninstall (would need separate uninstall script)
            if componentName is "Docker Desktop" then
                try
                    do shell script "osascript -e 'quit app \"Docker\"'"
                    do shell script "rm -rf /Applications/Docker.app" with administrator privileges
                end try
            else if componentName is "Google Chrome" then
                try
                    do shell script "osascript -e 'quit app \"Google Chrome\"'"
                    do shell script "rm -rf '/Applications/Google Chrome.app'" with administrator privileges
                end try
            else if componentName is "Franklin" then
                try
                    do shell script "pixi global uninstall franklin"
                end try
            end if
        end if
    end repeat
    
    -- Show progress dialog
    display dialog "Starting installation..." & return & return & "A Terminal window will open to show progress." buttons {"OK"} default button "OK" with icon note
    
    -- Get the directory containing this script
    set scriptDir to do shell script "dirname " & quoted form of (POSIX path of (path to me))
    set installerScript to scriptDir & "/master-installer.sh"
    
    -- Execute the installer script in Terminal
    tell application "Terminal"
        activate
        set newWindow to do script "cd " & quoted form of scriptDir & " && bash master-installer.sh" & scriptArgs
        
        -- Wait for completion
        repeat
            delay 2
            if not busy of newWindow then exit repeat
        end repeat
        
        -- Show completion dialog
        display dialog "Installation process completed!" & return & return & "Please check the Terminal window for details." buttons {"OK"} default button "OK" with icon note
    end tell
end processInstallation