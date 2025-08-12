#!/usr/bin/env bash
#
# Franklin Development Environment - Web Installer
# 
# Usage:
#   curl -fsSL https://munch-group.org/installers/install.sh | bash
#   curl -fsSL https://munch-group.org/installers/install.sh | bash -s -- --role educator
#   curl -fsSL https://munch-group.org/installers/install.sh | bash -s -- --help
#
# This script downloads and runs the Franklin installer without requiring
# users to deal with Gatekeeper or other OS-level security warnings.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Logging
log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step() { echo -e "${BLUE}[STEP]${NC} $*"; }

# Configuration
REPO_ORG="${FRANKLIN_REPO_ORG:-munch-group}"
REPO_NAME="${FRANKLIN_REPO_NAME:-franklin}"
REPO_BRANCH="${FRANKLIN_REPO_BRANCH:-main}"
INSTALL_DIR="${FRANKLIN_INSTALL_DIR:-$HOME/.franklin-installer}"

# Determine base URL (GitHub Pages or raw GitHub)
determine_base_url() {
    # Try GitHub Pages first
    if curl -fsSL "https://${REPO_ORG}.github.io/${REPO_NAME}/installers/scripts/master-installer.sh" -o /dev/null 2>&1; then
        echo "https://${REPO_ORG}.github.io/${REPO_NAME}/installers/scripts"
    else
        echo "https://raw.githubusercontent.com/${REPO_ORG}/${REPO_NAME}/${REPO_BRANCH}/src/franklin/dependencies"
    fi
}

# Show banner
show_banner() {
    echo -e "${BOLD}"
    echo "╔═════════════════════════════════════════════════════╗"
    echo "║     Franklin Development Environment Installer      ║"
    echo "╚═════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# Show help
show_help() {
    echo "Usage: curl -fsSL https://munch-group.org/installers/install.sh | bash -s -- [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --role ROLE        Set user role: student, educator, or administrator (default: student)"
    echo "  --skip-miniforge   Skip Miniforge installation"
    echo "  --skip-pixi       Skip Pixi installation"
    echo "  --skip-docker     Skip Docker Desktop installation"
    echo "  --skip-chrome     Skip Chrome installation"
    echo "  --skip-franklin   Skip Franklin installation"
    echo "  --force           Force reinstall all components"
    echo "  --dry-run         Show what would be installed without doing it"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Default installation (student)"
    echo "  curl -fsSL https://munch-group.org/installers/install.sh | bash"
    echo ""
    echo "  # Educator installation"
    echo "  curl -fsSL https://munch-group.org/installers/install.sh | bash -s -- --role educator"
    echo ""
    echo "  # Skip Docker and Chrome"
    echo "  curl -fsSL https://munch-group.org/installers/install.sh | bash -s -- --skip-docker --skip-chrome"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if grep -qi microsoft /proc/version 2>/dev/null; then
            echo "wsl"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Check requirements
check_requirements() {
    local os=$1
    
    # Check for curl
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    # Check for bash
    if [ -z "$BASH_VERSION" ]; then
        log_error "This script requires bash"
        exit 1
    fi
    
    # OS-specific checks
    case "$os" in
        macos)
            if ! command -v sw_vers &> /dev/null; then
                log_warn "Cannot verify macOS version"
            else
                local macos_version=$(sw_vers -productVersion)
                log_info "macOS version: $macos_version"
            fi
            ;;
        linux|wsl)
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                log_info "Linux distribution: $NAME $VERSION"
            fi
            ;;
    esac
}

# Download installer files
download_installers() {
    local temp_dir=$1
    local os=$2
    local base_url=$3
    
    log_step "Downloading installer scripts from: $base_url"
    
    # Core installer
    curl -fsSL "${base_url}/master-installer.sh" \
         -o "$temp_dir/master-installer.sh" || {
        log_error "Failed to download master installer"
        return 1
    }
    
    # Component installers
    local scripts=(
        "install-miniforge.sh"
        "install-pixi.sh"
        "install-docker-desktop.sh"
        "install-chrome.sh"
    )
    
    for script in "${scripts[@]}"; do
        log_info "Downloading $script..."
        curl -fsSL "${base_url}/$script" \
             -o "$temp_dir/$script" || {
            log_warn "Failed to download $script (component may be skipped)"
        }
    done
    
    # Make scripts executable
    chmod +x "$temp_dir"/*.sh 2>/dev/null || true
    
    log_info "Downloaded $(ls -1 "$temp_dir"/*.sh 2>/dev/null | wc -l) installer scripts"
}

# Main installation
main() {
    show_banner
    
    # Parse arguments
    local args=("$@")
    local dry_run=false
    
    # Always add --yes flag to bypass confirmations when called from web installer
    args+=("--yes")
    
    for arg in "$@"; do
        case $arg in
            --help|-h)
                show_help
                exit 0
                ;;
            --dry-run)
                dry_run=true
                ;;
        esac
    done
    
    # Detect OS
    local os=$(detect_os)
    log_info "Detected operating system: ${BOLD}$os${NC}"
    
    if [[ "$os" == "unknown" ]]; then
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    if [[ "$os" == "windows" ]]; then
        log_error "This is a Unix/Linux installer. For Windows, use:"
        echo "  irm https://munch-group.org/install.ps1 | iex"
        exit 1
    fi
    
    # Check requirements
    check_requirements "$os"
    
    # Confirm installation
    if [[ "$dry_run" == "false" ]]; then
        echo ""
        echo -e "${BOLD}This script will install:${NC}"
        echo "  • Miniforge (Python environment manager)"
        echo "  • Pixi (Fast package manager)"
        echo "  • Docker Desktop (Container platform)"
        echo "  • Google Chrome (Web browser)"
        echo "  • Franklin (Development environment)"
        echo ""
        echo "Installation directory: $INSTALL_DIR"
        echo ""
        
        # Check if running in CI/automated environment
        if [ -t 0 ] && [ -z "${CI:-}" ] && [ -z "${FRANKLIN_NONINTERACTIVE:-}" ]; then
            read -p "Continue with installation? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Installation cancelled"
                exit 0
            fi
        else
            log_info "Running in non-interactive mode"
        fi
    fi
    
    # Determine base URL
    local base_url
    base_url=$(determine_base_url)
    log_info "Using base URL: $base_url"
    
    # Create temp directory
    local temp_dir
    temp_dir=$(mktemp -d -t franklin-installer-XXXXXX)
    trap "rm -rf '$temp_dir'" EXIT
    
    log_info "Using temporary directory: $temp_dir"
    
    # Download installers
    download_installers "$temp_dir" "$os" "$base_url"
    
    # Run installation
    if [[ "$dry_run" == "true" ]]; then
        log_info "Dry run - would execute:"
        echo "  cd '$temp_dir'"
        echo "  ./master-installer.sh ${args[*]}"
    else
        log_step "Starting installation..."
        cd "$temp_dir"
        
        # Run master installer with all arguments
        if ./master-installer.sh "${args[@]}"; then
            echo ""
            log_info "${GREEN}${BOLD}Installation completed successfully!${NC}"
            # echo ""
            # echo "Next steps:"
            # echo "  1. Restart your terminal or run: source ~/.bashrc"
            # echo "  2. Verify installation: franklin --version"
            # echo "  3. Get started: franklin --help"
        else
            log_error "Installation failed. Check the output above for errors."
            exit 1
        fi
    fi

    echo "export BASH_SILENCE_DEPRECATION_WARNING=1" >> "$HOME/.bashrc"
}

# Handle errors
trap 'log_error "Installation failed on line $LINENO"' ERR

# Run main with all arguments
main "$@"