#!/bin/bash

# Pixi Package Manager - Install/Uninstall Script
# Cross-platform installer/uninstaller for pixi package manager
# Supports Linux, macOS, and Windows (via WSL/Git Bash)

set -euo pipefail

# Configuration
PIXI_VERSION="latest"
INSTALL_DIR="$HOME/.pixi"
BINARY_DIR="$HOME/.local/bin"
FORCE_INSTALL=false
INSTALL_METHOD="auto"  # auto, curl, cargo, binary

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_header() {
    echo -e "${CYAN}$1${NC}"
}

# Function to detect operating system and architecture
detect_platform() {
    local os_type=$(uname -s)
    local arch=$(uname -m)
    
    case "$os_type" in
        Linux*)
            case "$arch" in
                x86_64) echo "linux-64" ;;
                aarch64) echo "linux-aarch64" ;;
                *) log_error "Unsupported Linux architecture: $arch"; exit 1 ;;
            esac
            ;;
        Darwin*)
            case "$arch" in
                x86_64) echo "osx-64" ;;
                arm64) echo "osx-arm64" ;;
                *) log_error "Unsupported macOS architecture: $arch"; exit 1 ;;
            esac
            ;;
        CYGWIN*|MINGW*|MSYS*)
            case "$arch" in
                x86_64) echo "win-64" ;;
                *) log_error "Unsupported Windows architecture: $arch"; exit 1 ;;
            esac
            ;;
        *)
            log_error "Unsupported operating system: $os_type"
            exit 1
            ;;
    esac
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get latest pixi version
get_latest_version() {
    if command_exists curl; then
        # curl -s https://api.github.com/repos/prefix-dev/pixi/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/'
        curl -fsSL https://pixi.sh/install.sh | sh
    elif command_exists wget; then
        # wget -qO- https://api.github.com/repos/prefix-dev/pixi/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/'
        wget -qO- https://pixi.sh/install.sh | sh        
    else
        log_error "Neither curl nor wget found. Cannot determine latest version."
        exit 1
    fi
}

# Function to check if pixi is already installed
check_existing_pixi() {
    if command_exists pixi; then
        local current_version=$(pixi --version 2>/dev/null | awk '{print $2}' || echo "unknown")
        log_warning "Pixi is already installed (version: $current_version)"
        
        if [ "$FORCE_INSTALL" = true ]; then
            log_info "Force flag specified. Proceeding with reinstallation..."
            return 0
        fi
        
        read -p "Do you want to reinstall pixi? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            return 0
        else
            log_info "Installation cancelled."
            exit 0
        fi
    fi
    return 0
}

# Function to install pixi via official installer
install_via_curl() {
    log_info "Installing pixi via official installer..."
    
    if ! command_exists curl; then
        log_error "curl is required for this installation method"
        return 1
    fi
    
    # Download and run official installer
    curl -fsSL https://pixi.sh/install.sh | bash
    
    # Source the shell configuration to update PATH
    if [ -f "$HOME/.bashrc" ]; then
        source "$HOME/.bashrc" 2>/dev/null || true
    fi
    
    return 0
}

# Function to install pixi via cargo
install_via_cargo() {
    log_info "Installing pixi via cargo..."
    
    if ! command_exists cargo; then
        log_error "Rust/Cargo is required for this installation method"
        log_info "Install Rust from: https://rustup.rs/"
        return 1
    fi
    
    cargo install pixi
    return 0
}

