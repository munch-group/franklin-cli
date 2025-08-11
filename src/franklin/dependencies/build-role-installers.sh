#!/usr/bin/env bash
#
# Build role-specific installer scripts
# This script creates simplified installers with hardcoded roles
#
# Usage: ./build-role-installers.sh
#
# Creates:
#   - student-install.sh / student-install.ps1
#   - educator-install.sh / educator-install.ps1
#   - administrator-install.sh / administrator-install.ps1
#   - admin-install.sh / admin-install.ps1 (alias)

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building role-specific installer scripts...${NC}"

# Function to create bash installer with hardcoded role
create_bash_installer() {
    local role=$1
    local output_file=$2
    
    echo -e "${GREEN}Creating $output_file...${NC}"
    
    cat > "$output_file" << 'EOF'
#!/usr/bin/env bash
#
# Franklin Development Environment - ROLE_PLACEHOLDER Installation
# 
# Usage:
#   curl -fsSL https://munch-group.org/installers/ROLE_PLACEHOLDER-install.sh | bash
#
# This is a simplified installer with role pre-configured.
# For advanced options, use the main installer with parameters.

set -euo pipefail

# Hardcoded role
HARDCODED_ROLE="ROLE_PLACEHOLDER"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Show banner
echo -e "${BOLD}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║     Franklin ROLE_TITLE Installation                    ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${GREEN}[INFO]${NC} Installing Franklin for role: ${BOLD}ROLE_TITLE${NC}"
echo ""

# Download and run the main installer with hardcoded role
INSTALLER_URL="${FRANKLIN_INSTALLER_URL:-https://INSTALLER_BASE_URL/install.sh}"

# Check if we can download the installer
if ! command -v curl &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} curl is required but not installed" >&2
    exit 1
fi

# Pass all arguments plus the hardcoded role
# Users can still override with additional options like --skip-docker
echo -e "${BLUE}[INFO]${NC} Downloading main installer from: $INSTALLER_URL"
curl -fsSL "$INSTALLER_URL" | bash -s -- --role "$HARDCODED_ROLE" "$@"
EOF
    
    # Replace placeholders
    local role_title
    case "$role" in
        student)
            role_title="Student"
            ;;
        educator)
            role_title="Educator"
            ;;
        administrator|admin)
            role_title="Administrator"
            ;;
    esac
    
    sed -i.bak \
        -e "s/ROLE_PLACEHOLDER/$role/g" \
        -e "s/ROLE_TITLE/$role_title/g" \
        -e "s|INSTALLER_BASE_URL|munch-group.org/franklin/installers|g" \
        "$output_file"
    rm -f "$output_file.bak"
    
    chmod +x "$output_file"
}

# Function to create PowerShell installer with hardcoded role
create_powershell_installer() {
    local role=$1
    local output_file=$2
    
    echo -e "${GREEN}Creating $output_file...${NC}"
    
    cat > "$output_file" << 'EOF'
#Requires -Version 5.0
<#
.SYNOPSIS
    Franklin Development Environment - ROLE_TITLE Installation

.DESCRIPTION
    Simplified installer with pre-configured role.
    For advanced options, use the main installer with parameters.

.EXAMPLE
    # Simple installation
    irm https://munch-group.org/installers/ROLE_PLACEHOLDER-install.ps1 | iex

.NOTES
    Role: ROLE_TITLE
    This script automatically sets -Role ROLE_PLACEHOLDER
#>

[CmdletBinding()]
param(
    [switch]$SkipMiniforge,
    [switch]$SkipPixi,
    [switch]$SkipDocker,
    [switch]$SkipChrome,
    [switch]$SkipFranklin,
    [switch]$Force,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Hardcoded role
$HardcodedRole = 'ROLE_PLACEHOLDER'

# Banner
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Franklin ROLE_TITLE Installation                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "[INFO] Installing Franklin for role: $HardcodedRole" -ForegroundColor Green
Write-Host ""

# Help
if ($Help) {
    Write-Host @"
Franklin ROLE_TITLE Installer

USAGE:
    irm https://munch-group.org/installers/ROLE_PLACEHOLDER-install.ps1 | iex

PARAMETERS:
    -SkipMiniforge  Skip Miniforge installation
    -SkipPixi       Skip Pixi installation
    -SkipDocker     Skip Docker Desktop installation
    -SkipChrome     Skip Chrome installation
    -SkipFranklin   Skip Franklin installation
    -Force          Force reinstall all components
    -DryRun         Show what would be installed
    -Help           Show this help message

NOTE: Role is pre-set to ROLE_TITLE
For different roles, use the main installer.
"@
    exit 0
}

# Download and execute main installer with hardcoded role
$InstallerUrl = if ($env:FRANKLIN_INSTALLER_URL) { 
    $env:FRANKLIN_INSTALLER_URL 
} else { 
    "https://INSTALLER_BASE_URL/install.ps1" 
}

Write-Host "[INFO] Downloading main installer from: $InstallerUrl" -ForegroundColor Blue

try {
    # Build parameters for main installer
    $mainParams = @{
        Role = $HardcodedRole
    }
    
    # Pass through other parameters
    if ($SkipMiniforge) { $mainParams['SkipMiniforge'] = $true }
    if ($SkipPixi) { $mainParams['SkipPixi'] = $true }
    if ($SkipDocker) { $mainParams['SkipDocker'] = $true }
    if ($SkipChrome) { $mainParams['SkipChrome'] = $true }
    if ($SkipFranklin) { $mainParams['SkipFranklin'] = $true }
    if ($Force) { $mainParams['Force'] = $true }
    if ($DryRun) { $mainParams['DryRun'] = $true }
    
    # Download and execute
    $scriptContent = Invoke-RestMethod -Uri $InstallerUrl -UseBasicParsing
    $scriptBlock = [scriptblock]::Create($scriptContent)
    & $scriptBlock @mainParams
}
catch {
    Write-Host "[ERROR] Failed to download or execute installer: $_" -ForegroundColor Red
    exit 1
}
EOF
    
    # Replace placeholders
    local role_title
    case "$role" in
        student)
            role_title="Student"
            ;;
        educator)
            role_title="Educator"
            ;;
        administrator|admin)
            role_title="Administrator"
            ;;
    esac
    
    sed -i.bak \
        -e "s/ROLE_PLACEHOLDER/$role/g" \
        -e "s/ROLE_TITLE/$role_title/g" \
        -e "s|INSTALLER_BASE_URL|munch-group.org/franklin/installers|g" \
        "$output_file"
    rm -f "$output_file.bak"
}

