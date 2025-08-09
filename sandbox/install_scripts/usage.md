Usage Examples:
bash# Make script executable
chmod +x master-installer.sh

# Basic installation (all components)
./master-installer.sh

# Skip certain components
./master-installer.sh --skip-docker --skip-chrome

# Force reinstall everything
./master-installer.sh --force

# Continue even if some installations fail
./master-installer.sh --continue-on-error

# Use scripts from different directory
./master-installer.sh --script-dir /path/to/scripts

# Multiple options
./master-installer.sh --force --continue-on-error --skip-franklin
Command Line Options:

--skip-miniforge - Skip miniforge installation
--skip-pixi - Skip pixi installation
--skip-docker - Skip Docker Desktop installation
--skip-chrome - Skip Chrome installation
--skip-franklin - Skip Franklin installation
--force - Force reinstall even if already installed
--continue-on-error - Continue with remaining installations if one fails
--script-dir DIR - Use scripts from different directory

Expected Script Names:

install-miniforge.sh
install-pixi.sh
install-docker-desktop.sh
install-chrome.sh