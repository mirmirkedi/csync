# csync

A multi-account switcher and chat syncer for the **Claude desktop app** on macOS. It has no dependencies beyond Python 3 (standard library only) and does not need any other tool.

- Saves several accounts into slots and switches between them with one command.
- Syncs your Code chats across accounts when you switch, so every account shows the same chats.
- Never deletes anything: whatever gets overwritten is backed up under `~/.csync/backup/`.

## Install

```bash
cp csync ~/.local/bin/csync && chmod +x ~/.local/bin/csync
```

## Adding accounts

Save the account that is currently signed in to the app:

```bash
csync add main
```

For a second account:

```bash
csync login          # saves the current session, signs out, opens the app
# sign in to the app with the other account
csync add work
```

## Usage

```bash
csync                  # sync chats across all accounts
csync list             # saved accounts (* = currently signed in)
csync status           # which account is signed in right now
csync switch           # go to the next slot (syncs chats first)
csync switch 2         # switch by slot number, label, or uuid prefix
csync label 2 work     # set a label
csync swap 1 2         # exchange the slots of two accounts
csync move 2 5         # move an account to another slot
csync remove 2         # remove an account from the list (chats stay)
csync org 2 <org-uuid> # pick the organization folder used for sync by hand
csync switch --dry-run # show what would happen without touching anything
```

csync quits the Claude app if it is running, does its work, and reopens it. **Do not run it from a session inside the Claude app itself**, because that session closes with the app. Use a regular terminal.

## How it works

- Account records live in `~/.csync/accounts.json`. Each account's login session (cookies and tokens) is stored in `~/.csync/snapshots/<account-uuid>/` with owner-only permissions (`600`/`700`). Do not share or commit that folder.
- On a switch: the app is quit, the signed-in account's refreshed session is saved, chats are synced, then the target account's session is written into the app's `Cookies` and `config.json`.
- Chat sync spreads `claude-code-sessions/<account>/<org>/local_*.json` files toward the newest copy by `lastActivityAt`. If an account has several organization folders, the most recently used one is chosen; change it with `csync org` if that is wrong.
- Account ids and organization folders are read from the app's own data when you add an account. Nothing about any account is hard-coded.

## Limits

- The login state is managed through the app's `Cookies` and `config.json`. If an app update changes that layout, switching may break; the `live/` backups under `~/.csync/backup/` are there to roll back.
- There is no automatic switching, usage thresholds, priorities, or directory mapping.
- `CSYNC_APP_DIR`, `CSYNC_HOME` and `CSYNC_NO_APP=1` are environment variables meant for testing.
