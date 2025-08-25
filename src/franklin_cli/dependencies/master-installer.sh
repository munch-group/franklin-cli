#!/bin/bash

# Master Development Environment Installer for macOS/Linux
# Orchestrates the installation of a complete development environment
# by running multiple installer scripts in sequence, then configures pixi with franklin.
# Compatible with Bash 3.0+ and Bash 4.0+

set -euo pipefail

# Configuration
SCRIPT_DIR="$(dirname "$0")"
# SKIP_MINIFORGE=false # Removed - using Pixi for Python management
SKIP_PIXI=false
SKIP_DOCKER=false
SKIP_CHROME=false
SKIP_FRANKLIN=false
FORCE_INSTALL=false
# FORCE_MINIFORGE=false # Removed - using Pixi
FORCE_PIXI=false
FORCE_DOCKER=false
FORCE_CHROME=false
FORCE_FRANKLIN=false
CONTINUE_ON_ERROR=false
DRY_RUN=false
YES_FLAG=false  # Auto-accept all confirmations
USER_ROLE="student"  # Default role: student, educator, or administrator

# Script execution tracking (using simple counters and variables)
EXECUTION_LOG_COUNT=0
FAILED_INSTALLATIONS_COUNT=0
SUCCESSFUL_INSTALLATIONS_COUNT=0
RESTART_REQUIRED=0

# Installer script names
# MINIFORGE_SCRIPT="install-miniforge.sh" # Removed
PIXI_SCRIPT="install-pixi.sh"
DOCKER_SCRIPT="install-docker-desktop.sh"
CHROME_SCRIPT="install-chrome.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Bash 3/4 compatible array management functions
add_to_execution_log() {
    EXECUTION_LOG_COUNT=$((EXECUTION_LOG_COUNT + 1))
    eval "EXECUTION_LOG_$EXECUTION_LOG_COUNT=\"\$1\""
}

add_to_failed_installations() {
    FAILED_INSTALLATIONS_COUNT=$((FAILED_INSTALLATIONS_COUNT + 1))
    eval "FAILED_INSTALLATIONS_$FAILED_INSTALLATIONS_COUNT=\"\$1\""
}

add_to_successful_installations() {
    SUCCESSFUL_INSTALLATIONS_COUNT=$((SUCCESSFUL_INSTALLATIONS_COUNT + 1))
    eval "SUCCESSFUL_INSTALLATIONS_$SUCCESSFUL_INSTALLATIONS_COUNT=\"\$1\""
}

get_execution_log() {
    local i=1
    while [ $i -le $EXECUTION_LOG_COUNT ]; do
        eval "echo \"\$EXECUTION_LOG_$i\""
        i=$((i + 1))
    done
}

get_failed_installations() {
    local i=1
    while [ $i -le $FAILED_INSTALLATIONS_COUNT ]; do
        eval "echo \"\$FAILED_INSTALLATIONS_$i\""
        i=$((i + 1))
    done
}

get_successful_installations() {
    local i=1
    while [ $i -le $SUCCESSFUL_INSTALLATIONS_COUNT ]; do
        eval "echo \"\$SUCCESSFUL_INSTALLATIONS_$i\""
        i=$((i + 1))
    done
}

# Logging functions
log_info() {
    local timestamp=$(date '+%H:%M:%S')
    echo -e "${NC}[$timestamp] [INFO]${NC} $1"
    add_to_execution_log "[$timestamp] [INFO] $1"
}

log_success() {
    local timestamp=$(date '+%H:%M:%S')
    echo -e "${BLUE}[$timestamp] [SUCCESS]${NC} $1"
    add_to_execution_log "[$timestamp] [SUCCESS] $1"
}

log_warning() {
    local timestamp=$(date '+%H:%M:%S')
    echo -e "${YELLOW}[$timestamp] [WARNING]${NC} $1"
    add_to_execution_log "[$timestamp] [WARNING] $1"
}

log_error() {
    local timestamp=$(date '+%H:%M:%S')
    echo -e "${RED}[$timestamp] [ERROR]${NC} $1"
    add_to_execution_log "[$timestamp] [ERROR] $1"
}

