#!/usr/bin/swift
//
// macOS Installer UI with Radio Buttons
// Native Swift application for Franklin dependency installer
//

import Cocoa
import Foundation

// MARK: - Dependency Model

enum InstallState {
    case notInstalled
    case installed
    case outdated
    case corrupted
}

enum InstallAction {
    case install
    case reinstall
    case uninstall
    case none
}

class Dependency: NSObject {
    let name: String
    let displayName: String
    let description: String
    var state: InstallState = .notInstalled
    var version: String?
    var latestVersion: String?
    var selectedAction: InstallAction = .none
    var isRequired: Bool = false
    var dependencies: [String] = []
    
    init(name: String, displayName: String, description: String, required: Bool = false) {
        self.name = name
        self.displayName = displayName
        self.description = description
        self.isRequired = required
    }
    
    var canInstall: Bool {
        return state == .notInstalled || state == .corrupted
    }
    
    var canReinstall: Bool {
        return state == .installed || state == .outdated || state == .corrupted
    }
    
    var canUninstall: Bool {
        return state == .installed || state == .outdated || state == .corrupted
    }
}

// MARK: - Dependency Checker

class DependencyChecker {
    
    static func checkDependency(_ name: String) -> InstallState {
        switch name {
        case "miniforge":
            return checkCommand("conda") ? .installed : .notInstalled
        case "pixi":
            return checkCommand("pixi") ? .installed : .notInstalled
        case "docker":
            if FileManager.default.fileExists(atPath: "/Applications/Docker.app") {
                return .installed
            }
            return checkCommand("docker") ? .installed : .notInstalled
        case "chrome":
            return FileManager.default.fileExists(atPath: "/Applications/Google Chrome.app") ? .installed : .notInstalled
        case "franklin":
            return checkCommand("franklin") ? .installed : .notInstalled
        default:
            return .notInstalled
        }
    }
    
    static func checkCommand(_ command: String) -> Bool {
        let task = Process()
        task.launchPath = "/usr/bin/which"
        task.arguments = [command]
        task.standardOutput = Pipe()
        task.standardError = Pipe()
        
        do {
            try task.run()
            task.waitUntilExit()
            return task.terminationStatus == 0
        } catch {
            return false
        }
    }
    
    static func getVersion(for dependency: String) -> String? {
        let task = Process()
        let pipe = Pipe()
        
        switch dependency {
        case "miniforge":
            task.launchPath = "/usr/bin/env"
            task.arguments = ["conda", "--version"]
        case "pixi":
            task.launchPath = "/usr/bin/env"
            task.arguments = ["pixi", "--version"]
        case "docker":
            task.launchPath = "/usr/bin/env"
            task.arguments = ["docker", "--version"]
        case "franklin":
            task.launchPath = "/usr/bin/env"
            task.arguments = ["franklin", "--version"]
        default:
            return nil
        }
        
        task.standardOutput = pipe
        task.standardError = Pipe()
        
        do {
            try task.run()
            task.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
            
            // Parse version from output
            if let output = output {
                let components = output.components(separatedBy: " ")
                for (index, component) in components.enumerated() {
                    if component.contains("version") && index + 1 < components.count {
                        return components[index + 1]
                    }
                }
                // Fallback: last component often contains version
                return components.last
            }
        } catch {
            // Ignore errors
        }
        
        return nil
    }
}

// MARK: - Main Window Controller

class InstallerWindowController: NSWindowController, NSTableViewDelegate, NSTableViewDataSource {
    
    @IBOutlet weak var tableView: NSTableView!
    @IBOutlet weak var installButton: NSButton!
    @IBOutlet weak var statusLabel: NSTextField!
    @IBOutlet weak var progressIndicator: NSProgressIndicator!
    
    var dependencies: [Dependency] = []
    
    override func windowDidLoad() {
        super.windowDidLoad()
        
        setupDependencies()
        checkDependencyStates()
        tableView.reloadData()
        updateInstallButton()
    }
    
