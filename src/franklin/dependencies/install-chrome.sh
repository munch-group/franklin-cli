#!/bin/bash
set -euo pipefail

# Early OS check - this script is for macOS only
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "ERROR: This script is for macOS only. Detected OS: $OSTYPE"
    echo "For Linux, please install Chrome via your package manager:"
    echo "  Ubuntu/Debian: sudo apt install google-chrome-stable"
    echo "  Fedora: sudo dnf install google-chrome-stable"
    echo "  Or download from: https://www.google.com/chrome/"
    exit 1
fi

# Configuration
USERNAME=$(whoami)
LOG_FILE="/tmp/chrome_install.log"
CHROME_APP="/Applications/Google Chrome.app"
CHROME_PREFERENCES="$HOME/Library/Preferences/com.google.Chrome.plist"
CHROME_USER_DATA="$HOME/Library/Application Support/Google/Chrome"

# Command line options
UNINSTALL=false
CLEAN_UNINSTALL=false
STATUS_CHECK=false
SET_AS_DEFAULT=true
DISABLE_TRACKING=true
DISABLE_UPDATES=false
ENTERPRISE_MODE=false
HOMEPAGE_URL=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --clean-uninstall)
            CLEAN_UNINSTALL=true
            shift
            ;;
        --status)
            STATUS_CHECK=true
            shift
            ;;
        --no-default)
            SET_AS_DEFAULT=false
            shift
            ;;
        --enable-tracking)
            DISABLE_TRACKING=false
            shift
            ;;
        --disable-updates)
            DISABLE_UPDATES=true
            shift
            ;;
        --enterprise)
            ENTERPRISE_MODE=true
            shift
            ;;
        --homepage)
            HOMEPAGE_URL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --uninstall        Remove Chrome (keep user data)"
            echo "  --clean-uninstall  Remove Chrome and all data"
            echo "  --status          Show installation status"
            echo "  --no-default      Don't set Chrome as default browser"
            echo "  --enable-tracking  Don't disable tracking features"
            echo "  --disable-updates  Disable automatic updates"
            echo "  --enterprise      Apply enterprise security settings"
            echo "  --homepage URL    Set custom homepage"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_requirements() {
    MACOS_VERSION=$(sw_vers -productVersion)
    MAJOR_VERSION=$(echo $MACOS_VERSION | cut -d. -f1)
    
    if [[ $MAJOR_VERSION -lt 11 ]]; then
        log "ERROR: macOS 11.0 (Big Sur) or later required"
        exit 1
    fi
    
    AVAILABLE_SPACE=$(df -g / | tail -1 | awk '{print $4}')
    if [[ $AVAILABLE_SPACE -lt 5 ]]; then
        log "ERROR: Insufficient disk space (5GB required)"
        exit 1
    fi
}

get_installation_status() {
    echo "=== Google Chrome Installation Status ==="
    
    # Check if Chrome is installed
    if [[ -d "$CHROME_APP" ]]; then
        echo "✅ Chrome: Installed"
        
        # Get version info
        local version_plist="$CHROME_APP/Contents/Info.plist"
        if [[ -f "$version_plist" ]]; then
            local version=$(defaults read "$version_plist" CFBundleShortVersionString 2>/dev/null || echo "Unknown")
            echo "   Version: $version"
        fi
        
        local bundle_id=$(defaults read "$version_plist" CFBundleIdentifier 2>/dev/null || echo "Unknown")
        echo "   Bundle ID: $bundle_id"
    else
        echo "❌ Chrome: Not installed"
    fi
    
    # Check if Chrome is running
    if pgrep -x "Google Chrome" > /dev/null; then
        echo "✅ Chrome: Running"
    else
        echo "⚠️  Chrome: Not running"
    fi
    
    # Check default browser
    local default_browser=$(defaults read ~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure | grep -A 1 "https" | grep "LSHandlerRoleAll" -A 1 | grep "com.google.chrome" || echo "")
    if [[ -n "$default_browser" ]]; then
        echo "✅ Default Browser: Chrome"
    else
        echo "⚠️  Default Browser: Not Chrome"
    fi
    
    # Check user data
    echo ""
    echo "User Data:"
    if [[ -d "$CHROME_USER_DATA" ]]; then
        local profiles=$(ls "$CHROME_USER_DATA" | grep -E "^(Default|Profile)" | wc -l | tr -d ' ')
        echo "✅ User profiles: $profiles"
        
        local size=$(du -sh "$CHROME_USER_DATA" 2>/dev/null | cut -f1 || echo "Unknown")
        echo "   Data size: $size"
    else
        echo "❌ User data: Not found"
    fi
    
    # Check preferences
    if [[ -f "$CHROME_PREFERENCES" ]]; then
        echo "✅ Preferences: Configured"
    else
        echo "⚠️  Preferences: Default"
    fi
    
    # Check for managed policies
    local managed_prefs="/Library/Managed Preferences/$USERNAME/com.google.Chrome.plist"
    if [[ -f "$managed_prefs" ]]; then
        echo "✅ Managed policies: Active"
    else
        echo "⚠️  Managed policies: None"
    fi
    
    # Check updates
    local update_plist="$HOME/Library/Google/GoogleSoftwareUpdate/GoogleSoftwareUpdate.bundle/Contents/Info.plist"
    if [[ -f "$update_plist" ]]; then
        echo "✅ Auto-update: Enabled"
    else
        echo "⚠️  Auto-update: Disabled/Not found"
    fi
}