# Create output directory if it doesn't exist
OUTPUT_DIR="${1:-$SCRIPT_DIR}"
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}Output directory: $OUTPUT_DIR${NC}"

# Create role-specific installers
create_bash_installer "student" "$OUTPUT_DIR/student-install.sh"
create_bash_installer "educator" "$OUTPUT_DIR/educator-install.sh"
create_bash_installer "administrator" "$OUTPUT_DIR/administrator-install.sh"
create_bash_installer "admin" "$OUTPUT_DIR/admin-install.sh"  # Alias

create_powershell_installer "student" "$OUTPUT_DIR/student-install.ps1"
create_powershell_installer "educator" "$OUTPUT_DIR/educator-install.ps1"
create_powershell_installer "administrator" "$OUTPUT_DIR/administrator-install.ps1"
create_powershell_installer "admin" "$OUTPUT_DIR/admin-install.ps1"  # Alias

# Create a simple redirect HTML for each role
create_role_html() {
    local role=$1
    local role_title=$2
    local output_file="$OUTPUT_DIR/${role}-install.html"
    
    echo -e "${GREEN}Creating $output_file...${NC}"
    
    cat > "$output_file" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Franklin ${role_title} Installation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        .command {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            user-select: all;
            cursor: pointer;
            margin: 10px 0;
        }
        .platform { margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Franklin ${role_title} Installation</h1>
        
        <div class="platform">
            <h3>macOS/Linux</h3>
            <div class="command" onclick="navigator.clipboard.writeText(this.textContent.trim())">
                curl -fsSL https://munch-group.org/franklin/installers/${role}-install.sh | bash
            </div>
        </div>
        
        <div class="platform">
            <h3>Windows PowerShell</h3>
            <div class="command" onclick="navigator.clipboard.writeText(this.textContent.trim())">
                irm https://munch-group.org/franklin/installers/${role}-install.ps1 | iex
            </div>
        </div>
        
        <p><small>Click on command to copy to clipboard</small></p>
    </div>
</body>
</html>
EOF
}

create_role_html "student" "Student"
create_role_html "educator" "Educator"
create_role_html "administrator" "Administrator"
create_role_html "admin" "Administrator"

echo ""
echo -e "${GREEN}✓ Role-specific installers created successfully!${NC}"
echo ""
echo "Created files:"
ls -la "$OUTPUT_DIR"/*-install.* | awk '{print "  • " $NF}'
echo ""
echo -e "${YELLOW}Usage examples:${NC}"
echo ""
echo "Student:"
echo "  curl -fsSL https://munch-group.org/franklin/installers/student-install.sh | bash"
echo "  irm https://munch-group.org/franklin/installers/student-install.ps1 | iex"
echo ""
echo "Educator:"
echo "  curl -fsSL https://munch-group.org/franklin/installers/educator-install.sh | bash"
echo "  irm https://munch-group.org/franklin/installers/educator-install.ps1 | iex"
echo ""
echo "Administrator:"
echo "  curl -fsSL https://munch-group.org/franklin/installers/administrator-install.sh | bash"
echo "  irm https://munch-group.org/franklin/installers/administrator-install.ps1 | iex"