log_header() {
    echo
    # echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

log_step_header() {
    echo
    echo -e "${BLUE}>>> STEP $1: $2${NC}"
    echo -e "${BLUE}--------------------------------------------------${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if script exists
script_exists() {
    local script_name="$1"
    local script_path="$SCRIPT_DIR/$script_name"
    
    if [ -f "$script_path" ]; then
        echo "$script_path"
        return 0
    else
        log_warning "Script not found: $script_path"
        return 1
    fi
}

# Function to execute installer script with error handling
invoke_installer_script() {
    local name="$1"
    local script_path="$2"
    shift 2
    
    log_info "Starting $name installation..."
    
    # Make script executable
    chmod +x "$script_path"
    
    # Build argument list (bash 3 compatible)
    local args=""
    if [ "$FORCE_INSTALL" = true ]; then
        args="--force"
    fi
    
    # Add additional arguments
    while [ $# -gt 0 ]; do
        if [ -n "$args" ]; then
            args="$args $1"
        else
            args="$1"
        fi
        shift
    done
    
    # Execute the script
    if [ -n "$args" ]; then
        if $script_path $args; then
            log_info "$name installation completed successfully"
            add_to_successful_installations "$name"
            return 0
        else
            log_error "$name installation failed"
            add_to_failed_installations "$name"
            return 1
        fi
    else
        if $script_path; then
            log_info "$name installation completed successfully"
            add_to_successful_installations "$name"
            return 0
        else
            log_error "$name installation failed"
            add_to_failed_installations "$name"
            return 1
        fi
    fi
}

# Miniforge installation removed - Pixi handles Python environment management
# install_miniforge() {
#     log_step_header "1" "Installing Miniforge Python Distribution"
#     
#     if [ "$SKIP_MINIFORGE" = true ]; then
#         log_info "Skipping miniforge installation (--skip-miniforge flag)"
#         return 0
#     fi
#     
#     # Check if already installed
#     if command_exists conda && [ "$FORCE_INSTALL" = false ] && [ "$FORCE_MINIFORGE" = false ]; then
#         log_info "Miniforge/Conda already installed. Use --force or --force-miniforge to reinstall."
#         add_to_successful_installations "Miniforge"
#         return 0
#     fi
#     
#     local script_path
#     if script_path=$(script_exists "$MINIFORGE_SCRIPT"); then
#         if invoke_installer_script "Miniforge" "$script_path" "install"; then
#             return 0
#         elif [ "$CONTINUE_ON_ERROR" = true ]; then
#             log_warning "Miniforge installation failed. Continuing..."
#             return 1
#         else
#             log_error "Miniforge installation failed. Stopping."
#             exit 1
#         fi
#     else
#         if [ "$CONTINUE_ON_ERROR" = true ]; then
#             log_warning "Miniforge installer script not found. Continuing..."
#             add_to_failed_installations "Miniforge"
#             return 1
#         else
#             log_error "Miniforge installer script not found: $MINIFORGE_SCRIPT"
#             exit 1
#         fi
#     fi
# }

# Function to install pixi
install_pixi() {
    log_step_header "1" "Installing Pixi Package Manager"
    
    if [ "$SKIP_PIXI" = true ]; then
        log_info "Skipping pixi installation (--skip-pixi flag)"
        return 0
    fi
    
    # Check if already installed
    if command_exists pixi && [ "$FORCE_INSTALL" = false ] && [ "$FORCE_PIXI" = false ]; then
        log_info "Pixi already installed. Use --force or --force-pixi to reinstall."
        add_to_successful_installations "Pixi"
        return 0
    fi
    
    local script_path
    if script_path=$(script_exists "$PIXI_SCRIPT"); then
        if invoke_installer_script "Pixi" "$script_path" "install"; then
            return 0
        elif [ "$CONTINUE_ON_ERROR" = true ]; then
            log_warning "Pixi installation failed. Continuing..."
            return 1
        else
            log_error "Pixi installation failed. Stopping."
            exit 1
        fi
    else
        if [ "$CONTINUE_ON_ERROR" = true ]; then
            log_warning "Pixi installer script not found. Continuing..."
            add_to_failed_installations "Pixi"
            return 1
        else
            log_error "Pixi installer script not found: $PIXI_SCRIPT"
            exit 1
        fi
    fi
}

# Function to install Docker Desktop
install_docker_desktop() {
    log_step_header "2" "Installing Docker Desktop"
    
    if [ "$SKIP_DOCKER" = true ]; then
        log_info "Skipping Docker Desktop installation (--skip-docker flag)"
        return 0
    fi
    
    # Check OS - Docker Desktop installer is macOS-only
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_warning "Docker Desktop installer is for macOS only."
        log_info "For Linux, please install Docker Engine manually:"
        log_info "  Ubuntu/Debian: https://docs.docker.com/engine/install/ubuntu/"
        log_info "  RHEL/CentOS: https://docs.docker.com/engine/install/centos/"
        log_info "  Other: https://docs.docker.com/engine/install/"
        
        # Check if Docker is already installed via other means
        if command_exists docker; then
            log_info "Docker is already installed via system package manager"
            add_to_successful_installations "Docker (system)"
            return 0
        else
            log_info "Skipping Docker Desktop installation on Linux"
            return 0
        fi
    fi
    
    # Check if already installed
    if command_exists docker && [ "$FORCE_INSTALL" = false ] && [ "$FORCE_DOCKER" = false ]; then
        log_info "Docker already installed. Use --force or --force-docker to reinstall."
        add_to_successful_installations "Docker Desktop"
        return 0
    fi
    
    local script_path
    if script_path=$(script_exists "$DOCKER_SCRIPT"); then
        # Docker installation may require sudo - provide clear prompt
        log_info "Docker Desktop installation may require administrator privileges"
        # if invoke_installer_script "Docker Desktop" "$script_path" "install"; then
        if invoke_installer_script "Docker Desktop" "$script_path"; then
            return 0
        elif [ "$CONTINUE_ON_ERROR" = true ]; then
            log_warning "Docker Desktop installation failed. Continuing..."
            return 1
        else
            log_error "Docker Desktop installation failed. Stopping."
            exit 1
        fi
    else
        if [ "$CONTINUE_ON_ERROR" = true ]; then
            log_warning "Docker Desktop installer script not found. Continuing..."
            add_to_failed_installations "Docker Desktop"
            return 1
        else
            log_error "Docker Desktop installer script not found: $DOCKER_SCRIPT"
            exit 1
        fi
    fi
}

# Function to install Chrome
install_chrome() {
    log_step_header "3" "Installing Google Chrome"
    
    if [ "$SKIP_CHROME" = true ]; then
        log_info "Skipping Chrome installation (--skip-chrome flag)"
        return 0
    fi
    
    # Check OS first
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_warning "Chrome installer script is for macOS only."
        log_info "For Linux, please install Chrome manually:"
        log_info "  Ubuntu/Debian: sudo apt install google-chrome-stable"
        log_info "  Fedora: sudo dnf install google-chrome-stable"
        log_info "  Or download from: https://www.google.com/chrome/"
        
        # Check if Chrome is already installed via system package manager
        if command_exists google-chrome || command_exists google-chrome-stable; then
            log_info "Chrome is already installed via system package manager"
            add_to_successful_installations "Chrome (system)"
            return 0
        else
            log_info "Skipping Chrome installation on Linux"
            return 0
        fi
    fi
    
    # Check if already installed (macOS specific check)
    if [ -d "/Applications/Google Chrome.app" ] && [ "$FORCE_INSTALL" = false ] && [ "$FORCE_CHROME" = false ]; then
        log_info "Chrome already installed. Use --force or --force-chrome to reinstall."
        add_to_successful_installations "Chrome"
        return 0
    fi
    
    local script_path
    if script_path=$(script_exists "$CHROME_SCRIPT"); then
        if invoke_installer_script "Chrome" "$script_path"; then
            return 0
        elif [ "$CONTINUE_ON_ERROR" = true ]; then
            log_warning "Chrome installation failed. Continuing..."
            return 1
        else
            log_error "Chrome installation failed. Stopping."
            exit 1
        fi
    else
        if [ "$CONTINUE_ON_ERROR" = true ]; then
            log_warning "Chrome installer script not found. Continuing..."
            add_to_failed_installations "Chrome"
            return 1
        else
            log_error "Chrome installer script not found: $CHROME_SCRIPT"
            exit 1
        fi
    fi
}

# Function to install Franklin via pixi global
install_franklin() {
    log_step_header "4" "Installing Franklin via Pixi Global"
    
    if [ "$SKIP_FRANKLIN" = true ]; then
        log_info "Skipping Franklin installation (--skip-franklin flag)"
        return 0
    fi
    
    # Check if pixi is available
    if ! command_exists pixi; then
        log_error "Pixi is not available. Cannot install Franklin."
        if [ "$CONTINUE_ON_ERROR" = true ]; then
            add_to_failed_installations "Franklin"
            return 1
        else
            log_error "Pixi is required to install Franklin"
            exit 1
        fi
    fi
    
    log_info "Installing Franklin using pixi global..."
    
    # Refresh PATH to ensure pixi is available
    # Note: We avoid sourcing shell configs as they may hang on interactive elements
    log_info "Checking for pixi in common locations..."
    
    # Add common pixi installation paths to PATH if not already present (bash 3 compatible)
    for p in "$HOME/.pixi/bin" "/opt/pixi/bin" "/usr/local/bin"; do
        if [ -d "$p" ]; then
            case ":$PATH:" in
                *":$p:"*) ;;
                *) export PATH="$p:$PATH"
                   log_info "Added $p to PATH" ;;
            esac
        fi
    done
    
    # Verify pixi is available
    if command_exists pixi; then
        log_info "Pixi found at: $(which pixi)"
    else
        log_warning "Pixi not found in PATH after refresh"
    fi
    
    # # Determine which package to install based on user role
    # log_info "User role: $USER_ROLE"
    # local package_name="franklin"
    # case "$USER_ROLE" in
    #     educator)
    #         package_name="franklin-educator"
    #         log_info "Installing Franklin Educator package for educator role"
    #         ;;
    #     administrator|admin)
    #         package_name="franklin-admin"
    #         log_info "Installing Franklin Administrator package for admin role"
    #         ;;
    #     student|*)
    #         package_name="franklin"
    #         log_info "Installing standard Franklin package for student role"
    #         ;;
    # esac
    # log_info "Package to install: $package_name"
    
    # Determine which package to install based on user role
    log_info "User role: $USER_ROLE"
    local package_name="franklin"
    case "$USER_ROLE" in
        educator)
            command="pixi global install -c munch-group -c conda-forge python git franklin-cli pysteps 2>&1 && pixi global add --environment franklin-cli franklin-educator 2>&1"
            log_info "Installing Franklin Educator package for educator role"
            ;;
        administrator|admin)
            command="pixi global install -c munch-group -c conda-forge python git franklin-cli pysteps 2>&1 && pixi global add --environment franklin-cli franklin-educator franklin-admin 2>&1"
            log_info "Installing Franklin Administrator package for admin role"
            ;;
        student|*)
            command="pixi global install -c munch-group -c conda-forge python git franklin-cli pysteps 2>&1"
            log_info "Installing standard Franklin package for student role"
            ;;
    esac
    log_info "Package to install: $package_name"


    # Run pixi global install command
    log_info "Executing: $command"
    # Capture the output and error for debugging
    local install_output
    local install_exit_code
    # Run the command and capture output
    install_output=$(eval "$command")
    install_exit_code=$?





    # # Run pixi global install command
    # log_info "Executing: pixi global install -c munch-group -c conda-forge python git $package_name"
    # # Capture the output and error for debugging
    # local install_output
    # local install_exit_code
    # # Run the command and capture output
    # install_output=$(pixi global install -c munch-group -c conda-forge python git "$package_name" 2>&1)
    # install_exit_code=$?
    

    if [ $install_exit_code -eq 0 ]; then
        log_info "$package_name installed successfully via pixi global"
        add_to_successful_installations "Franklin ($USER_ROLE)"
        return 0
    else
        log_error "$package_name installation failed with exit code: $install_exit_code"
        log_error "Error output:"
        echo "$install_output" | while IFS= read -r line; do
            log_error "  $line"
        done
        
        # Check for common issues
        if echo "$install_output" | grep -q "not found"; then
            log_error "Package '$package_name' not found in the specified channels"
            log_info "Try updating pixi: pixi self-update"
        elif echo "$install_output" | grep -q "permission"; then
            log_error "Permission issue detected. Try running with appropriate permissions"
        elif echo "$install_output" | grep -q "network\|connection"; then
            log_error "Network issue detected. Check your internet connection"
        fi
        
        add_to_failed_installations "Franklin"
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check bash version
    local bash_major_version
    bash_major_version=$(echo "$BASH_VERSION" | cut -d. -f1)
    if [ "$bash_major_version" -lt 3 ]; then
        log_error "Bash 3.0 or higher is required. Current version: $BASH_VERSION"
        exit 1
    fi
    log_info "Bash version: $BASH_VERSION [OK]"
    
    # Check operating system
    local os_type
    os_type=$(uname -s)
    case "$os_type" in
        Darwin*)
            log_info "Operating System: macOS [OK]"
            ;;
        Linux*)
            log_info "Operating System: Linux [OK]"
            ;;
        *)
            log_warning "Operating System: $os_type (may not be fully supported)"
            ;;
    esac
    
    # Check script directory
    if [ ! -d "$SCRIPT_DIR" ]; then
        log_error "Script directory not found: $SCRIPT_DIR"
        exit 1
    fi
    log_info "Script directory: $SCRIPT_DIR [OK]"
    
    # Check for available installer scripts (bash 3/4 compatible)
    local available_scripts=""
    local missing_scripts=""
    
    # Check each script individually
    # Miniforge script check removed - using Pixi
    available_scripts=""
    missing_scripts=""
    
    if [ -f "$SCRIPT_DIR/$PIXI_SCRIPT" ]; then
        if [ -n "$available_scripts" ]; then
            available_scripts="$available_scripts, pixi"
        else
            available_scripts="pixi"
        fi
    else
        if [ -n "$missing_scripts" ]; then
            missing_scripts="$missing_scripts, pixi"
        else
            missing_scripts="pixi"
        fi
    fi
    
    if [ -f "$SCRIPT_DIR/$DOCKER_SCRIPT" ]; then
        if [ -n "$available_scripts" ]; then
            available_scripts="$available_scripts, docker"
        else
            available_scripts="docker"
        fi
    else
        if [ -n "$missing_scripts" ]; then
            missing_scripts="$missing_scripts, docker"
        else
            missing_scripts="docker"
        fi
    fi
    
    if [ -f "$SCRIPT_DIR/$CHROME_SCRIPT" ]; then
        if [ -n "$available_scripts" ]; then
            available_scripts="$available_scripts, chrome"
        else
            available_scripts="chrome"
        fi
    else
        if [ -n "$missing_scripts" ]; then
            missing_scripts="$missing_scripts, chrome"
        else
            missing_scripts="chrome"
        fi
    fi
    
    if [ -n "$available_scripts" ]; then
        log_info "Available installer scripts: $available_scripts"
    fi
    if [ -n "$missing_scripts" ]; then
        log_warning "Missing installer scripts: $missing_scripts"
    fi
}

