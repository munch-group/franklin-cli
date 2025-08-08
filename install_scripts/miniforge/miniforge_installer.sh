#!/bin/bash

# Miniforge Python Installer
# Cross-platform installer for miniforge conda distribution
# Supports Linux, macOS, and Windows (via WSL/Git Bash)

set -euo pipefail

# Configuration
MINIFORGE_VERSION="latest"
INSTALL_DIR="$HOME/miniforge3"
CONDA_FORGE_ONLY=true
AUTO_ACTIVATE=true
UPDATE_PROFILE=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to detect operating system and architecture
detect_platform() {
    local os_type=$(uname -s)
    local arch=$(uname -m)
    
    case "$os_type" in
        Linux*)
            case "$arch" in
                x86_64) echo "Linux-x86_64" ;;
                aarch64) echo "Linux-aarch64" ;;
                ppc64le) echo "Linux-ppc64le" ;;
                *) log_error "Unsupported Linux architecture: $arch"; exit 1 ;;
            esac
            ;;
        Darwin*)
            case "$arch" in
                x86_64) echo "MacOSX-x86_64" ;;
                arm64) echo "MacOSX-arm64" ;;
                *) log_error "Unsupported macOS architecture: $arch"; exit 1 ;;
            esac
            ;;
        CYGWIN*|MINGW*|MSYS*)
            case "$arch" in
                x86_64) echo "Windows-x86_64" ;;
                *) log_error "Unsupported Windows architecture: $arch"; exit 1 ;;
            esac
            ;;
        *)
            log_error "Unsupported operating system: $os_type"
            exit 1
            ;;
    esac
}

# Function to get download URL
get_download_url() {
    local platform=$1
    local base_url="https://github.com/conda-forge/miniforge/releases/latest/download"
    
    case "$platform" in
        Linux-*)
            echo "$base_url/Miniforge3-$platform.sh"
            ;;
        MacOSX-*)
            echo "$base_url/Miniforge3-$platform.sh"
            ;;
        Windows-*)
            echo "$base_url/Miniforge3-$platform.exe"
            ;;
    esac
}

# Function to check if miniforge is already installed
check_existing_installation() {
    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Miniforge installation found at $INSTALL_DIR"
        read -p "Do you want to remove the existing installation and reinstall? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing existing installation..."
            rm -rf "$INSTALL_DIR"
        else
            log_info "Keeping existing installation. Exiting."
            exit 0
        fi
    fi
}

# Function to download and install miniforge
install_miniforge() {
    local platform=$(detect_platform)
    local download_url=$(get_download_url "$platform")
    local installer_name="miniforge_installer"
    
    log_info "Detected platform: $platform"
    log_info "Download URL: $download_url"
    
    # Download installer
    log_info "Downloading miniforge installer..."
    if command -v wget >/dev/null 2>&1; then
        wget -q --show-progress -O "$installer_name" "$download_url"
    elif command -v curl >/dev/null 2>&1; then
        curl -L -o "$installer_name" "$download_url" --progress-bar
    else
        log_error "Neither wget nor curl found. Please install one of them."
        exit 1
    fi
    
    # Make installer executable (for Unix-like systems)
    if [[ "$platform" != Windows-* ]]; then
        chmod +x "$installer_name"
    fi
    
    # Run installer
    log_info "Installing miniforge to $INSTALL_DIR..."
    if [[ "$platform" == Windows-* ]]; then
        # For Windows, we would need different handling
        log_error "Windows installation requires manual execution of the .exe file"
        log_info "Please run: ./$installer_name"
        exit 1
    else
        ./"$installer_name" -b -p "$INSTALL_DIR"
    fi
    
    # Clean up installer
    rm -f "$installer_name"
    
    log_success "Miniforge installed successfully!"
}

# Function to configure conda
configure_conda() {
    local conda_bin="$INSTALL_DIR/bin/conda"
    
    if [ ! -f "$conda_bin" ]; then
        log_error "Conda binary not found at $conda_bin"
        exit 1
    fi
    
    log_info "Configuring conda..."
    
    # Initialize conda for shell integration
    "$conda_bin" init bash
    
    # Set conda-forge as default and only channel if requested
    if [ "$CONDA_FORGE_ONLY" = true ]; then
        log_info "Setting conda-forge as the only channel..."
        "$conda_bin" config --set channels conda-forge
        "$conda_bin" config --set channel_priority strict
    fi
    
    # Disable auto activation of base environment if requested
    if [ "$AUTO_ACTIVATE" = false ]; then
        log_info "Disabling auto-activation of base environment..."
        "$conda_bin" config --set auto_activate_base false
    fi
    
    # Update conda to latest version
    log_info "Updating conda to latest version..."
    "$conda_bin" update -n base -c conda-forge conda -y
    
    log_success "Conda configuration completed!"
}

