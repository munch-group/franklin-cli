# Installer Methods Comparison

## Quick Comparison Table

| Method | Cost | Security Warnings | User Trust | Corporate Friendly | Offline |
|--------|------|------------------|------------|-------------------|---------|
| **Web Installer** (`curl\|bash`) | $0 | None | Low-Medium | Often Blocked | No |
| **Signed Native** | $99-700/yr | None | High | Yes | Yes |
| **Unsigned Native** | $0 | Yes (bypass required) | Medium | Maybe | Yes |
| **Package Manager** | $0 | None | High | Yes | Yes* |

*Depends on package manager configuration

## Web Installer (`curl | bash`)

### How to Use
```bash
curl -fsSL https://franklin.io/install | bash
```

### Pros
- ✅ No security warnings at all
- ✅ One-line installation
- ✅ Free (no certificates needed)
- ✅ Easy to update server-side
- ✅ Works on any Unix-like system

### Cons
- ❌ Requires internet connection
- ❌ Users must trust your server
- ❌ Often blocked in corporate environments
- ❌ Controversial security pattern
- ❌ Can't inspect before running (easily)

### Best For
- Open source projects
- Developer tools
- Quick demos and prototypes
- Technical audiences

## Signed Native Installers

### How to Use
```bash
# Download DMG/EXE and double-click
# No warnings, runs immediately
```

### Pros
- ✅ No security warnings
- ✅ Professional appearance
- ✅ High user trust
- ✅ Works offline
- ✅ Corporate-friendly

### Cons
- ❌ Expensive ($99-700/year)
- ❌ Complex setup
- ❌ Annual renewal required
- ❌ Different certificates per platform
- ❌ Build process required

### Best For
- Commercial software
- Enterprise deployments
- Non-technical users
- High-security environments

## Unsigned Native Installers

### How to Use
```bash
# macOS: Right-click → Open → Open
# Windows: More info → Run anyway
```

### Pros
- ✅ Free
- ✅ Works offline
- ✅ Professional appearance
- ✅ Full control over installation

### Cons
- ❌ Security warnings
- ❌ Users need instructions to bypass
- ❌ Lower trust
- ❌ May be blocked by IT policies
- ❌ Support overhead

### Best For
- Internal tools
- Beta software
- Small user base
- Budget-conscious projects

## Package Managers

### How to Use
```bash
# Homebrew
brew install franklin

# Conda
conda install -c munch-group franklin

# Chocolatey
choco install franklin
```

### Pros
- ✅ No security warnings
- ✅ High trust (managed by package manager)
- ✅ Easy updates
- ✅ Dependency management
- ✅ Corporate-friendly

### Cons
- ❌ Requires package manager installed
- ❌ Maintenance overhead
- ❌ Approval process for some managers
- ❌ Platform-specific
- ❌ Version lag

### Best For
- Developer tools
- Scientific software
- Unix/Linux focus
- Technical users

## Decision Matrix

### Choose Web Installer If:
- [x] You have no budget for certificates
- [x] Your users are developers
- [x] You need zero-friction installation
- [x] You can maintain a reliable server
- [x] Security warnings are a blocker

### Choose Signed Native If:
- [x] You have budget ($99-700/year)
- [x] You have non-technical users
- [x] You need corporate deployment
- [x] Professional appearance matters
- [x] Offline installation is required

### Choose Unsigned Native If:
- [x] You have no budget
- [x] You have a small, known user base
- [x] Users can follow bypass instructions
- [x] You need offline installation
- [x] It's for internal/beta use

### Choose Package Manager If:
- [x] Your users already use the manager
- [x] You need dependency management
- [x] You're targeting developers/scientists
- [x] You want automatic updates
- [x] Platform coverage isn't critical

## Hybrid Approach (Recommended)

Offer multiple options to maximize reach:

```markdown
## Install Franklin

### Quick Install (Developers)
curl -fsSL https://franklin.io/install | bash

### Native Installers (End Users)
- [Download for macOS](https://franklin.io/download/mac)
- [Download for Windows](https://franklin.io/download/windows)

### Package Managers (Power Users)
brew install franklin      # macOS/Linux
choco install franklin     # Windows
conda install franklin     # Cross-platform

### Manual Installation (Security-Conscious)
git clone https://github.com/franklin/franklin
cd franklin && ./install.sh
```

## Security Best Practices

### For Web Installers
1. Always use HTTPS
2. Provide checksums
3. Allow inspection option
4. Use GPG signing
5. Rate limit endpoints

### For Native Installers
1. Sign everything if budget allows
2. Provide clear bypass instructions
3. Use timestamp servers
4. Notarize on macOS
5. Consider EV certificates for Windows

### For All Methods
1. Communicate what will be installed
2. Provide uninstall instructions
3. Support version pinning
4. Document system requirements
5. Maintain security contact

## Cost Analysis (Annual)

### Minimal Budget ($0)
- Web installer (curl|bash)
- Unsigned native installers
- Package managers
- Documentation for bypassing warnings

### Small Budget ($99)
- Apple Developer Program
- Signed macOS installers
- Web installer for Windows/Linux

### Medium Budget ($300-500)
- Apple Developer Program ($99)
- Windows Standard Certificate ($200-400)
- Both platforms signed

### Full Budget ($400-800)
- Apple Developer Program ($99)
- Windows EV Certificate ($300-700)
- Instant trust on all platforms

## Conclusion

**No single method is perfect.** The best approach depends on:
- Your budget
- Your audience
- Security requirements
- Platform requirements
- Maintenance capacity

**Recommendation**: Start with web installer + unsigned native installers, then add signing as your project grows and budget allows.