# Function to install pixi via direct binary download
install_via_binary() {
    log_info "Installing pixi via direct binary download..."
    
    local platform=$(detect_platform)
    local version=$PIXI_VERSION
    
    if [ "$version" = "latest" ]; then
        version=$(get_latest_version)
        log_info "Latest version: $version"
    fi
    
    # Construct download URL
    local base_url="https://github.com/prefix-dev/pixi/releases/download"
    local filename
    
    case "$platform" in
        linux-64) filename="pixi-x86_64-unknown-linux-musl.tar.bz2" ;;
        linux-aarch64) filename="pixi-aarch64-unknown-linux-musl.tar.bz2" ;;
        osx-64) filename="pixi-x86_64-apple-darwin.tar.bz2" ;;
        osx-arm64) filename="pixi-aarch64-apple-darwin.tar.bz2" ;;
        win-64) filename="pixi-x86_64-pc-windows-msvc.zip" ;;
        *) log_error "No binary available for platform: $platform"; return 1 ;;
    esac
    
    local download_url="$base_url/v$version/$filename"
    local temp_dir=$(mktemp -d)
    local download_file="$temp_dir/$filename"
    
    log_info "Downloading from: $download_url"
    
    # Download the binary
    if command_exists curl; then
        curl -L -o "$download_file" "$download_url"
    elif command_exists wget; then
        wget -O "$download_file" "$download_url"
    else
        log_error "Neither curl nor wget found"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Create binary directory if it doesn't exist
    mkdir -p "$BINARY_DIR"
    
    # Extract and install
    cd "$temp_dir"
    if [[ "$filename" == *.tar.bz2 ]]; then
        tar -xjf "$filename"
        # Find the pixi binary in extracted contents
        local pixi_binary=$(find . -name "pixi" -type f | head -1)
        if [ -n "$pixi_binary" ]; then
            chmod +x "$pixi_binary"
            cp "$pixi_binary" "$BINARY_DIR/pixi"
        else
            log_error "Could not find pixi binary in extracted archive"
            rm -rf "$temp_dir"
            return 1
        fi
    elif [[ "$filename" == *.zip ]]; then
        if command_exists unzip; then
            unzip -q "$filename"
            local pixi_binary=$(find . -name "pixi.exe" -o -name "pixi" | head -1)
            if [ -n "$pixi_binary" ]; then
                chmod +x "$pixi_binary"
                cp "$pixi_binary" "$BINARY_DIR/pixi"
            else
                log_error "Could not find pixi binary in extracted archive"
                rm -rf "$temp_dir"
                return 1
            fi
        else
            log_error "unzip command not found"
            rm -rf "$temp_dir"
            return 1
        fi
    fi
    
    # Clean up
    rm -rf "$temp_dir"
    
    log_success "Binary installed to $BINARY_DIR/pixi"
    return 0
}

# Function to add pixi to PATH
update_shell_profile() {
    local shell_profile=""
    
    # Determine shell profile file
    if [ -n "${BASH_VERSION:-}" ]; then
        if [ -f "$HOME/.bashrc" ]; then
            shell_profile="$HOME/.bashrc"
        elif [ -f "$HOME/.bash_profile" ]; then
            shell_profile="$HOME/.bash_profile"
        fi
    elif [ -n "${ZSH_VERSION:-}" ]; then
        shell_profile="$HOME/.zshrc"
    elif [ -f "$HOME/.profile" ]; then
        shell_profile="$HOME/.profile"
    fi
    
    if [ -z "$shell_profile" ]; then
        log_warning "Could not determine shell profile file"
        log_info "Please manually add $BINARY_DIR to your PATH"
        return 0
    fi
    
    # Check if PATH update is needed
    if ! echo "$PATH" | grep -q "$BINARY_DIR"; then
        log_info "Adding $BINARY_DIR to PATH in $shell_profile"
        
        echo "" >> "$shell_profile"
        echo "# Added by pixi installer" >> "$shell_profile"
        echo "export PATH=\"$BINARY_DIR:\$PATH\"" >> "$shell_profile"
        
        # Update PATH for current session
        export PATH="$BINARY_DIR:$PATH"
        
        log_success "PATH updated in $shell_profile"
    else
        log_info "PATH already contains $BINARY_DIR"
    fi
}

# Function to install pixi
install_pixi() {
    log_header "Installing Pixi Package Manager"
    
    check_existing_pixi
    
    local install_success=false
    
    case "$INSTALL_METHOD" in
        curl)
            install_via_curl && install_success=true
            ;;
        cargo)
            install_via_cargo && install_success=true
            ;;
        binary)
            install_via_binary && install_success=true
            update_shell_profile
            ;;
        auto)
            # Try methods in order of preference
            if install_via_curl; then
                install_success=true
            elif install_via_binary; then
                install_success=true
                update_shell_profile
            elif install_via_cargo; then
                install_success=true
            else
                log_error "All installation methods failed"
                exit 1
            fi
            ;;
        *)
            log_error "Unknown installation method: $INSTALL_METHOD"
            exit 1
            ;;
    esac
    
    if [ "$install_success" = true ]; then
        verify_installation
    else
        log_error "Installation failed"
        exit 1
    fi
}

# Function to uninstall pixi
uninstall_pixi() {
    log_header "Uninstalling Pixi Package Manager"
    
    if ! command_exists pixi; then
        log_warning "Pixi is not installed or not in PATH"
        return 0
    fi
    
    local pixi_path=$(which pixi)
    log_info "Found pixi at: $pixi_path"
    
    # Confirm uninstallation
    read -p "Are you sure you want to uninstall pixi? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Uninstallation cancelled."
        return 0
    fi
    
    # Remove pixi binary
    if [ -f "$pixi_path" ]; then
        log_info "Removing pixi binary..."
        rm -f "$pixi_path"
        log_success "Pixi binary removed"
    fi
    
    # Remove pixi directory if it exists
    if [ -d "$INSTALL_DIR" ]; then
        read -p "Remove pixi cache and configuration directory ($INSTALL_DIR)? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing pixi directory..."
            rm -rf "$INSTALL_DIR"
            log_success "Pixi directory removed"
        fi
    fi
    
    # Clean up shell profile (optional)
    read -p "Remove pixi PATH entries from shell profile? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup_shell_profile
    fi
    
    log_success "Pixi uninstallation completed!"
}

