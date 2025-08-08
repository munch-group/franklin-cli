# Basic installation
.\Install-Miniforge.ps1

# Custom installation directory
.\Install-Miniforge.ps1 -InstallDir "C:\miniforge3"

# Force reinstall over existing installation
.\Install-Miniforge.ps1 -Force

# Install without auto-activating base environment
.\Install-Miniforge.ps1 -NoAutoActivate

# Install without updating PowerShell profile
.\Install-Miniforge.ps1 -NoProfileUpdate





# Basic installation
./install_miniforge.sh

# Custom installation directory
./install_miniforge.sh -d /opt/miniforge3

# Install without auto-activating base environment
./install_miniforge.sh --no-auto-activate