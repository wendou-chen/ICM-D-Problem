# Secret Scanning Runbook

This document provides instructions for scanning the repository for secrets and sensitive information.

## Quick Scan Commands

### Using gitleaks (Recommended)

```bash
# Install gitleaks
# Windows (Scoop): scoop install gitleaks
# macOS: brew install gitleaks
# Linux: Download from https://github.com/gitleaks/gitleaks/releases

# Scan current directory
gitleaks detect --source . --verbose

# Scan git history
gitleaks detect --source . --verbose --log-opts="--all"

# Generate report
gitleaks detect --source . --report-format json --report-path gitleaks-report.json
```

### Using trufflehog

```bash
# Install trufflehog
pip install trufflehog

# Scan current directory
trufflehog filesystem .

# Scan git history
trufflehog git file://. --since-commit HEAD~50
```

### Manual grep patterns

```bash
# API Keys
grep -rn "sk-[a-zA-Z0-9]\{20,\}" .
grep -rn "AKIA[A-Z0-9]\{16\}" .
grep -rn "ghp_[a-zA-Z0-9]\{36\}" .
grep -rn "e2b_[a-zA-Z0-9]\{30,\}" .
grep -rn "figd_[a-zA-Z0-9]\{30,\}" .

# Generic secrets
grep -rn -i "api_key\|apikey\|secret\|password\|token\|credential" . --include="*.py" --include="*.json" --include="*.yaml" --include="*.yml" --include="*.env"

# Emails and usernames
grep -rn "[a-zA-Z0-9._%+-]\+@[a-zA-Z0-9.-]\+\.[a-zA-Z]\{2,\}" . --include="*.py" --include="*.md" --include="*.json"

# Home paths
grep -rn "C:\\\\Users\\\\" . --include="*.py" --include="*.json" --include="*.yaml"
grep -rn "/Users/" . --include="*.py" --include="*.json" --include="*.yaml"
grep -rn "/home/" . --include="*.py" --include="*.json" --include="*.yaml"
```

## Pre-commit Integration

Enable automatic secret scanning on every commit:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks (uses .pre-commit-config.yaml)
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## What to Look For

### High Priority (Must Remove)

| Pattern | Example | Risk |
|---------|---------|------|
| API Keys | `sk-abc123...`, `AKIA...` | Direct access to services |
| Tokens | `ghp_...`, `figd_...`, `e2b_...` | Authentication bypass |
| Passwords | `password = "secret"` | Account compromise |
| Private Keys | `-----BEGIN RSA PRIVATE KEY-----` | Full system access |
| Database URLs | `postgresql://user:pass@host` | Data breach |

### Medium Priority (Should Remove)

| Pattern | Example | Risk |
|---------|---------|------|
| Emails | `user@company.com` | Privacy, spam target |
| Usernames | `/Users/john/`, `C:\Users\john\` | Identity exposure |
| Internal IPs | `192.168.1.1`, `10.0.0.1` | Network reconnaissance |

### Low Priority (Review)

| Pattern | Example | Risk |
|---------|---------|------|
| Author names | `Author: John Doe` | Attribution (may be intentional) |
| URLs | Internal company URLs | Information leakage |

## Files to Check Carefully

1. **Configuration files**
   - `.env`, `.env.*`
   - `*.yaml`, `*.yml`
   - `config*.json`

2. **IDE/Editor settings**
   - `.vscode/settings.json`
   - `.idea/`
   - `.opencode/settings.local.json`

3. **Git artifacts**
   - `.git/config` (remote URLs with tokens)
   - `.git/logs/` (author emails)

4. **Notebooks**
   - `*.ipynb` (embedded outputs may contain secrets)

5. **Log files**
   - `*.log` (may contain runtime secrets)

## Remediation Actions

### If Secret Found in Current Files

1. Remove or replace with placeholder
2. Rotate the exposed credential immediately
3. Update `.gitignore` to prevent reoccurrence

### If Secret Found in Git History

Use `git filter-repo` to purge:

```bash
# Install git-filter-repo
pip install git-filter-repo

# Create backup first!
git clone --mirror . ../backup-repo

# Remove file from all history
git filter-repo --path-glob '*.env' --invert-paths

# Remove specific pattern
git filter-repo --blob-callback '
    import re
    data = blob.data.decode("utf-8", errors="ignore")
    data = re.sub(r"sk-[a-zA-Z0-9]{20,}", "REDACTED_API_KEY", data)
    blob.data = data.encode("utf-8")
'
```

**WARNING**: This rewrites history. Coordinate with all team members before running.

## Verification Checklist

- [ ] No API keys in source files
- [ ] No tokens in configuration
- [ ] No passwords in any file
- [ ] No private keys (*.pem, id_rsa)
- [ ] No personal emails (except official contacts)
- [ ] No absolute paths with usernames
- [ ] `.env.example` exists (not `.env`)
- [ ] `.gitignore` includes all secret patterns
- [ ] Pre-commit hooks are configured

---

*Last updated: 2026-02-05*