uninstall_chrome() {
    local keep_user_data=${1:-false}
    
    log "Starting Google Chrome uninstallation..."
    
    # Stop Chrome processes
    log "Stopping Chrome processes..."
    osascript -e 'quit app "Google Chrome"' 2>/dev/null || true
    
    # Wait for processes to stop
    local count=0
    while pgrep -x "Google Chrome" > /dev/null && [[ $count -lt 30 ]]; do
        sleep 1
        ((count++))
    done
    
    # Force kill if still running
    if pgrep -x "Google Chrome" > /dev/null; then
        log "Force killing Chrome processes..."
        pkill -9 "Google Chrome" 2>/dev/null || true
    fi
    
    # Remove application
    if [[ -d "$CHROME_APP" ]]; then
        log "Removing Chrome application..."
        rm -rf "$CHROME_APP"
        echo "✅ Removed: $CHROME_APP"
    fi
    
    # Remove Google Software Update
    local update_paths=(
        "$HOME/Library/Google"
        "/Library/Google"
        "$HOME/Library/Application Support/Google"
        "$HOME/Library/Caches/com.google.SoftwareUpdate"
    )
    
    for path in "${update_paths[@]}"; do
        if [[ -d "$path" ]] && [[ "$keep_user_data" != "true" || "$path" == *"Library/Google"* || "$path" == *"SoftwareUpdate"* ]]; then
            rm -rf "$path" 2>/dev/null || true
            echo "✅ Removed: $path"
        fi
    done
    
    # Remove user data if requested
    if [[ "$keep_user_data" != "true" ]]; then
        log "Removing user data..."
        
        local user_paths=(
            "$CHROME_USER_DATA"
            "$CHROME_PREFERENCES"
            "$HOME/Library/Caches/com.google.Chrome"
            "$HOME/Library/Caches/com.google.Chrome.helper"
            "$HOME/Library/Saved Application State/com.google.Chrome.savedState"
            "$HOME/Library/WebKit/com.google.Chrome"
            "$HOME/Library/Cookies/com.google.Chrome.binarycookies"
        )
        
        for path in "${user_paths[@]}"; do
            if [[ -e "$path" ]]; then
                rm -rf "$path"
                echo "✅ Removed: $path"
            fi
        done
    else
        log "Keeping user data (use --clean-uninstall to remove all data)"
    fi
    
    # Remove managed preferences
    local managed_prefs="/Library/Managed Preferences/$USERNAME/com.google.Chrome.plist"
    if [[ -f "$managed_prefs" ]]; then
        sudo rm -f "$managed_prefs" 2>/dev/null || true
        echo "✅ Removed managed preferences"
    fi
    
    # Remove system-wide preferences
    local system_prefs="/Library/Preferences/com.google.Chrome.plist"
    if [[ -f "$system_prefs" ]]; then
        sudo rm -f "$system_prefs" 2>/dev/null || true
        echo "✅ Removed system preferences"
    fi
    
    # Remove LaunchAgents
    local launch_agents=(
        "$HOME/Library/LaunchAgents/com.google.keystone.agent.plist"
        "/Library/LaunchAgents/com.google.keystone.agent.plist"
        "/Library/LaunchDaemons/com.google.keystone.daemon.plist"
    )
    
    for agent in "${launch_agents[@]}"; do
        if [[ -f "$agent" ]]; then
            if [[ "$agent" == "/Library/"* ]]; then
                sudo launchctl unload "$agent" 2>/dev/null || true
                sudo rm -f "$agent"
            else
                launchctl unload "$agent" 2>/dev/null || true
                rm -f "$agent"
            fi
            echo "✅ Removed launch agent: $agent"
        fi
    done
    
    # Reset default browser if Chrome was default
    defaults delete ~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure 2>/dev/null || true
    
    log "Google Chrome uninstallation completed!"
    echo ""
    echo "Uninstallation Summary:"
    echo "✅ Chrome application removed"
    echo "✅ Google Update services removed"
    echo "✅ Launch agents removed"
    
    if [[ "$keep_user_data" != "true" ]]; then
        echo "✅ User data removed"
    else
        echo "⚠️  User data preserved"
    fi
}

