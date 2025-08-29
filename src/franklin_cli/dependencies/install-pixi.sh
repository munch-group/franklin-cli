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
VERBOSE=false
QUIET=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color


# Pixi path to add
#PIXI_PATH='export PATH="$HOME/.pixi/bin:$PATH"'
PIXI_COMMENT='# Pixi - Added before conda for priority'

# Function to check if file contains pixi path
has_pixi_path() {
    grep -q '\.pixi/bin' "$1" 2>/dev/null
}

# Function to check if file contains conda initialization
has_conda_init() {
    grep -q '>>> conda initialize >>>' "$1" 2>/dev/null
}

add_pixi_to_shell_config_file() {
    local file=$1
    local temp_file="${file}.tmp"
    
    [ "$VERBOSE" = true ] && echo -e "${YELLOW}Processing $file...${NC}"
    
    # Check if file exists
    if [ ! -f "$file" ]; then
        [ "$VERBOSE" = true ] && echo -e "${YELLOW}File doesn't exist, creating it...${NC}"
        touch "$file" 2>/dev/null || {
            echo -e "${RED}Cannot create $file (permission denied)${NC}"
            return 1
        }
    fi
    
    # Check if file is writable
    if [ ! -w "$file" ]; then
        [ "$VERBOSE" = true ] && echo -e "${YELLOW}File is read-only, attempting to make it writable...${NC}"
        chmod u+w "$file" 2>/dev/null || {
            echo -e "${RED}Cannot modify $file (permission denied). You may need to manually add the following to your $file:${NC}"
            echo -e "${CYAN}$PIXI_COMMENT${NC}"
            echo -e "${CYAN}$PIXI_PATH${NC}"
            return 1
        }
    fi
    
    printf "\n# Adding to path:\nexport PATH=$HOME/.pixi/bin:\$PATH\n" >> "$file"
}

# Function to ensure conda base is not auto-activated
disable_conda_auto_activate() {
    if command -v conda &> /dev/null; then
        [ "$VERBOSE" = true ] && echo -e "${YELLOW}Disabling conda auto_activate_base...${NC}"
        conda config --set auto_activate_base false 2>/dev/null || true
        [ "$VERBOSE" = true ] && echo -e "${GREEN}  ✓ Conda auto_activate_base disabled${NC}"
    fi
}

# Logging functions
log_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}$1${NC}"
    elif [ "$QUIET" != true ]; then
        echo "$1"
    fi
}

log_success() {
    if [ "$QUIET" != true ]; then
        echo -e "${GREEN}$1${NC}"
    fi
}

log_warning() {
    if [ "$QUIET" != true ]; then
        if [ "$VERBOSE" = true ]; then
            echo -e "${YELLOW}Warning: $1${NC}"
        else
            echo -e "${YELLOW}Warning: $1${NC}"
        fi
    fi
}

log_error() {
    # Show errors unless in quiet mode
    if [ "$QUIET" != true ]; then
        echo -e "${RED}[ERROR]${NC} $1"
    fi
}

log_header() {
    if [ "$QUIET" != true ]; then
        echo "$1"
    fi
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

# Function to check if pixi is already installed
check_existing_pixi() {
    if command_exists pixi; then
        local current_version=$(pixi --version 2>/dev/null | awk '{print $2}' || echo "unknown")
        log_warning "Pixi is already installed (version: $current_version)"
        
        if [ "$FORCE_INSTALL" = true ]; then
            log_info "Force flag specified. Proceeding with reinstallation..."
            # Remove existing .pixi folder
            if [ -d "$HOME/.pixi" ]; then
                log_info "Removing existing .pixi folder..."
                rm -rf "$HOME/.pixi" 2>/dev/null || {
                    log_warning "Could not remove .pixi folder completely. Some files may be in use."
                }
            fi
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
    elif [ "$FORCE_INSTALL" = true ] && [ -d "$HOME/.pixi" ]; then
        # Even if pixi command doesn't exist, remove .pixi folder if force flag is set
        log_info "Force flag specified. Removing existing .pixi folder..."
        rm -rf "$HOME/.pixi" 2>/dev/null || {
            log_warning "Could not remove .pixi folder completely. Some files may be in use."
        }
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
    if [ "$QUIET" != true ]; then
        curl -fsSL https://pixi.sh/install.sh | bash -s -- --no-modify-path
    else
        curl -fsSL https://pixi.sh/install.sh  2> /dev/null | bash -s -- --no-modify-path 1> /dev/null > /dev/null 2>&1
    fi

    
    # Process .bash_profile first (it's read first on macOS)
    add_pixi_to_shell_config_file "$HOME/.bash_profile"

    add_pixi_to_shell_config_file "$HOME/.bashrc"

    # Handle zsh configuration
    add_pixi_to_shell_config_file "$HOME/.zshrc"

    # Disable conda auto-activation
    disable_conda_auto_activate

    return 0
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
            # elif install_via_binary; then
            #     install_success=true
            #     update_shell_profile
            # elif install_via_cargo; then
            #     install_success=true
            # else
            #     log_error "All installation methods failed"
            #     exit 1
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
    --verbose              Show detailed logging information
    --quiet                Show only essential colored output
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
            --verbose)
                VERBOSE=true
                shift
                ;;
            --quiet)
                QUIET=true
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

# # Function to show completion message
# show_completion_message() {
#     echo
#     log_success "Operation completed!"
#     echo
#     log_info "Quick start with pixi:"
#     log_info "  pixi --version                     # Check version"
#     log_info "  pixi init my-project              # Initialize new project"
#     log_info "  pixi add python=3.11              # Add Python dependency"
#     log_info "  pixi run python --version         # Run command in environment"
#     log_info "  pixi shell                        # Activate project environment"
#     echo
#     log_info "For more information, visit: https://pixi.sh/"
#     echo
# }

# # Main function
# main() {

#     parse_arguments "$@"

#     # Check if no arguments provided, default to install
#     if [ $# -eq 0 ]; then
#         install_pixi
# #        show_completion_message
#     # else
#     #     parse_arguments "$@"
#     #     if [ "$1" = "install" ] || [ "$1" = "uninstall" ]; then
#     #         show_completion_message
#     #     fi
#     fi
# }

# # Run main function with all arguments
# main "$@"
parse_arguments "$@"