# Function to show installation plan
show_installation_plan() {
    echo "Installation Plan:"
    
    # Miniforge removed - Pixi handles Python environments
    if [ "$SKIP_PIXI" = false ]; then echo "  1. Pixi Package Manager"; fi
    if [ "$SKIP_DOCKER" = false ]; then echo "  2. Docker Desktop"; fi
    if [ "$SKIP_CHROME" = false ]; then echo "  3. Google Chrome"; fi
    if [ "$SKIP_FRANKLIN" = false ]; then echo "  4. Franklin (via pixi global)"; fi
    
    echo
    log_info "Script directory: $SCRIPT_DIR"
    log_info "Force reinstall: $FORCE_INSTALL"
    log_info "Continue on error: $CONTINUE_ON_ERROR"
    
    if [ "$YES_FLAG" = true ]; then
        log_info "Bypassing confirmation"
    else
        echo
        read -p "Do you want to proceed with the installation? (y/N): " -n 1 -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi


        # read -r reply
        # case "$reply" in
        #     [Yy]|[Yy][Ee][Ss])
        #         ;;
        #     *)
        #         log_info "Installation cancelled by user."
        #         exit 0
        #         ;;
        # esac
    fi
}

# Function to show installation summary
show_installation_summary() {
    # log_header "Installation Summary"
    # echo -e "${BLUE}Summary:${NC}"    
    
    if [ $SUCCESSFUL_INSTALLATIONS_COUNT -gt 0 ]; then
        echo -e "${BLUE}Installation status:${NC}" 
        get_successful_installations | while read -r item; do
            echo -e "  ${BLUE}[OK] $item${NC}"
        done
    fi
    
    if [ $FAILED_INSTALLATIONS_COUNT -gt 0 ]; then
        log_warning "Failed installations:"
        get_failed_installations | while read -r item; do
            echo -e "  ${RED} $item${NC}"
        done
    fi
    
    echo
    if [ $FAILED_INSTALLATIONS_COUNT -eq 0 ]; then
        log_info "All installations completed successfully!"
        log_info "Your development environment is ready to use."
    else
        log_warning "Some installations failed. Check the error messages above."
        log_info "You may need to install the failed components manually."
    fi

    # # Show next steps
    # echo
    # log_info "NEXT STEPS:"
    # log_info "1. Restart your terminal session to refresh environment variables"
    # log_info "2. Verify installations:"
    # log_info "   - conda --version"
    # log_info "   - pixi --version"
    # log_info "   - docker --version"
    # log_info "   - franklin --version (if installed)"
    # log_info "3. Check that Franklin is available via 'franklin' command"
}

