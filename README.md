<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey?logo=apple&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/github/license/junlinwk/e3cli?color=green" alt="License">
  <img src="https://img.shields.io/github/v/tag/junlinwk/e3cli?label=version&color=orange" alt="Version">
</p>

<h1 align="center">e3cli</h1>

<p align="center">
  <b>NYCU E3 Moodle automation CLI</b><br>
  Sync courses, download materials, submit assignments — all from your terminal.
</p>

<p align="center">
  <a href="#installation">Install</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#commands">Commands</a> &bull;
  <a href="#security">Security</a> &bull;
  <a href="./README_zh-TW.md">繁體中文</a>
</p>

---

> **Intended use:** Finished your homework? Too lazy to open the browser? Submit it from CLI.
>
> ~~**Unintended use:** Let Claude Code auto-pull new assignments, finish them, and upload. (Please don't.)~~

## Features

- **Login** — Moodle Web Service API authentication with encrypted credential storage
- **Courses** — List all enrolled courses
- **Assignments** — View assignments, deadlines, and submission status
- **Download** — Batch download course materials, skip already-downloaded files
- **Submit** — Upload and submit assignments directly from CLI
- **Sync** — One command to pull everything new (materials + assignment status)
- **Schedule** — Cron-based automatic sync
- **Bilingual** — Full Chinese/English support

## Supported Platforms

| Platform | Architecture | Status |
|----------|-------------|--------|
| macOS | Apple Silicon (ARM64) | :white_check_mark: Supported |
| macOS | Intel (x86_64) | :white_check_mark: Supported |
| Linux | x86_64 | :white_check_mark: Supported |
| Linux | ARM64 | :white_check_mark: Supported |

Requires **Python 3.11+**.

---

## Installation

### Homebrew (recommended)

```bash
brew tap junlinwk/e3cli
brew install e3cli
```

### pipx

```bash
pipx install git+https://github.com/junlinwk/e3cli.git
```

### pip

```bash
pip install git+https://github.com/junlinwk/e3cli.git
```

### From source

```bash
git clone https://github.com/junlinwk/e3cli.git
cd e3cli
pip install -e ".[dev]"
```

> After installation, `e3cli` is available as a system-wide command.

### Upgrade

| Method | Command |
|--------|---------|
| Homebrew | `brew update && brew upgrade e3cli` |
| pipx (GitHub) | `pipx install git+https://github.com/junlinwk/e3cli.git --force` |
| pipx (PyPI) | `pipx upgrade e3cli` |
| pip (PyPI) | `pip install e3cli --upgrade` |

---

## Quick Start

```bash
# 1. Login (first time — interactive setup wizard will guide you)
e3cli login --save

# 2. List your courses
e3cli courses

# 3. Download all course materials
e3cli download --all

# 4. Check assignments and deadlines
e3cli assignments

# 5. Submit an assignment
e3cli submit <assignment-id> homework.pdf

# 6. Enable automatic sync (every hour)
e3cli schedule enable
```

---

## Commands

### `e3cli login`

Authenticate with your Moodle account and store the API token.

```bash
e3cli login                    # Interactive prompt
e3cli login -u <student-id>    # Specify username
e3cli login --save             # Save credentials (encrypted) for auto-refresh
e3cli login --refresh          # Re-authenticate using saved credentials
```

### `e3cli logout`

Securely erase all stored credentials and tokens.

```bash
e3cli logout
```

### `e3cli courses`

List all enrolled courses in a formatted table.

```bash
e3cli courses
```

### `e3cli assignments`

View assignments with deadlines and submission status.

```bash
e3cli assignments                  # All assignments
e3cli assignments --due-soon 7     # Due within 7 days
```

### `e3cli download`

Download course materials to local disk.

```bash
e3cli download --all               # All courses
e3cli download --course "OS"       # Filter by course name/code
```

Files are saved to `~/e3-downloads/<course>/<section>/` by default. Already-downloaded files are skipped automatically (tracked via SQLite).

### `e3cli submit`

Upload and submit an assignment.

```bash
e3cli submit <assignment-id> file1.pdf file2.zip
e3cli submit <assignment-id> report.pdf --text "Some notes"
e3cli submit <assignment-id> late-hw.pdf --force     # Submit past deadline
```

### `e3cli sync`

Pull all new materials and update assignment status in one command.

```bash
e3cli sync                # Interactive output
e3cli sync --quiet        # Silent mode (for cron)
```

### `e3cli schedule`

Manage automatic sync via system crontab.

```bash
e3cli schedule enable                  # Default: every 60 minutes
e3cli schedule enable --interval 30    # Every 30 minutes
e3cli schedule disable                 # Remove cron job
e3cli schedule status                  # Show current schedule
```

### `e3cli setup`

Re-run the interactive setup wizard (language, Moodle URL, download directory, login).

```bash
e3cli setup
```

### `e3cli version`

```bash
e3cli version
```

---

## Configuration

Config file location: `~/.e3cli/config.toml`

```toml
[moodle]
url = "https://e3p.nycu.edu.tw"
service = "moodle_mobile_app"

[storage]
download_dir = "~/e3-downloads"

[schedule]
interval_minutes = 60
notify = true

[general]
lang = "zh"    # "zh" or "en", or omit for auto-detect
```

Auto-created with defaults on first run. Edit to customize, or run `e3cli setup` to reconfigure interactively.

---

## Security

### Credential Storage

e3cli uses **PBKDF2-HMAC-SHA256** key derivation with integrity verification to protect stored credentials:

```
~/.e3cli/
  key               # 256-bit random encryption key  (chmod 600)
  credentials.enc   # Encrypted username + password   (chmod 600)
  token             # Moodle API token                (chmod 600)
```

| Measure | Detail |
|---------|--------|
| Encryption | PBKDF2-HMAC-SHA256 (100k iterations) + XOR stream cipher |
| Integrity | HMAC-SHA256 verification on every read |
| File permissions | `chmod 600` — owner-only read/write |
| Password input | `getpass` — never appears in shell history or CLI args |
| Logout | `e3cli logout` overwrites files with zeros before deletion |
| Key separation | Encryption key and encrypted data stored in separate files |

### What's NOT Stored

- :x: No plaintext passwords on disk
- :x: No credentials in `config.toml`
- :x: No credentials in environment variables
- :x: No credentials in shell history

### Recommendations

- Use `e3cli login --save` only on machines you trust
- Run `e3cli logout` when done on shared machines
- The `~/.e3cli/` directory is in `.gitignore` — never commit it

---

## Local Data

| Path | Purpose |
|------|---------|
| `~/.e3cli/config.toml` | User configuration |
| `~/.e3cli/token` | Moodle API token (chmod 600) |
| `~/.e3cli/key` | Encryption key (chmod 600) |
| `~/.e3cli/credentials.enc` | Encrypted credentials (chmod 600) |
| `~/.e3cli/data/e3cli.db` | SQLite tracking DB |
| `~/e3-downloads/` | Downloaded course materials |

---

## Development

```bash
git clone https://github.com/junlinwk/e3cli.git
cd e3cli
make dev       # pip install -e ".[dev]"
make lint      # ruff check
make test      # pytest
make build     # python -m build
```

## Roadmap

- [ ] AI-powered material summarization
- [ ] AI-assisted assignment drafting
- [ ] Smart deadline notifications with priority scoring
- [ ] Desktop notifications (Linux `notify-send`, macOS `osascript`)
- [ ] Course filtering by semester
- [ ] Parallel downloads

---

## License

[MIT](./LICENSE)
