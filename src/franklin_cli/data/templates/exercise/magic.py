"""Franklin magic commands for Jupyter notebooks in exercise containers.

This module provides IPython magic commands for managing packages and
dependencies within Franklin exercise containers using Pixi.
"""

from IPython.core.magic import register_line_magic
import subprocess
import shutil
import pyperclip
import webbrowser
from functools import wraps
import sys
import os
import tempfile


def crash_report(func):
    """Decorator to handle exceptions and provide crash reporting."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            url = 'https://github.com/munch-group/franklin-cli/issues'
            print(f"Error while running magic: {e}", file=sys.stderr)
            print("Please report this by creating an issue at:")
            print(url)
            print("The error description has been copied to your clipboard "
                   "for you to paste into the issue description.")
            pyperclip.copy(f"Exception occurred while running magic: {e}")
            webbrowser.open(url, new=1)
        return ret
    return wrapper


# Script to install Pixi if not already present
install_pixi_script = f'''
WORKSPACE_FOLDER="{os.getcwd()}"
ENVIRONMENT="prod"
export PIXI_HOME=/home/vscode
export PIXI_PROJECT_MANIFEST="$WORKSPACE_FOLDER/pixi.toml"
curl -fsSL https://pixi.sh/install.sh | bash
'''


@crash_report
def load_ipython_extension(ipython):
    """Load the Franklin magic extension.
    
    This function is called when `%load_ext magic` is run in IPython.
    """
    
    @register_line_magic
    def franklin(line):
        """Franklin magic command for package installation.
        
        Usage:
            %franklin <package-name> [<package-name> ...]
        
        Examples:
            %franklin numpy pandas
            %franklin scikit-learn matplotlib
        """
        
        # Only run in exercise repositories (with Dockerfile)
        if not os.path.exists('Dockerfile'):
            return
        
        packages = line.strip().split()
        if not packages:
            print("Usage: %franklin <package-name> <package-name> ...")
            return
        
        # Check if Pixi is installed
        pixi_exe = os.environ.get('PIXI_EXE', '/home/vscode/.pixi/bin/pixi')
        if not os.path.exists(pixi_exe):
            print("Installing pixi...")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as script_file:
                script_file.write(install_pixi_script)
                script_path = script_file.name
            
            try:
                cmd = ["bash", script_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode:
                    print(f"Error installing pixi:\n{result.stderr}")
                    return
            finally:
                os.unlink(script_path)
        
        # Install packages using Pixi
        print(f"Installing: {', '.join(packages)}")
        cmd = [pixi_exe, "add", "--feature", "exercise", "--platform", "linux-64"] + packages
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"Successfully installed: {', '.join(packages)}")
        except subprocess.CalledProcessError as e:
            print(f"Error installing {', '.join(packages)}:\n{e.stderr}")
    
    
    @register_line_magic
    def pixi_install(line):
        """Alternative magic command for Pixi package installation.
        
        Usage:
            %pixi_install <package-name> [<package-name> ...]
        
        This is an alias for %franklin for compatibility.
        """
        franklin(line)