# Function to update shell profile
update_shell_profile() {
    if [ "$UPDATE_PROFILE" = false ]; then
        return
    fi
    
    local profile_file
    if [ -f "$HOME/.bashrc" ]; then
        profile_file="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        profile_file="$HOME/.bash_profile"
    elif [ -f "$HOME/.profile" ]; then
        profile_file="$HOME/.profile"
    else
        log_warning "No shell profile file found. Skipping profile update."
        return
    fi
    
    log_info "Updating shell profile: $profile_file"
    
    # Add miniforge to PATH if not already present
    local conda_setup="# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup=\"\$('$INSTALL_DIR/bin/conda' 'shell.bash' 'hook' 2> /dev/null)\"
if [ \$? -eq 0 ]; then
    eval \"\$__conda_setup\"
else
    if [ -f \"$INSTALL_DIR/etc/profile.d/conda.sh\" ]; then
        . \"$INSTALL_DIR/etc/profile.d/conda.sh\"
    else
        export PATH=\"$INSTALL_DIR/bin:\$PATH\"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<"
    
    if ! grep -q "conda initialize" "$profile_file"; then
        echo "$conda_setup" >> "$profile_file"
        log_success "Added conda initialization to $profile_file"
    else
        log_info "Conda initialization already exists in $profile_file"
    fi
}

# Function to verify installation
verify_installation() {
    local conda_bin="$INSTALL_DIR/bin/conda"
    
    if [ -f "$conda_bin" ]; then
        log_info "Verifying installation..."
        local version=$("$conda_bin" --version 2>/dev/null || echo "unknown")
        log_success "Installation verified! Conda version: $version"
        
        log_info "Available environments:"
        "$conda_bin" env list
        
        log_info "Conda configuration:"
        "$conda_bin" config --show channels
        
        return 0
    else
        log_error "Installation verification failed!"
        return 1
    fi
}

# Function to show usage instructions
show_usage() {
    cat << EOF
Miniforge Python Installer

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -d, --install-dir DIR   Installation directory (default: $HOME/miniforge3)
    -v, --version VERSION   Miniforge version to install (default: latest)
    --no-conda-forge-only   Don't restrict to conda-forge channel only
    --no-auto-activate      Disable auto-activation of base environment
    --no-profile-update     Don't update shell profile

Examples:
    $0                                    # Install with default settings
    $0 -d /opt/miniforge3                # Install to custom directory
    $0 --no-auto-activate               # Install without auto-activation
    $0 --no-conda-forge-only            # Allow all conda channels

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -d|--install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -v|--version)
                MINIFORGE_VERSION="$2"
                shift 2
                ;;
            --no-conda-forge-only)
                CONDA_FORGE_ONLY=false
                shift
                ;;
            --no-auto-activate)
                AUTO_ACTIVATE=false
                shift
                ;;
            --no-profile-update)
                UPDATE_PROFILE=false
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Main installation function
main() {
    echo "=================================================="
    echo "       Miniforge Python Installer"
    echo "=================================================="
    echo
    
    parse_arguments "$@"
    
    log_info "Starting miniforge installation..."
    log_info "Installation directory: $INSTALL_DIR"
    log_info "Version: $MINIFORGE_VERSION"
    log_info "Conda-forge only: $CONDA_FORGE_ONLY"
    log_info "Auto-activate base: $AUTO_ACTIVATE"
    log_info "Update profile: $UPDATE_PROFILE"
    echo
    
    # Check for existing installation
    check_existing_installation
    
    # Install miniforge
    install_miniforge
    
    # Configure conda
    configure_conda
    
    # Update shell profile
    update_shell_profile
    
    # Verify installation
    if verify_installation; then
        echo
        log_success "Miniforge installation completed successfully!"
        echo
        log_info "To start using conda, either:"
        log_info "1. Restart your terminal, or"
        log_info "2. Run: source ~/.bashrc (or your shell's profile file)"
        echo
        log_info "Quick start commands:"
        log_info "  conda --version                    # Check conda version"
        log_info "  conda create -n myenv python=3.11  # Create new environment"
        log_info "  conda activate myenv               # Activate environment"
        log_info "  conda install numpy pandas         # Install packages"
        echo
    else
        log_error "Installation failed!"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"