    func setupDependencies() {
        dependencies = [
            Dependency(name: "miniforge", displayName: "Miniforge", description: "Python distribution and package manager", required: true),
            Dependency(name: "pixi", displayName: "Pixi", description: "Modern package manager for scientific computing", required: true),
            Dependency(name: "docker", displayName: "Docker Desktop", description: "Container platform for development"),
            Dependency(name: "chrome", displayName: "Google Chrome", description: "Web browser for development"),
            Dependency(name: "franklin", displayName: "Franklin", description: "Educational platform for Jupyter notebooks")
        ]
        
        // Set dependencies
        dependencies[1].dependencies = ["miniforge"] // pixi depends on miniforge
        dependencies[4].dependencies = ["pixi"] // franklin depends on pixi
    }
    
    func checkDependencyStates() {
        for dep in dependencies {
            dep.state = DependencyChecker.checkDependency(dep.name)
            if dep.state == .installed {
                dep.version = DependencyChecker.getVersion(for: dep.name)
            }
            
            // Set default action based on state
            switch dep.state {
            case .notInstalled:
                dep.selectedAction = dep.isRequired ? .install : .none
            case .outdated:
                dep.selectedAction = .none
            default:
                dep.selectedAction = .none
            }
        }
    }
    
    // MARK: - Table View Data Source
    
    func numberOfRows(in tableView: NSTableView) -> Int {
        return dependencies.count
    }
    
    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        let dep = dependencies[row]
        
        if tableColumn?.identifier.rawValue == "ComponentColumn" {
            let cellView = tableView.makeView(withIdentifier: NSUserInterfaceItemIdentifier("ComponentCell"), owner: self) as? ComponentCellView
            cellView?.configure(with: dep, delegate: self)
            return cellView
        }
        
        return nil
    }
    
    func tableView(_ tableView: NSTableView, heightOfRow row: Int) -> CGFloat {
        return 80
    }
    
    // MARK: - Actions
    
    @IBAction func installButtonClicked(_ sender: Any) {
        performInstallation()
    }
    
    @IBAction func refreshButtonClicked(_ sender: Any) {
        checkDependencyStates()
        tableView.reloadData()
        updateInstallButton()
    }
    
    func updateInstallButton() {
        let hasActions = dependencies.contains { $0.selectedAction != .none }
        installButton.isEnabled = hasActions
        
        if hasActions {
            let actionCount = dependencies.filter { $0.selectedAction != .none }.count
            installButton.title = "Execute \(actionCount) Action\(actionCount > 1 ? "s" : "")"
        } else {
            installButton.title = "No Actions Selected"
        }
    }
    
    func performInstallation() {
        installButton.isEnabled = false
        progressIndicator.startAnimation(nil)
        statusLabel.stringValue = "Preparing installation..."
        
        // Build command arguments
        var scriptArgs: [String] = []
        
        for dep in dependencies {
            switch dep.selectedAction {
            case .none:
                scriptArgs.append("--skip-\(dep.name)")
            case .uninstall:
                // Handle uninstall separately
                break
            case .reinstall:
                scriptArgs.append("--force-\(dep.name)")
            case .install:
                // Default action, no skip flag needed
                break
            }
        }
        
        // Execute installation script
        let task = Process()
        task.launchPath = Bundle.main.path(forResource: "master-installer", ofType: "sh")
        task.arguments = scriptArgs
        
        let outputPipe = Pipe()
        task.standardOutput = outputPipe
        task.standardError = outputPipe
        
        outputPipe.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if let output = String(data: data, encoding: .utf8) {
                DispatchQueue.main.async {
                    self.statusLabel.stringValue = output.trimmingCharacters(in: .whitespacesAndNewlines)
                }
            }
        }
        
        task.terminationHandler = { _ in
            DispatchQueue.main.async {
                self.progressIndicator.stopAnimation(nil)
                self.checkDependencyStates()
                self.tableView.reloadData()
                self.updateInstallButton()
                
                if task.terminationStatus == 0 {
                    self.statusLabel.stringValue = "Installation completed successfully!"
                    self.showAlert(title: "Success", message: "All selected actions have been completed successfully.")
                } else {
                    self.statusLabel.stringValue = "Installation failed with errors"
                    self.showAlert(title: "Error", message: "Some actions failed. Please check the log for details.")
                }
                
                self.installButton.isEnabled = true
            }
        }
        
        do {
            try task.run()
        } catch {
            statusLabel.stringValue = "Failed to start installation: \(error)"
            progressIndicator.stopAnimation(nil)
            installButton.isEnabled = true
        }
    }
    
    func showAlert(title: String, message: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = title == "Success" ? .informational : .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}