install_chrome() {
    log "Starting Google Chrome installation..."
    
    # Determine architecture
    ARCH=$(uname -m)
    if [[ $ARCH == "arm64" ]]; then
        DOWNLOAD_URL="https://dl.google.com/chrome/mac/universal/stable/GGRO/googlechrome.dmg"
    else
        DOWNLOAD_URL="https://dl.google.com/chrome/mac/stable/GGRO/googlechrome.dmg"
    fi
    
    log "Downloading Chrome for $ARCH..."
    curl -L -o /tmp/GoogleChrome.dmg "$DOWNLOAD_URL"
    
    if [[ ! -f "/tmp/GoogleChrome.dmg" ]]; then
        log "ERROR: Failed to download Chrome"
        exit 1
    fi
    
    log "Installing Chrome..."
    
    # Mount the DMG
    hdiutil attach /tmp/GoogleChrome.dmg -nobrowse -quiet
    
    # Copy the app
    cp -R "/Volumes/Google Chrome/Google Chrome.app" /Applications/
    
    # Unmount the DMG
    hdiutil detach "/Volumes/Google Chrome" -quiet
    
    # Clean up
    rm -f /tmp/GoogleChrome.dmg
    
    log "✅ Chrome installation completed"
}

configure_chrome() {
    log "Configuring Google Chrome..."
    
    # Ensure Chrome preferences directory exists
    local prefs_dir=$(dirname "$CHROME_PREFERENCES")
    mkdir -p "$prefs_dir"
    
    # Create base preferences if they don't exist
    if [[ ! -f "$CHROME_PREFERENCES" ]]; then
        defaults write com.google.Chrome NSInitialToolTip -bool false
    fi
    
    # Configure privacy settings
    if [[ "$DISABLE_TRACKING" == "true" ]]; then
        log "Configuring privacy settings..."
        
        # Disable various tracking features
        defaults write com.google.Chrome MetricsReportingEnabled -bool false
        defaults write com.google.Chrome SearchSuggestEnabled -bool false
        defaults write com.google.Chrome NetworkPredictionOptions -int 2
        defaults write com.google.Chrome SafeBrowsingProtectionLevel -int 1
        defaults write com.google.Chrome PasswordManagerEnabled -bool false
        defaults write com.google.Chrome AutofillAddressEnabled -bool false
        defaults write com.google.Chrome AutofillCreditCardEnabled -bool false
        defaults write com.google.Chrome SyncDisabled -bool true
        defaults write com.google.Chrome SigninAllowed -bool false
        defaults write com.google.Chrome BrowserGuestModeEnabled -bool false
        defaults write com.google.Chrome PromotionalTabsEnabled -bool false
        defaults write com.google.Chrome WelcomePageOnOSUpgradeEnabled -bool false
        defaults write com.google.Chrome DefaultBrowserSettingEnabled -bool false
    fi
    
    # Configure updates
    if [[ "$DISABLE_UPDATES" == "true" ]]; then
        log "Disabling automatic updates..."
        defaults write com.google.Chrome UpdateDefault -int 0
        
        # Remove Google Software Update if present
        if [[ -d "$HOME/Library/Google/GoogleSoftwareUpdate" ]]; then
            rm -rf "$HOME/Library/Google/GoogleSoftwareUpdate"
        fi
        
        # Disable update services
        launchctl unload "$HOME/Library/LaunchAgents/com.google.keystone.agent.plist" 2>/dev/null || true
    fi
    
    # Set homepage
    if [[ -n "$HOMEPAGE_URL" ]]; then
        log "Setting homepage to: $HOMEPAGE_URL"
        defaults write com.google.Chrome HomepageLocation -string "$HOMEPAGE_URL"
        defaults write com.google.Chrome HomepageIsNewTabPage -bool false
        defaults write com.google.Chrome ShowHomeButton -bool true
    fi
    
    # Enterprise mode settings
    if [[ "$ENTERPRISE_MODE" == "true" ]]; then
        log "Applying enterprise security settings..."
        
        # Create managed preferences (requires admin rights for system-wide)
        local managed_prefs_dir="/Library/Managed Preferences/$USERNAME"
        
        if [[ -w "/Library/Managed Preferences" ]] || sudo -n true 2>/dev/null; then
            sudo mkdir -p "$managed_prefs_dir"
            
            # Create enterprise policy file
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" DeveloperToolsDisabled -bool true
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" IncognitoModeAvailability -int 1
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" BookmarkBarEnabled -bool true
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" ExtensionInstallBlacklist -array "*"
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" HideWebStoreIcon -bool true
            sudo defaults write "$managed_prefs_dir/com.google.Chrome" BrowserGuestModeEnabled -bool false
            
            sudo chown root:wheel "$managed_prefs_dir/com.google.Chrome.plist"
            sudo chmod 644 "$managed_prefs_dir/com.google.Chrome.plist"
        else
            log "WARNING: Cannot apply enterprise settings - admin rights required"
        fi
    fi
    
    log "✅ Chrome configuration completed"
}