# Function to save installation log
save_installation_log() {
    local log_file="/tmp/master-installer-$(date '+%Y%m%d-%H%M%S').log"
    
    get_execution_log > "$log_file"
    log_info "Installation log saved to: $log_file"
}

# Function to show usage
show_usage() {
    cat << 'EOF'
Master Development Environment Installer for macOS/Linux

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -d, --script-dir DIR    Directory containing installer scripts (default: script directory)
    # --skip-miniforge        Removed - using Pixi for Python management
    --skip-pixi            Skip pixi installation
    --skip-docker          Skip Docker Desktop installation
    --skip-chrome          Skip Chrome installation
    --skip-franklin        Skip Franklin installation
    -f, --force            Force installation even if components already exist
    # --force-miniforge      Removed - using Pixi
    --force-pixi          Force reinstall Pixi only
    --force-docker        Force reinstall Docker Desktop only
    --force-chrome        Force reinstall Chrome only
    --force-franklin      Force reinstall Franklin only
    -c, --continue-on-error Continue with remaining installations if one fails
    -y, --yes              Bypass all user confirmations (auto-accept)
    --role ROLE           Set user role: student, educator, or administrator (default: student)

Examples:
    ./master-installer.sh                          # Install all components
    ./master-installer.sh --skip-docker --skip-chrome  # Skip Docker and Chrome
    ./master-installer.sh --force                  # Force reinstall all components
    ./master-installer.sh --force-docker          # Force reinstall Docker only
    ./master-installer.sh --continue-on-error      # Continue even if some fail
    ./master-installer.sh -d /path/to/scripts      # Use scripts from different directory
    ./master-installer.sh --role educator          # Install educator version
    ./master-installer.sh --role administrator     # Install admin version

Required Scripts:
    # - install-miniforge.sh (Removed - using Pixi)
    - install-pixi.sh
    - install-docker-desktop.sh
    - install-chrome.sh

EOF
}