// MARK: - Component Cell View

class ComponentCellView: NSTableCellView {
    
    @IBOutlet weak var nameLabel: NSTextField!
    @IBOutlet weak var descriptionLabel: NSTextField!
    @IBOutlet weak var statusLabel: NSTextField!
    @IBOutlet weak var versionLabel: NSTextField!
    
    @IBOutlet weak var noneRadioButton: NSButton!
    @IBOutlet weak var installRadioButton: NSButton!
    @IBOutlet weak var reinstallRadioButton: NSButton!
    @IBOutlet weak var uninstallRadioButton: NSButton!
    
    weak var dependency: Dependency?
    weak var delegate: InstallerWindowController?
    
    func configure(with dependency: Dependency, delegate: InstallerWindowController) {
        self.dependency = dependency
        self.delegate = delegate
        
        nameLabel.stringValue = dependency.displayName
        descriptionLabel.stringValue = dependency.description
        
        // Set status
        switch dependency.state {
        case .notInstalled:
            statusLabel.stringValue = "Not Installed"
            statusLabel.textColor = .systemRed
        case .installed:
            statusLabel.stringValue = "Installed"
            statusLabel.textColor = .systemGreen
        case .outdated:
            statusLabel.stringValue = "Outdated"
            statusLabel.textColor = .systemOrange
        case .corrupted:
            statusLabel.stringValue = "Corrupted"
            statusLabel.textColor = .systemRed
        }
        
        // Set version
        if let version = dependency.version {
            versionLabel.stringValue = "v\(version)"
            versionLabel.isHidden = false
        } else {
            versionLabel.isHidden = true
        }
        
        // Enable/disable radio buttons based on state
        noneRadioButton.isEnabled = true
        installRadioButton.isEnabled = dependency.canInstall
        reinstallRadioButton.isEnabled = dependency.canReinstall
        uninstallRadioButton.isEnabled = dependency.canUninstall && !dependency.isRequired
        
        // Set selected action
        switch dependency.selectedAction {
        case .none:
            noneRadioButton.state = .on
        case .install:
            installRadioButton.state = .on
        case .reinstall:
            reinstallRadioButton.state = .on
        case .uninstall:
            uninstallRadioButton.state = .on
        }
        
        // Set button titles with hints
        if !installRadioButton.isEnabled {
            installRadioButton.title = "Install (N/A)"
        } else {
            installRadioButton.title = "Install"
        }
        
        if !reinstallRadioButton.isEnabled {
            reinstallRadioButton.title = "Reinstall (N/A)"
        } else {
            reinstallRadioButton.title = "Reinstall"
        }
        
        if !uninstallRadioButton.isEnabled {
            if dependency.isRequired {
                uninstallRadioButton.title = "Uninstall (Required)"
            } else {
                uninstallRadioButton.title = "Uninstall (N/A)"
            }
        } else {
            uninstallRadioButton.title = "Uninstall"
        }
    }
    
    @IBAction func radioButtonChanged(_ sender: NSButton) {
        guard let dependency = dependency else { return }
        
        switch sender {
        case noneRadioButton:
            dependency.selectedAction = .none
        case installRadioButton:
            dependency.selectedAction = .install
        case reinstallRadioButton:
            dependency.selectedAction = .reinstall
        case uninstallRadioButton:
            dependency.selectedAction = .uninstall
        default:
            break
        }
        
        delegate?.updateInstallButton()
    }
}

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    
    var windowController: InstallerWindowController?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Create and show main window
        let storyboard = NSStoryboard(name: "Main", bundle: nil)
        windowController = storyboard.instantiateController(withIdentifier: "InstallerWindowController") as? InstallerWindowController
        windowController?.showWindow(self)
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

// MARK: - Main

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()