set_chrome_as_default() {
    if [[ "$SET_AS_DEFAULT" == "true" ]]; then
        log "Setting Chrome as default browser..."
        
        # Use Chrome's built-in method
        if [[ -f "$CHROME_APP/Contents/MacOS/Google Chrome" ]]; then
            "$CHROME_APP/Contents/MacOS/Google Chrome" --make-default-browser &
            sleep 2
            pkill "Google Chrome" 2>/dev/null || true
            
            log "✅ Chrome set as default browser"
        else
            log "WARNING: Chrome executable not found"
        fi
    fi
}

# Main execution logic
main() {
    if [[ "$STATUS_CHECK" == "true" ]]; then
        get_installation_status
        exit 0
    fi
    
    if [[ "$UNINSTALL" == "true" ]] || [[ "$CLEAN_UNINSTALL" == "true" ]]; then
        echo "Google Chrome Uninstallation"
        echo "============================="
        echo ""
        
        # Show current status
        get_installation_status
        echo ""
        
        local keep_data="true"
        if [[ "$CLEAN_UNINSTALL" == "true" ]]; then
            keep_data="false"
            echo "⚠️  CLEAN UNINSTALL: This will remove ALL Chrome data including:"
            echo "   - Bookmarks and browsing history"
            echo "   - Saved passwords and autofill data"
            echo "   - Extensions and their data"
            echo "   - All user preferences and settings"
        else
            echo "Standard uninstall: Chrome will be removed but user data preserved"
        fi
        
        echo ""
        read -p "Proceed with uninstallation? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            echo "Uninstallation cancelled"
            exit 0
        fi
        
        uninstall_chrome "$keep_data"
        
        echo ""
        echo "Final status:"
        get_installation_status
        exit 0
    fi
    
    # Normal installation flow
    log "Starting Chrome installation and configuration..."
    check_requirements
    
    # Check if Chrome is already installed
    if [[ -d "$CHROME_APP" ]]; then
        log "Chrome is already installed. Applying configuration..."
    else
        install_chrome
    fi
    
    # Apply configuration
    configure_chrome
    
    # Set as default browser
    set_chrome_as_default
    
    log "Installation and configuration complete!"
    
    # echo ""
    # echo "🌐 Google Chrome installation completed successfully!"
    # echo ""
    # echo "Next steps:"
    # echo "1. Launch Chrome from Applications folder"
    # echo "2. Complete any initial setup if needed"
    # echo "3. Import bookmarks and settings if desired"
    # echo ""
    # echo "Management commands:"
    # echo "- Check status: $0 --status"
    # echo "- Uninstall: $0 --uninstall"
    # echo "- Clean uninstall: $0 --clean-uninstall"
    
    # Show final status
    echo ""
    echo "Final installation status:"
    get_installation_status
}

# Run main function
main "$@"