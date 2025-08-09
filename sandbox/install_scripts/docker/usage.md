.\windows\install-docker-desktop.ps1 -CleanUninstall  # Complete removal
.\windows\install-docker-desktop.ps1                   # Fresh install


./macos/install-docker-desktop.sh --clean-uninstall   # Complete removal
./macos/install-docker-desktop.sh  




# Standard uninstall (keep data)
./install-docker-desktop.sh --uninstall

# Complete removal
./install-docker-desktop.sh --clean-uninstall

# Check status
./install-docker-desktop.sh --status

# Configure existing installation
./install-docker-desktop.sh --configure-only



# Standard uninstall (keep data)
.\install-docker-desktop.ps1 -Uninstall

# Complete removal
.\install-docker-desktop.ps1 -CleanUninstall

# Check status
Get-DockerInstallationStatus