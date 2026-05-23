# E3CLI — Claude Code Integration

## What is this?

e3cli is a CLI tool for Moodle platforms (default: NYCU E3). It can sync courses, download materials, check assignments, view announcements, list members, send messages, and submit homework.

## Quick Reference

```bash
# Sync current semester (materials + assignments)
e3cli sync

# List assignments (sorted by urgency, with submission status)
e3cli assignments

# Assignments due within 7 days
e3cli assignments --due-soon 7

# View full assignment description + attachments
e3cli assignments --detail <ASSIGNMENT_ID>

# List courses (current semester)
e3cli courses
e3cli courses --all    # all semesters

# Download materials
e3cli download                     # current semester
e3cli download --course "OS"       # specific course (fuzzy match)

# View announcements
e3cli announcements -c "OS"
e3cli announcements -c "OS" --detail <ID>

# List course members
e3cli members -c "OS"

# Send message to a user
e3cli message <USER_ID> "message text"

# Submit assignment
e3cli submit <ASSIGNMENT_ID> <FILE_PATH>

# Re-submit (overwrite) — same command, overwrites previous
e3cli submit <ASSIGNMENT_ID> <NEW_FILE_PATH>

# Profile management (multi-account, multi-school)
e3cli profile                      # list all profiles (with Moodle URL)
e3cli profile use <name>           # switch profile (also switches Moodle URL)
e3cli profile remove <name>        # remove a profile
e3cli login --profile <name> --url <moodle-url> --save  # add profile for different school

# Interactive mode (arrow keys)
e3cli i

# Token expired?
e3cli login --refresh

# AI agent skill (install SKILL.md into Claude Code / Codex / Gemini / Antigravity CLI)
e3cli skill status                 # check what's detected / installed
e3cli skill install                # auto-install for detected agents
e3cli skill install -t claude      # specific target (claude/codex/gemini/antigravity)
e3cli skill uninstall              # remove
```

> **First run:** if `~/.e3cli/config.toml` doesn't exist, ANY `e3cli <cmd>` launches the interactive setup wizard. The wizard is 6 steps (Moodle URL → semester format → download dir → alias → login → AI agent skill install). After completion, re-run the original command.

## Workflow: When a New Assignment is Detected

1. `e3cli sync` — pull latest materials and assignment status
2. `e3cli assignments` — see what's new/urgent (sorted by deadline)
3. `e3cli assignments --detail <ID>` — read the full description and check attachments
4. Downloaded materials are in the download directory (check `e3cli sync` output for path)
5. Work on the assignment
6. `e3cli submit <ID> <file>` — submit when ready
7. **Always confirm with the user before submitting**

## Reading Assignment Details

```bash
# Get assignment list with IDs
e3cli assignments

# Read full description (HTML converted to text)
e3cli assignments --detail 12345

# The output includes:
# - Full description text
# - Attachment list with URLs
# - Submission status
# - Due date
```

## Checking Course Materials

```bash
# Download materials for a course
e3cli download --course "artificial intelligence"

# Materials are saved to the download directory
# The exact path is shown after download completes
```

## Important Rules

1. **Never submit without user confirmation** — always ask before running `e3cli submit`
2. **Academic integrity** — assist, don't replace the student's work
3. **Check deadlines first** — prioritize urgent assignments
4. **Token expiry** — if commands fail with auth errors, run `e3cli login --refresh`
5. **Don't read credential files** — use CLI commands, not direct file access
6. **First-run wizard hangs the agent** — if a command opens an interactive setup wizard (config missing) or `login --refresh` prompt, STOP and tell the user to run `e3cli setup` / `e3cli login --refresh` themselves in their terminal. Both are interactive and will hang an agent session.

## Data Locations

| Path | Content |
|------|---------|
| Download directory | Course materials (shown in sync/download output) |
| `~/.e3cli/data/e3cli.db` | Local tracking database |
| `~/.e3cli/config.toml` | Configuration |

## Full Agent Automation Guide

See `e3cli/agent_prompt.md` for the complete automation workflow.