# Function to parse command line arguments
parse_arguments() {
    while [ $# -gt 0 ]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -d|--script-dir)
                if [ -n "$2" ]; then
                    SCRIPT_DIR="$2"
                    shift 2
                else
                    log_error "Option --script-dir requires an argument"
                    exit 1
                fi
                ;;
            # --skip-miniforge) # Removed - using Pixi
            #     SKIP_MINIFORGE=true
            #     shift
            #     ;;
            --skip-pixi)
                SKIP_PIXI=true
                shift
                ;;
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            --skip-chrome)
                SKIP_CHROME=true
                shift
                ;;
            --skip-franklin)
                SKIP_FRANKLIN=true
                shift
                ;;
            -f|--force)
                FORCE_INSTALL=true
                shift
                ;;
            # --force-miniforge) # Removed - using Pixi
            #     FORCE_MINIFORGE=true
            #     shift
            #     ;;
            --force-pixi)
                FORCE_PIXI=true
                shift
                ;;
            --force-docker)
                FORCE_DOCKER=true
                shift
                ;;
            --force-chrome)
                FORCE_CHROME=true
                shift
                ;;
            --force-franklin)
                FORCE_FRANKLIN=true
                shift
                ;;
            -c|--continue-on-error)
                CONTINUE_ON_ERROR=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -y|--yes)
                YES_FLAG=true
                shift
                ;;
            --role)
                if [ -z "$2" ]; then
                    log_error "Role argument requires a value"
                    show_usage
                    exit 1
                fi
                USER_ROLE="$2"
                case "$USER_ROLE" in
                    student|educator|administrator|admin)
                        shift 2
                        ;;
                    *)
                        log_error "Invalid role: $USER_ROLE. Must be student, educator, or administrator"
                        show_usage
                        exit 1
                        ;;
                esac
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Main installation orchestrator
start_master_installation() {
    local start_time
    start_time=$(date +%s)
    
    # # Show header
    # log_header "Franklin setup for $USER_ROLE on Mac"

    log_info "Starting installation process at $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Check prerequisites
    check_prerequisites
    
    # Show installation plan
    show_installation_plan

    if [ "$DRY_RUN" = true ]; then 
        exit 0
    fi

    if [ "$YES_FLAG" = false ]; then 
        read -p "Continue? (type Y for Yes or N for No) " -n 1 -r
        echo    # (optional) move to a new line
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi

    # Execute installations in sequence
    # install_miniforge # Removed - using Pixi
    install_pixi
    install_docker_desktop
    if [ $? -eq 0 ] && [[ "$OSTYPE" == "darwin"* ]]; then
        RESTART_REQUIRED=1
    fi
    install_chrome
    install_franklin
    
    # Show summary
    show_installation_summary
    
    # Save log
    save_installation_log
    
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local hours=$((duration / 3600))
    local minutes=$(((duration % 3600) / 60))
    local seconds=$((duration % 60))
    
    log_info "Total installation time: $(printf "%02d:%02d:%02d" $hours $minutes $seconds)"
    
    # Determine exit code
    if [ $FAILED_INSTALLATIONS_COUNT -eq 0 ]; then
        if [ "$DRY_RUN" = false ]; then
            log_info "Master installation completed successfully!"
            if [ $RESTART_REQUIRED -eq 1 ]; then
                echo ""
                echo -e "  ${RED}You must now restart your computer to activate installed components${NC}"
                echo ""
            fi
        fi

        exit 0
    elif [ "$CONTINUE_ON_ERROR" = true ]; then
        log_warning "Master installation completed with some failures."
        exit 2
    else
        log_error "Master installation failed."
        exit 1
    fi
}

# Script entry point
echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN}  Installing for $USER_ROLE {NC}"
echo -e "${GREEN}=======================================================${NC}"

# Parse command line arguments
parse_arguments "$@"

# Validate script directory
if [ ! -d "$SCRIPT_DIR" ]; then
    log_error "Script directory does not exist: $SCRIPT_DIR"
    exit 1
fi

# Start the installation process
start_master_installation
