# Test script to validate PowerShell syntax
param()

Write-Host "Testing PowerShell syntax validation..."

try {
    # Attempt to parse the Master-Installer.ps1 script
    $scriptPath = Join-Path $PSScriptRoot "Master-Installer.ps1"
    
    if (Test-Path $scriptPath) {
        $scriptContent = Get-Content $scriptPath -Raw
        $errors = $null
        $tokens = $null
        $ast = [System.Management.Automation.Language.Parser]::ParseInput($scriptContent, [ref]$tokens, [ref]$errors)
        
        if ($errors.Count -gt 0) {
            Write-Host "Syntax errors found:" -ForegroundColor Red
            foreach ($error in $errors) {
                Write-Host "  Line $($error.Extent.StartLineNumber): $($error.Message)" -ForegroundColor Yellow
                Write-Host "    Near: $($error.Extent.Text)" -ForegroundColor Gray
            }
            exit 1
        } else {
            Write-Host "No syntax errors found!" -ForegroundColor Green
            
            # Check for specific patterns that might cause issues
            $lines = $scriptContent -split "`n"
            for ($i = 0; $i -lt $lines.Count; $i++) {
                $line = $lines[$i]
                $lineNum = $i + 1
                
                # Check for problematic patterns
                if ($line -match '^\s*}\s*$' -and $i -gt 0) {
                    $prevLine = $lines[$i - 1]
                    if ($prevLine -match '^\s*}\s*$') {
                        Write-Host "Warning: Double closing brace at line $lineNum" -ForegroundColor Yellow
                    }
                }
            }
        }
    } else {
        Write-Host "Master-Installer.ps1 not found!" -ForegroundColor Red
    }
} catch {
    Write-Host "Error parsing script: $_" -ForegroundColor Red
    exit 1
}