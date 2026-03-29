<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey?logo=apple&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/github/license/junlinwk/e3cli?color=green" alt="License">
  <img src="https://img.shields.io/github/v/tag/junlinwk/e3cli?label=version&color=orange" alt="Version">
</p>

<h1 align="center">e3cli</h1>

<p align="center">
  <b>Moodle automation CLI — works with any Moodle instance</b><br>
  Sync courses, download materials, submit assignments, view announcements — all from your terminal.
</p>

<p align="center">
  <a href="#installation">Install</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#commands">Commands</a> &bull;
  <a href="#interactive-mode">Interactive</a> &bull;
  <a href="#security">Security</a> &bull;
  <a href="#claude-code-integration">Claude Code</a> &bull;
  <a href="./README_zh-TW.md">繁體中文</a>
</p>

---

> **Intended use:** Finished your homework? Too lazy to open the browser? Submit it from CLI.
>
> ~~**Unintended use:** Let Claude Code auto-pull new assignments, finish them, and upload. (Please don't.)~~

## Features

- **Login** — Moodle Web Service API authentication with encrypted credential storage
- **Multi-profile** — Multiple accounts with per-profile Moodle URL; switch profiles to switch schools instantly
- **Courses** — List enrolled courses grouped by semester, view course intro
- **Assignments** — View assignments with descriptions, deadlines, submission status, and attachments
- **Download** — Batch download course materials (current semester by default)
- **Submit / Edit** — Upload, submit, and re-upload (overwrite) assignments
- **Announcements** — View course announcements and their content
- **Members** — List course members (teachers and students)
- **Messaging** — Send Moodle messages to course members
- **Sync** — One command to pull everything new (materials + assignment status)
- **Schedule** — Cron-based automatic sync
- **Interactive TUI** — Full arrow-key interactive interface (`e3cli i`)
- **Bilingual** — Full Chinese/English support
- **Multi-school** — Works with any Moodle instance (configurable semester format)

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
e3cli download

# 4. Check assignments and deadlines
e3cli assignments

# 5. Submit an assignment
e3cli submit <assignment-id> homework.pdf

# 6. Launch interactive mode
e3cli i
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

List enrolled courses grouped by semester.

```bash
e3cli courses                  # Current semester only
e3cli courses --all            # All semesters
e3cli courses --semester 1142  # Specific semester
```

### `e3cli assignments`

View assignments with deadlines, submission status, descriptions, and attachment counts. Sorted by urgency (upcoming first, expired middle, submitted last).

```bash
e3cli assignments                  # Current semester
e3cli assignments --due-soon 7     # Due within 7 days
e3cli assignments --all            # All semesters
e3cli assignments --detail <ID>    # Full description + attachments for one assignment
```

### `e3cli download`

Download course materials to local disk (current semester by default).

```bash
e3cli download                     # Current semester (default)
e3cli download --all               # All semesters
e3cli download --course "OS"       # Fuzzy match by course name/code
e3cli download --select            # Interactive course selection
```

Files are saved to `~/e3-downloads/<course>/<section>/` by default. Already-downloaded files are skipped automatically (tracked via SQLite).

### `e3cli submit`

Upload and submit an assignment.

```bash
e3cli submit <assignment-id> file1.pdf file2.zip
e3cli submit <assignment-id> report.pdf --text "Some notes"
e3cli submit <assignment-id> late-hw.pdf --force     # Submit past deadline
```

Re-submitting to the same assignment ID will overwrite the previous submission.

### `e3cli announcements`

View course announcements.

```bash
e3cli announcements -c "OS"                # List announcements
e3cli announcements -c "OS" --detail <ID>  # View full content + attachments
```

### `e3cli members`

List course members with roles and email.

```bash
e3cli members -c "OS"          # Teachers listed first
```

### `e3cli message`

Send a Moodle message to a user (recipient receives notification based on their settings).

```bash
e3cli message <user-id> "Hello"    # Direct message
e3cli message <user-id>            # Interactive multi-line input
```

### `e3cli sync`

Pull all new materials and update assignment status in one command.

```bash
e3cli sync                     # Current semester (default)
e3cli sync --all               # All semesters
e3cli sync --course "OS"       # Specific course
e3cli sync --quiet             # Silent mode (for cron)
```

### `e3cli schedule`

Manage automatic sync via system crontab.

```bash
e3cli schedule enable                  # Default: every 60 minutes
e3cli schedule enable --interval 30    # Every 30 minutes
e3cli schedule disable                 # Remove cron job
e3cli schedule status                  # Show current schedule
```

### `e3cli profile`

Manage multiple accounts. Each profile stores its own credentials, token, and **Moodle URL**, so you can switch between different schools instantly.

```bash
e3cli profile                  # List all profiles (with school URL)
e3cli profile use <name>       # Switch to a profile (also switches Moodle URL)
e3cli profile remove <name>    # Remove a profile
```

When switching profiles via `e3cli profile use` or the interactive TUI, the Moodle URL in `config.toml` is automatically updated to match the profile's school.

```bash
# Login to a different school with a new profile
e3cli login --profile nycu --url https://e3p.nycu.edu.tw --save
e3cli login --profile ntu --url https://cool.ntu.edu.tw --save

# Switch between schools
e3cli profile use nycu    # → connects to NYCU E3
e3cli profile use ntu     # → connects to NTU COOL
```

### `e3cli setup`

Re-run the interactive setup wizard (language, Moodle URL, semester format, alias, download directory, login).

```bash
e3cli setup
```

### `e3cli version`

```bash
e3cli version
```

---

## Interactive Mode

Launch with `e3cli i` for a full TUI experience with arrow-key navigation:

```
╭──────────────── e3cli v0.5.0 ────────────────╮
│  王小明  |  114學年第2學期  |  6 courses      │
╰──────────────────────────────────────────────╯

────────────────── 主選單 ──────────────────────
❯ 選擇課程 (114學年第2學期)
  選擇課程 (所有學期)
  作業
  同步課程
  離開

↑↓ navigate  →/Enter select  ← back  / search
────────────────────────────────────────────────
```

### Navigation

| Key | Action |
|-----|--------|
| `↑` `↓` | Move selection |
| `→` / `Enter` | Enter selected item |
| `←` / `Esc` | Go back |
| `/` or type | Search / filter |
| `q` | Quit / back |

### Profile Menu

Select "Profile" from the main menu to:
- **Switch** between profiles (auto-reloads with the new school's data)
- **Edit** a profile (change Moodle URL, username, password)
- **Delete** a profile (cannot delete the active one)
- **Add** a new profile with a different school URL

### Course Menu

Enter a course to access:
- **Course Intro** — View course description
- **Materials** — Browse and download files (with download status)
- **Assignments** — View with descriptions, attachments, submission status; submit or re-upload
- **Announcements** — Read course announcements
- **Members** — View member list, send messages directly
- **Grades** — View grade items

### Assignment Detail

Select an assignment to see:
- Full description (HTML rendered as text)
- Attachment list with download
- Currently submitted files
- Submit (`s`) or Edit/re-upload (`e`) with tab-completion file picker
- Shell mode (`!`) for terminal commands within the file picker

### File Picker Features

When submitting or re-uploading:
- Shows current directory and file listing
- **Tab completion** for file paths (like your shell)
- **`!command`** to run a shell command (e.g., `!ls -la`)
- **`!`** alone to enter interactive shell mode (type `exit` to return)
- Confirmation prompt before uploading

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
lang = "zh"              # "zh" or "en", or omit for auto-detect
semester_format = "nycu"  # "nycu", "western", "none"
alias = ""                # custom command name (e.g. "moodle")
```

### Semester Format

| Format | Schools | Example |
|--------|---------|---------|
| `nycu` (default) | NYCU, NTU, and other Taiwan universities | `1142` = year 114, semester 2 |
| `western` | Western year-based systems | `2025` |
| `none` | Any school (no filtering) | All courses treated as current |

Auto-created with defaults on first run. Edit to customize, or run `e3cli setup` to reconfigure interactively.

---

## Security

### Credential Storage

e3cli uses **PBKDF2-HMAC-SHA256** key derivation with integrity verification to protect stored credentials:

```
~/.e3cli/profiles/<name>/
  key               # 256-bit random encryption key  (chmod 600)
  credentials.enc   # Encrypted username + password   (chmod 600)
  token             # Moodle API token                (chmod 600)
  profile.json      # Moodle URL and service config
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

## Claude Code Integration

This project includes a `CLAUDE.md` file that teaches [Claude Code](https://claude.ai/code) how to use e3cli as an automated assistant. When Claude Code is invoked in this project directory, it can:

- Sync and check for new assignments (`e3cli sync`)
- Read assignment descriptions and downloaded materials
- Help complete assignments (with human oversight)
- Submit completed work (`e3cli submit`)

See [`CLAUDE.md`](./CLAUDE.md) and [`e3cli/agent_prompt.md`](./e3cli/agent_prompt.md) for the full agent automation guide.

> **Note:** Claude Code will always ask for confirmation before submitting assignments.

---

## Local Data

| Path | Purpose |
|------|---------|
| `~/.e3cli/config.toml` | User configuration |
| `~/.e3cli/token` | Active profile's Moodle API token (chmod 600) |
| `~/.e3cli/active_profile` | Active profile name |
| `~/.e3cli/profiles/<name>/` | Per-profile credentials, token, key, and Moodle URL |
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

- [x] Interactive TUI with arrow-key navigation
- [x] Semester filtering (current semester by default)
- [x] Multi-school Moodle support (per-profile URL)
- [x] Assignment descriptions and attachments
- [x] Course announcements
- [x] Course members and messaging
- [x] Edit/re-upload submissions
- [ ] AI-powered material summarization
- [ ] AI-assisted assignment drafting
- [ ] Smart deadline notifications with priority scoring
- [ ] Desktop notifications (Linux `notify-send`, macOS `osascript`)
- [ ] Parallel downloads

---

## License

[MIT](./LICENSE)
