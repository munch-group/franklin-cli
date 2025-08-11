#!/usr/bin/env python3
"""
Cross-platform GUI installer for Franklin Development Environment
"""

import os
import sys
import subprocess
import platform
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from typing import Dict, List, Tuple
from dependency_checker import DependencyChecker, InstallState

class FranklinInstallerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Franklin Development Environment Installer")
        self.root.geometry("800x600")
        
        # Initialize dependency checker
        self.checker = DependencyChecker()
        self.dependencies = self.checker.check_all()
        
        # Track selected actions for each dependency
        self.selected_actions = {}
        
        # Track user role
        self.user_role = tk.StringVar(value="student")
        
        # Create UI
        self.create_widgets()
        
        # Refresh states
        self.refresh_states()
    
    def create_widgets(self):
        """Create the main UI widgets"""
        # Title
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(title_frame, text="Franklin Development Environment Installer", 
                                font=("Arial", 16, "bold"))
        title_label.pack()
        
        # Main content frame with scrollbar
        content_frame = ttk.Frame(self.root, padding="10")
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(content_frame)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Dependencies section
        deps_label = ttk.Label(scrollable_frame, text="Dependencies:", font=("Arial", 12, "bold"))
        deps_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Create dependency widgets
        self.dep_widgets = {}
        for i, (name, info) in enumerate(self.dependencies.items(), start=1):
            self.create_dependency_widget(scrollable_frame, i, name, info)
        
        # User role selection
        role_frame = ttk.LabelFrame(scrollable_frame, text="User Role", padding="10")
        role_frame.grid(row=len(self.dependencies) + 1, column=0, columnspan=5, 
                       sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(role_frame, text="Select your role:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        ttk.Radiobutton(role_frame, text="Student (standard Franklin)", 
                       variable=self.user_role, value="student").grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(role_frame, text="Educator (franklin-educator)", 
                       variable=self.user_role, value="educator").grid(row=0, column=2, sticky=tk.W, padx=10)
        ttk.Radiobutton(role_frame, text="Administrator (franklin-admin)", 
                       variable=self.user_role, value="administrator").grid(row=0, column=3, sticky=tk.W)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Button frame
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        # Buttons
        self.refresh_button = ttk.Button(button_frame, text="Refresh", command=self.refresh_states)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        self.install_button = ttk.Button(button_frame, text="Install", command=self.run_installation)
        self.install_button.pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E))
    
    def create_dependency_widget(self, parent, row, name, info):
        """Create widget for a single dependency"""
        # Name label
        name_label = ttk.Label(parent, text=info.display_name, font=("Arial", 10, "bold"))
        name_label.grid(row=row, column=0, sticky=tk.W, padx=(20, 10), pady=2)
        
        # Status label
        status_text = f"{info.state.value}"
        if info.version:
            status_text += f" (v{info.version})"
        status_label = ttk.Label(parent, text=status_text)
        status_label.grid(row=row, column=1, sticky=tk.W, padx=10, pady=2)
        
        # Radio buttons for actions
        action_var = tk.StringVar(value="none")
        self.selected_actions[name] = action_var
        
        ttk.Radiobutton(parent, text="None", variable=action_var, value="none"
                       ).grid(row=row, column=2, padx=5, pady=2)
        
        install_radio = ttk.Radiobutton(parent, text="Install", variable=action_var, value="install")
        install_radio.grid(row=row, column=3, padx=5, pady=2)
        
        reinstall_radio = ttk.Radiobutton(parent, text="Reinstall", variable=action_var, value="reinstall")
        reinstall_radio.grid(row=row, column=4, padx=5, pady=2)
        
        uninstall_radio = ttk.Radiobutton(parent, text="Uninstall", variable=action_var, value="uninstall")
        uninstall_radio.grid(row=row, column=5, padx=5, pady=2)
        
        # Enable/disable based on state
        if info.state == InstallState.NOT_INSTALLED:
            reinstall_radio.config(state="disabled")
            uninstall_radio.config(state="disabled")
            action_var.set("install")
        elif info.state == InstallState.INSTALLED:
            install_radio.config(state="disabled")
        elif info.state == InstallState.OUTDATED:
            action_var.set("reinstall")
        elif info.state == InstallState.CORRUPTED:
            action_var.set("reinstall")
        
        # Store widgets for later updates
        self.dep_widgets[name] = {
            'status': status_label,
            'install': install_radio,
            'reinstall': reinstall_radio,
            'uninstall': uninstall_radio,
            'action': action_var
        }
    
    def refresh_states(self):
        """Refresh dependency states"""
        self.status_var.set("Refreshing...")
        self.root.update()
        
        # Re-check all dependencies
        self.dependencies = self.checker.check_all()
        
        # Update UI
        for name, info in self.dependencies.items():
            if name in self.dep_widgets:
                widgets = self.dep_widgets[name]
                
                # Update status label
                status_text = f"{info.state.value}"
                if info.version:
                    status_text += f" (v{info.version})"
                widgets['status'].config(text=status_text)
                
                # Update radio button states
                if info.state == InstallState.NOT_INSTALLED:
                    widgets['install'].config(state="normal")
                    widgets['reinstall'].config(state="disabled")
                    widgets['uninstall'].config(state="disabled")
                    if widgets['action'].get() in ['reinstall', 'uninstall']:
                        widgets['action'].set("install")
                elif info.state == InstallState.INSTALLED:
                    widgets['install'].config(state="disabled")
                    widgets['reinstall'].config(state="normal")
                    widgets['uninstall'].config(state="normal")
                    if widgets['action'].get() == 'install':
                        widgets['action'].set("none")
                elif info.state in [InstallState.OUTDATED, InstallState.CORRUPTED]:
                    widgets['install'].config(state="disabled")
                    widgets['reinstall'].config(state="normal")
                    widgets['uninstall'].config(state="normal")
                    if widgets['action'].get() == 'install':
                        widgets['action'].set("reinstall")
        
        self.status_var.set("Ready")
    
    def run_installation(self):
        """Run the installation based on selected options"""
        # Build command arguments
        script_args = []
        actions_summary = []
        
        for name, action_var in self.selected_actions.items():
            action = action_var.get()
            info = self.dependencies[name]
            
            if action == "none":
                script_args.extend([f"--skip-{name}"])
            elif action == "install":
                actions_summary.append(f"Install {info.display_name}")
            elif action == "reinstall":
                script_args.extend([f"--force-{name}"])
                actions_summary.append(f"Reinstall {info.display_name}")
            elif action == "uninstall":
                # Handle uninstall separately
                actions_summary.append(f"Uninstall {info.display_name}")
        
        # Add user role
        role = self.user_role.get()
        script_args.extend(["--role", role])
        
        # Add role to Franklin action if applicable
        franklin_action = self.selected_actions.get('franklin', tk.StringVar()).get()
        if franklin_action in ['install', 'reinstall']:
            for i, action in enumerate(actions_summary):
                if 'Franklin' in action:
                    actions_summary[i] = f"{action} ({role})"
        
        if not actions_summary:
            messagebox.showinfo("No Actions", "No installation actions selected.")
            return
        
        # Confirm actions
        message = "The following actions will be performed:\n\n"
        message += "\n".join(f"• {action}" for action in actions_summary)
        message += "\n\nDo you want to proceed?"
        
        if not messagebox.askyesno("Confirm Actions", message):
            return
        
        # Find the installer script
        script_dir = Path(__file__).parent
        if platform.system() == "Windows":
            script_path = script_dir / "Master-Installer.ps1"
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)] + script_args
        else:
            script_path = script_dir / "master-installer.sh"
            cmd = ["bash", str(script_path)] + script_args
        
        if not script_path.exists():
            messagebox.showerror("Error", f"Installer script not found: {script_path}")
            return
        
        # Create progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Installation Progress")
        progress_window.geometry("600x400")
        
        text_widget = scrolledtext.ScrolledText(progress_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Run installation
        self.status_var.set("Installing...")
        self.install_button.config(state="disabled")
        
        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output line by line
            for line in process.stdout:
                text_widget.insert(tk.END, line)
                text_widget.see(tk.END)
                progress_window.update()
            
            process.wait()
            
            if process.returncode == 0:
                messagebox.showinfo("Complete", "Installation completed successfully!")
            else:
                messagebox.showwarning("Warning", f"Installation completed with errors (exit code: {process.returncode})")
        
        except Exception as e:
            messagebox.showerror("Error", f"Installation failed: {str(e)}")
        
        finally:
            self.install_button.config(state="normal")
            self.status_var.set("Ready")
            progress_window.destroy()
            self.refresh_states()
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    app = FranklinInstallerGUI()
    app.run()

if __name__ == "__main__":
    main()