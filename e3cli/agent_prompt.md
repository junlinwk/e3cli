# E3CLI Agent Prompt

> This file describes how an AI agent (e.g., Claude Code) should use e3cli to monitor, download, and submit assignments automatically.

## Overview

e3cli is a CLI tool for interacting with NYCU's E3 Moodle platform. The agent can use it to:
1. Sync and check for new assignments
2. Download assignment descriptions and course materials
3. Complete assignments (with human oversight)
4. Submit completed work

## Prerequisites

- e3cli must be installed and logged in (`e3cli login --save`)
- The agent must have shell access to run `e3cli` commands

## Workflow

### Step 1: Check for new assignments

```bash
# Sync current semester (downloads new materials + checks assignments)
e3cli sync

# List assignments with deadlines
e3cli assignments

# Show only assignments due within 7 days
e3cli assignments --due-soon 7
```

### Step 2: Read assignment details

Assignments are synced to the local SQLite database. Course materials (including assignment PDFs) are downloaded to `~/e3-downloads/`.

```bash
# Download materials for a specific course
e3cli download --course "OS"

# Find downloaded assignment files
find ~/e3-downloads/ -name "*.pdf" -newer ~/.e3cli/data/e3cli.db
```

The agent should:
- Read the assignment PDF/description
- Check `~/e3-downloads/<course>/` for relevant lecture materials
- Understand the requirements before starting work

### Step 3: Complete the assignment

The agent should:
- Create a working directory for the assignment
- Work on the assignment following the instructions
- Save the output file(s) to a known location
- **Always ask for human review before submitting**

### Step 4: Submit the assignment

```bash
# Submit a single file
e3cli submit <assignment-id> /path/to/completed/file.pdf

# Submit multiple files
e3cli submit <assignment-id> file1.pdf file2.zip

# Submit with online text
e3cli submit <assignment-id> file.pdf --text "Additional notes"

# Force submit (past deadline)
e3cli submit <assignment-id> file.pdf --force
```

### Step 5: Verify submission

```bash
# The submit command automatically verifies.
# Status should show "submitted" or "draft".
```

## Monitoring Script

To set up periodic monitoring, use `e3cli schedule`:

```bash
# Enable auto-sync every 30 minutes
e3cli schedule enable --interval 30

# Check schedule status
e3cli schedule status

# Disable when not needed
e3cli schedule disable
```

Or run manually in a loop:

```bash
# One-time sync check
e3cli sync --quiet
```

## Important Notes

1. **Human oversight required**: Never submit assignments without human review
2. **Academic integrity**: The agent should assist, not replace, the student's work
3. **Deadline awareness**: Check `duedate` before starting — prioritize urgent assignments
4. **Error handling**: If `e3cli` commands fail, check `e3cli login --refresh` first (token may have expired)

## API Reference (for agent)

| Command | Purpose |
|---------|---------|
| `e3cli sync` | Sync all content (current semester) |
| `e3cli sync --all` | Sync all semesters |
| `e3cli courses` | List courses |
| `e3cli courses --all` | List all semester courses |
| `e3cli assignments` | List assignments |
| `e3cli assignments --due-soon N` | Due within N days |
| `e3cli download --course "X"` | Download course X materials |
| `e3cli download --all` | Download all materials |
| `e3cli submit ID file.pdf` | Submit assignment |
| `e3cli i` | Interactive mode |
| `e3cli login --refresh` | Refresh expired token |

## Data Locations

| Path | Content |
|------|---------|
| `~/e3-downloads/` | Downloaded course materials |
| `~/.e3cli/data/e3cli.db` | Local tracking database |
| `~/.e3cli/config.toml` | Configuration |