# Function to clean up shell profile
cleanup_shell_profile() {
    local profiles=("$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc" "$HOME/.profile")
    
    for profile in "${profiles[@]}"; do
        if [ -f "$profile" ]; then
            # Remove pixi-related PATH entries
            if grep -q "# Added by pixi installer" "$profile"; then
                log_info "Cleaning up $profile"
                
                # Create a temporary file without pixi entries
                grep -v "# Added by pixi installer" "$profile" | \
                grep -v "export PATH.*\.local/bin.*PATH" > "$profile.tmp" || true
                
                mv "$profile.tmp" "$profile"
                log_success "Cleaned up $profile"
            fi
        fi
    done
}

# Function to verify installation
verify_installation() {
    log_info "Verifying pixi installation..."
    
    # Refresh PATH for current session
    if [ -d "$BINARY_DIR" ]; then
        export PATH="$BINARY_DIR:$PATH"
    fi
    
    if command_exists pixi; then
        local version=$(pixi --version 2>/dev/null | awk '{print $2}' || echo "unknown")
        log_success "Pixi installed successfully! Version: $version"
        
        log_info "Installation location: $(which pixi)"
        log_info "Testing pixi functionality..."
        
        # Test basic pixi commands
        if pixi --help >/dev/null 2>&1; then
            log_success "Pixi is working correctly!"
        else
            log_warning "Pixi installed but may not be working correctly"
        fi
        
        return 0
    else
        log_error "Pixi installation verification failed!"
        log_info "Try restarting your shell or running: source ~/.bashrc"
        return 1
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Pixi Package Manager - Install/Uninstall Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    install     Install pixi package manager (default)
    uninstall   Uninstall pixi package manager
    help        Show this help message

Options:
    -v, --version VERSION   Specific version to install (default: latest)
    -d, --dir DIR          Installation directory (default: $HOME/.pixi)
    -b, --bin-dir DIR      Binary directory (default: $HOME/.local/bin)
    -m, --method METHOD    Installation method: auto, curl, cargo, binary (default: auto)
    -f, --force            Force installation even if already installed
    -h, --help             Show this help message

Examples:
    $0                                    # Install pixi with default settings
    $0 install --version 0.7.0          # Install specific version
    $0 install --method cargo            # Install via cargo
    $0 install --force                   # Force reinstall
    $0 uninstall                         # Uninstall pixi

Installation Methods:
    auto    - Try official installer, then binary, then cargo
    curl    - Use official pixi installer script
    cargo   - Install via Rust cargo (requires Rust)
    binary  - Download and install binary directly

EOF
}

# Function to parse command line arguments
parse_arguments() {
    local command="install"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            install|uninstall|help)
                command="$1"
                shift
                ;;
            -v|--version)
                PIXI_VERSION="$2"
                shift 2
                ;;
            -d|--dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -b|--bin-dir)
                BINARY_DIR="$2"
                shift 2
                ;;
            -m|--method)
                INSTALL_METHOD="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_INSTALL=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    case "$command" in
        install)
            install_pixi
            ;;
        uninstall)
            uninstall_pixi
            ;;
        help)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Function to show completion message
show_completion_message() {
    echo
    log_success "Operation completed!"
    echo
    log_info "Quick start with pixi:"
    log_info "  pixi --version                     # Check version"
    log_info "  pixi init my-project              # Initialize new project"
    log_info "  pixi add python=3.11              # Add Python dependency"
    log_info "  pixi run python --version         # Run command in environment"
    log_info "  pixi shell                        # Activate project environment"
    echo
    log_info "For more information, visit: https://pixi.sh/"
    echo
}

# Main function
main() {
    echo "=================================================="
    echo "       Pixi Package Manager Installer"
    echo "=================================================="
    echo
    
    # Check if no arguments provided, default to install
    if [ $# -eq 0 ]; then
        install_pixi
        show_completion_message
    else
        parse_arguments "$@"
        if [ "$1" = "install" ] || [ "$1" = "uninstall" ]; then
            show_completion_message
        fi
    fi
}

# Run main function with all arguments
main "$@"