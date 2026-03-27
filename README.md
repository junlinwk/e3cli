# e3cli

NYCU E3 Moodle automation CLI -- sync courses, download materials, submit assignments from your terminal.

## Features

- **Login** -- authenticate via Moodle Web Service API, encrypted credential storage
- **Courses** -- list all enrolled courses
- **Assignments** -- view assignments, deadlines, submission status
- **Download** -- batch download course materials, skip already-downloaded files
- **Submit** -- upload and submit assignments from CLI
- **Sync** -- one command to pull everything new (materials + assignment status)
- **Schedule** -- cron-based automatic sync

## Supported Platforms

| Platform | Architecture | Status |
|----------|-------------|--------|
| macOS | Apple Silicon (ARM64) | Supported |
| macOS | Intel (x86_64) | Supported |
| Linux | x86_64 | Supported |
| Linux | ARM64 | Supported |

Requires **Python 3.11+**.

---

## Installation

### Option 1: Homebrew (recommended for macOS/Linux)

```bash
# Add the tap
brew tap junlinwk/e3cli

# Install
brew install e3cli

# Verify
e3cli version
```

### Option 2: pipx (isolated install, recommended for Linux)

```bash
# Install pipx if you don't have it
brew install pipx   # or: apt install pipx
pipx ensurepath

# Install e3cli
pipx install e3cli

# Verify
e3cli version
```

### Option 3: pip

```bash
pip install e3cli
```

### Option 4: From source (development)

```bash
git clone https://github.com/junlinwk/e3cli.git
cd e3cli
pip install -e ".[dev]"
```

## Update
---

## Quick Start

```bash
# 1. Login (first time)
e3cli login --save        # --save encrypts and stores your credentials locally

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

### `e3cli version`

```bash
e3cli version
```

---

## Configuration

Config file: `~/.e3cli/config.toml`

```toml
[moodle]
url = "https://e3p.nycu.edu.tw"    # Your Moodle instance URL
service = "moodle_mobile_app"       # Web service name (usually don't change)

[storage]
download_dir = "~/e3-downloads"     # Where to save course materials
db_path = "~/.e3cli/data/e3cli.db"  # Tracking database

[schedule]
interval_minutes = 60               # Sync interval for cron job
notify = true                       # Desktop notifications (future)
```

The config file is auto-created with defaults on first run. Edit it to customize behavior.

---

## Security

### Credential Storage

e3cli uses **Fernet symmetric encryption** (from the `cryptography` library) to protect stored credentials:

```
~/.e3cli/
  key               # Random 256-bit encryption key (chmod 600)
  credentials.enc   # Encrypted username + password (chmod 600)
  token             # Moodle API token (chmod 600)
```

- Encryption key is randomly generated per machine and stored separately from credentials
- All sensitive files are created with `chmod 600` (owner-only read/write)
- Passwords are **never** stored in plaintext or passed as CLI arguments (uses `getpass`)
- `e3cli logout` securely overwrites files with zeros before deletion

### What's NOT stored

- Your password is never written to shell history (interactive `getpass` prompt)
- No credentials in `config.toml`
- No credentials in environment variables

### Recommendations

- Use `e3cli login --save` only on machines you trust
- Run `e3cli logout` when done on shared machines
- The `~/.e3cli/` directory is in `.gitignore` -- never commit it

---

## Local Data

| Path | Purpose |
|------|---------|
| `~/.e3cli/config.toml` | User configuration |
| `~/.e3cli/token` | Moodle API token (encrypted-equivalent, chmod 600) |
| `~/.e3cli/key` | Encryption key (chmod 600) |
| `~/.e3cli/credentials.enc` | Encrypted credentials (chmod 600) |
| `~/.e3cli/data/e3cli.db` | SQLite tracking DB (downloaded files, assignment status) |
| `~/e3-downloads/` | Downloaded course materials |


---

## Project Structure

```
e3cli/
├── pyproject.toml              # Package metadata and dependencies
├── Makefile                    # Dev shortcuts (make dev, make test, etc.)
├── LICENSE                     # MIT License
├── Formula/e3cli.rb            # Homebrew formula template
├── scripts/
│   ├── generate-formula.py     # Auto-generate formula from PyPI
│   └── setup-homebrew-tap.sh   # Bootstrap Homebrew tap repo
├── .github/workflows/
│   ├── ci.yml                  # Test on push/PR (Linux + macOS, Py 3.11-3.13)
│   └── release.yml             # Build + publish on tag push
├── e3cli/
│   ├── __init__.py
│   ├── __main__.py             # python -m e3cli
│   ├── cli.py                  # Typer CLI entry point
│   ├── config.py               # ~/.e3cli/config.toml management
│   ├── auth.py                 # Moodle token authentication
│   ├── credential.py           # Encrypted credential storage
│   ├── api/
│   │   ├── client.py           # Moodle REST API client
│   │   ├── site.py             # Site info
│   │   ├── courses.py          # Course listing and contents
│   │   ├── assignments.py      # Assignment queries and submission
│   │   └── files.py            # File download
│   ├── storage/
│   │   ├── db.py               # SQLite schema and operations
│   │   ├── models.py           # Data models
│   │   └── tracking.py         # Download/assignment tracking
│   ├── commands/
│   │   ├── _common.py          # Shared utilities (get_client, get_db)
│   │   ├── login.py            # e3cli login
│   │   ├── logout.py           # e3cli logout
│   │   ├── courses.py          # e3cli courses
│   │   ├── assignments.py      # e3cli assignments
│   │   ├── download.py         # e3cli download
│   │   ├── submit.py           # e3cli submit
│   │   ├── sync.py             # e3cli sync
│   │   └── schedule.py         # e3cli schedule
│   ├── scheduler/
│   │   └── cron.py             # Crontab management
│   └── ai/                     # Future: AI integration
│       └── __init__.py
└── tests/
```

---

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/<your-user>/e3cli.git
cd e3cli
make dev                    # pip install -e ".[dev]"

# Run linter
make lint

# Run tests
make test

# Build distribution
make build
```

---

## Roadmap

- [ ] AI-powered material summarization (`e3cli ai summarize`)
- [ ] AI-assisted assignment drafting (`e3cli ai draft`)
- [ ] Smart deadline notifications with priority scoring
- [ ] Desktop notification integration (Linux `notify-send`, macOS `osascript`)
- [ ] Course filtering by semester
- [ ] Parallel downloads for faster sync

---

## License

MIT
