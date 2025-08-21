# Quick Start: Signing Installers

## What You Need

### macOS ($99/year)
1. Apple Developer Account
2. Developer ID Certificate
3. App-specific password

### Windows ($200-700/year)
- **Option A**: Standard Certificate ($200-400) - Has initial warnings
- **Option B**: EV Certificate ($300-700) - No warnings from day one

## Setup Commands

### macOS

```bash
# 1. Set environment variables
export MACOS_CERTIFICATE_NAME="Developer ID Application: Your Name (TEAMID)"
export APPLE_ID="your.email@example.com"
export APPLE_ID_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export TEAM_ID="XXXXXXXXXX"

# 2. Build and sign
cd src/franklin_cli/dependencies
./build_native_installers.sh

# 3. Verify
codesign --verify --verbose dist/Franklin-Installer-macOS.dmg
```

### Windows

```bash
# 1. Convert certificate to base64 (for GitHub Actions)
base64 -i certificate.pfx -o cert_base64.txt

# 2. Set environment variables
export WINDOWS_CERT_BASE64=$(cat cert_base64.txt)
export WINDOWS_CERT_PASSWORD="your_password"

# 3. Build and sign (on macOS with cross-compile)
brew install makensis osslsigncode
cd src/franklin_cli/dependencies
./build_native_installers.sh

# 4. Verify
osslsigncode verify dist/Franklin-Installer-Windows.exe
```

## GitHub Actions Secrets

Add these to your repository (Settings → Secrets → Actions):

### macOS
- `MACOS_CERTIFICATE_NAME`
- `APPLE_ID`
- `APPLE_ID_PASSWORD`
- `TEAM_ID`

### Windows
- `WINDOWS_CERT_BASE64`
- `WINDOWS_CERT_PASSWORD`

## Without Signing (Free)

Users will see security warnings but can still install:

### macOS
- Right-click → Open → Open

### Windows
- More info → Run anyway

## Testing

Always test on a clean machine without developer tools:

```bash
# macOS - Check if it opens without warning
open dist/Franklin-Installer-macOS.dmg

# Windows - Check SmartScreen
# (Must test on actual Windows machine)
```

## Certificate Providers

### macOS
- Apple Developer Program: https://developer.apple.com/programs/

### Windows
- DigiCert: https://www.digicert.com/code-signing
- Sectigo: https://sectigo.com/ssl-certificates/code-signing
- GlobalSign: https://www.globalsign.com/en/code-signing-certificate
- SSL.com: https://www.ssl.com/certificates/code-signing

## Costs Summary

| What You're Building | Recommended Setup | Annual Cost |
|---------------------|------------------|-------------|
| Personal/Testing | Self-signed (with instructions) | $0 |
| Small Team (<50 users) | Apple Dev + Standard Windows Cert | $299-499 |
| Production/Enterprise | Apple Dev + EV Windows Cert | $399-799 |
| Open Source Project | Self-signed + Package Managers | $0 |

## Common Issues

### macOS: "Certificate not trusted"
- Make sure you're using "Developer ID Application" not "Mac Development"
- Certificate must be in login keychain

### Windows: "Publisher unknown"
- Standard certificates need ~100 downloads to build reputation
- Consider EV certificate for instant trust

### Both: "Certificate expired"
- Certificates expire annually
- Set calendar reminders 30 days before expiration

## Next Steps

1. **Start with self-signed** - Get everything working first
2. **Document the bypass process** - Help users install unsigned versions
3. **Buy certificates when ready** - When you have users and budget
4. **Automate everything** - Use GitHub Actions for consistent builds