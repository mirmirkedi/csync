# Security

## What csync stores

csync saves a copy of each account's login session so it can switch between accounts. That copy contains **live credentials** (session cookies and OAuth tokens) in `~/.csync/snapshots/<account-uuid>/`, plus backups of the app's `Cookies` and `config.json` under `~/.csync/backup/`.

- Everything under `~/.csync` is created with owner-only permissions (`700` for folders, `600` for files).
- Treat `~/.csync` like an SSH private key: never commit it, upload it, or paste its contents into an issue.
- csync copies the values exactly as the app stores them and never decrypts or inspects them. Electron apps normally encrypt cookies and tokens with a key held in the macOS keychain, which would make snapshots usable only by your user on your Mac, but do not rely on that: assume they are sensitive.
- csync makes no network requests.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository ("Security" tab -> "Report a vulnerability") instead of a public issue. Never include real tokens, cookies, or the contents of `~/.csync` in a report.
