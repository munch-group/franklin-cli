#!/usr/bin/env python3
"""
Example usage of the Development Environment Installer Python module.

This script demonstrates various ways to use the dev_env_installer module
programmatically in your own Python applications.
"""

import sys
import logging
from pathlib import Path

# Import the installer module
from dependencies import DevEnvironmentInstaller, InstallationStatus, Platform

def basic_usage_example():
    """Example 1: Basic usage - check and install all missing tools"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Create installer instance with default settings
    installer = DevEnvironmentInstaller()
    
    # Check what's already installed
    print("\n🔍 Checking current installation status...")
    status = installer.check_all_tools()
    
    for tool_name, tool_status in status.items():
        tool_display_name = installer.tools[tool_name].display_name
        print(f"  {tool_display_name}: {tool_status.value}")
    
    # Install missing tools
    print("\n🚀 Installing missing tools...")
    results = installer.run_full_installation()
    
    return results

def selective_installation_example():
    """Example 2: Install only specific tools"""
    print("\n" + "=" * 60)
    print("Example 2: Selective Installation")
    print("=" * 60)
    
    # Create installer with custom settings
    installer = DevEnvironmentInstaller(
        force=False,  # Don't reinstall if already present
        continue_on_error=True,  # Continue if one tool fails
        dry_run=False  # Actually install (set to True to test)
    )
    
    # Install only Miniforge and Pixi
    tools_to_install = ["miniforge", "pixi"]
    
    print(f"\n🎯 Installing specific tools: {tools_to_install}")
    results = installer.install_missing_tools(tools_to_install)
    
    # Install Franklin if Pixi was successfully installed
    if results.get("pixi", False):
        print("\n📦 Installing Franklin via Pixi...")
        franklin_success = installer.install_franklin_via_pixi()
        results["franklin"] = franklin_success
    
    return results

def status_check_only_example():
    """Example 3: Only check status without installing"""
    print("\n" + "=" * 60)
    print("Example 3: Status Check Only")
    print("=" * 60)
    
    installer = DevEnvironmentInstaller()
    
    print("\n🔍 Current development environment status:")
    print("-" * 40)
    
    # Check each tool individually with detailed info
    for tool_name, tool_info in installer.tools.items():
        status = installer.check_tool_status(tool_name)
        
        # Get status emoji
        status_emoji = {
            InstallationStatus.INSTALLED: "✅",
            InstallationStatus.NOT_INSTALLED: "❌", 
            InstallationStatus.UNKNOWN: "❓",
            InstallationStatus.FAILED: "💥"
        }.get(status, "❓")
        
        print(f"  {status_emoji} {tool_info.display_name}: {status.value}")
        
        # Show detection details for debugging
        if status == InstallationStatus.INSTALLED:
            for cmd in tool_info.check_commands:
                if installer._command_exists(cmd):
                    print(f"    └── Found via command: {cmd}")
                    break
            else:
                for path in tool_info.check_paths:
                    if installer._path_exists(path):
                        print(f"    └── Found at path: {path}")
                        break
    
    # Special check for Franklin (pixi global package)
    print(f"\n📦 Additional packages:")
    if installer.check_tool_status("pixi") == InstallationStatus.INSTALLED:
        franklin_installed = installer._command_exists("franklin")
        franklin_emoji = "✅" if franklin_installed else "❌"
        print(f"  {franklin_emoji} Franklin (via Pixi): {'installed' if franklin_installed else 'not installed'}")
    else:
        print(f"  ⚠️  Franklin: Cannot check (Pixi not installed)")

def advanced_configuration_example():
    """Example 4: Advanced configuration with custom script directory"""
    print("\n" + "=" * 60)
    print("Example 4: Advanced Configuration")
    print("=" * 60)
    
    # Custom script directory (you would point this to where your scripts are)
    script_directory = Path("./installer_scripts")  # Adjust path as needed
    
    # Create installer with custom configuration
    installer = DevEnvironmentInstaller(
        script_directory=str(script_directory),
        force=True,  # Force reinstall everything
        continue_on_error=True,  # Don't stop on errors
        dry_run=True  # Dry run mode - show what would be done
    )
    
    print(f"\n⚙️  Configuration:")
    print(f"  Script directory: {installer.script_directory}")
    print(f"  Platform: {installer.platform.value}")
    print(f"  Force reinstall: {installer.force}")
    print(f"  Continue on error: {installer.continue_on_error}")
    print(f"  Dry run mode: {installer.dry_run}")
    
    # Show what scripts would be used
    print(f"\n📜 Available installer scripts:")
    for tool_name, tool_info in installer.tools.items():
        script_name = tool_info.installer_scripts.get(installer.platform, "N/A")
        script_path = installer.script_directory / script_name
        exists = script_path.exists() if script_name != "N/A" else False
        exists_emoji = "✅" if exists else "❌"
        print(f"  {exists_emoji} {tool_info.display_name}: {script_name}")
    
    # Run dry installation
    print(f"\n🎭 Dry run installation (no actual changes):")
    results = installer.run_full_installation()
    
    return results

def error_handling_example():
    """Example 5: Error handling and logging"""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling and Custom Logging")
    print("=" * 60)
    
    # Setup custom logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create installer that will likely fail (invalid script directory)
        installer = DevEnvironmentInstaller(
            script_directory="/nonexistent/directory",
            continue_on_error=True
        )
        
        print(f"\n🧪 Testing error handling with invalid script directory...")
        
        # This should handle missing scripts gracefully
        results = installer.install_missing_tools(["miniforge"])
        
        print(f"\n📊 Results despite errors: {results}")
        
    except Exception as e:
        print(f"\n❌ Caught exception: {e}")
        print(f"   This demonstrates the error handling in the module")

def platform_detection_example():
    """Example 6: Platform detection and tool information"""
    print("\n" + "=" * 60)
    print("Example 6: Platform Detection and Tool Information")
    print("=" * 60)
    
    installer = DevEnvironmentInstaller()
    
    print(f"\n🖥️  Platform Information:")
    print(f"  Detected platform: {installer.platform.value}")
    print(f"  Python version: {sys.version}")
    print(f"  Script directory: {installer.script_directory}")
    
    print(f"\n🛠️  Tool Configuration:")
    for tool_name, tool_info in installer.tools.items():
        print(f"\n  📦 {tool_info.display_name}:")
        print(f"    Check commands: {tool_info.check_commands}")
        print(f"    Check paths: {tool_info.check_paths[:3]}...")  # Show first 3 paths
        
        script_name = tool_info.installer_scripts.get(installer.platform)
        print(f"    Installer script: {script_name}")

def main():
    """Run all examples"""
    print("🐍 Development Environment Installer - Python Module Examples")
    print("=" * 60)
    
    try:
        # Example 1: Basic usage
        basic_results = basic_usage_example()
        
        # Example 2: Selective installation 
        selective_results = selective_installation_example()
        
        # Example 3: Status check only
        status_check_only_example()
        
        # Example 4: Advanced configuration
        advanced_results = advanced_configuration_example()
        
        # Example 5: Error handling
        error_handling_example()
        
        # Example 6: Platform detection
        platform_detection_example()
        
        print("\n" + "=" * 60)
        print("🎉 All examples completed!")
        print("=" * 60)
        
        print(f"\n💡 Tips:")
        print(f"  - Use dry_run=True to test without installing")
        print(f"  - Set force=True to reinstall existing tools")
        print(f"  - Use continue_on_error=True for resilient installation")
        print(f"  - Check the logs for detailed installation progress")
        
    except KeyboardInterrupt:
        print(f"\n❌ Examples cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
