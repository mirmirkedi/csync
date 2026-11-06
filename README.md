# csync

A multi-account switcher and chat syncer for the **Claude desktop app** on macOS.

- Save several accounts into numbered slots and switch between them with one command.
- Your Code chats are synced across accounts when you switch, so every account shows the same chats.
- Never deletes anything: whatever gets overwritten is backed up under `~/.csync/backup/`.
- One file, Python 3 standard library only, no network access.

> **Unofficial.** csync is an independent community tool. It is not made by, affiliated with, or endorsed by Anthropic. "Claude" is a trademark of Anthropic.
>
> **Experimental.** It works by copying the app's login files (`Cookies` and part of `config.json`). If a Claude app update changes how it stores logins, switching can stop working. Back-ups are made before every change (see [Recovering](#recovering)). Use at your own risk, and check that using several accounts fits the terms of the services you use.

## Requirements

- macOS
- Python 3.9 or newer (`python3 --version`)
- The Claude desktop app, signed in at least once per account

## Install

```bash
git clone https://github.com/mirmirkedi/csync.git
cd csync
mkdir -p ~/.local/bin
cp csync ~/.local/bin/csync && chmod +x ~/.local/bin/csync
```

Make sure `~/.local/bin` is on your `PATH`, then check:

```bash
csync --version
```

To uninstall, delete `~/.local/bin/csync`. Delete `~/.csync` as well if you also want to remove saved sessions and backups.

## Quick start

1. Sign in to the Claude app with your first account, then save it:

   ```bash
   csync add main
   ```

2. Add a second account:

   ```bash
   csync login          # saves the current session, signs out, reopens the app
   # sign in to the app with the other account, then:
   csync add work
   ```

3. Switch whenever you like:

   ```bash
   csync switch work    # or just `csync switch` for the next slot
   ```

Run csync from a **regular terminal** (Terminal, iTerm, ...). It quits and reopens the Claude app, so running it from a session inside the Claude app would close that session.

## Commands

| Command | What it does |
| --- | --- |
| `csync` | Sync chats across all accounts |
| `csync add [label]` | Save the account that is signed in right now into a slot (updates it if already saved) |
| `csync login` | Save the current session, sign out, and reopen the app so you can sign in with another account |
| `csync list` | List saved accounts (`*` marks the signed-in one) |
| `csync status` | Show which account is signed in |
| `csync switch [account]` | Sync, then switch. With no argument, go to the next slot |
| `csync label <account> <name>` | Rename an account |
| `csync swap <a> <b>` | Exchange the slot numbers of two accounts |
| `csync move <account> <slot>` | Move an account to another slot (swaps if taken) |
| `csync remove <account>` | Forget an account (its chats stay) |
| `csync org <account> <org-uuid>` | Choose which organization folder is used for chat sync |
| `csync --dry-run` | With `sync` or `switch`: show what would happen without changing anything |
| `csync --version`, `csync --help` | Version and usage |

`<account>` is a slot number, a label, or the start of the account uuid (see `csync list`).

## How it works

- Account records live in `~/.csync/accounts.json`. Each account's login session (cookies and tokens) is stored in `~/.csync/snapshots/<account-uuid>/` with owner-only permissions. See [SECURITY.md](SECURITY.md).
- On a switch: the app is quit, the signed-in account's refreshed session is saved, chats are synced, then the target account's session is written into the app's `Cookies` and `config.json` (only the login keys, other settings stay), and the app is reopened.
- Chat sync copies `claude-code-sessions/<account>/<org>/local_*.json` files toward the newest copy, judged by `lastActivityAt`. Older copies that get replaced are backed up first. If an account has several organization folders, the most recently used one is chosen; change it with `csync org` if that is wrong.
- Account ids and organization folders are read from the app's own data when you run `csync add`. Nothing is hard-coded.

## Recovering

Before every change csync copies the app's live `config.json` and `Cookies` to `~/.csync/backup/<timestamp>/live/`, and replaced chat files to `~/.csync/backup/<timestamp>/sessions/`.

If something looks wrong after a switch:

```bash
# 1. quit the Claude app (Cmd+Q)
# 2. pick a backup folder
ls ~/.csync/backup
# 3. put the files back (replace <timestamp>)
B=~/.csync/backup/<timestamp>/live
cp "$B/config.json" "$HOME/Library/Application Support/Claude/config.json"
cp "$B/Cookies" "$HOME/Library/Application Support/Claude/Cookies"
```

Backups are never pruned automatically; delete old ones from `~/.csync/backup` when you no longer need them.

## Troubleshooting

- **"The Claude app did not quit"** - quit it by hand (Cmd+Q) and run the command again.
- **Still signed in as the old account after a switch** - run `csync status`. If the app caches the login somewhere csync does not copy, please open an issue with your macOS and Claude app versions (never paste anything from `~/.csync`).
- **Chats are not syncing** - run `csync list`. Both accounts need an organization folder; one appears after an account's first Code chat. Run `csync add` again for that account. Use `csync org` if the wrong folder was picked, and `csync --dry-run` to preview.
- **"The signed-in account is not saved"** - `csync login` refuses to sign you out of an unsaved account so you cannot lose it. Run `csync add` first.

## Limits

- No automatic switching, usage thresholds, priorities, or per-directory accounts.
- Only the desktop app's Code chats are synced, not the Claude CLI's own credentials or history.
- macOS only.

## Development

```bash
python3 -m unittest discover -s tests -v
```

Tests run `csync` against a fake data folder and never touch the real app or your real `~/.csync`. The `CSYNC_APP_DIR`, `CSYNC_HOME` and `CSYNC_NO_APP=1` environment variables exist for this; do not set them in normal use.

Issues and pull requests are welcome. Please keep it dependency-free, add a test for new behavior, and never include real tokens, cookies, account ids or e-mail addresses in issues or commits.

## License

[MIT](LICENSE). See also [CHANGELOG.md](CHANGELOG.md).
