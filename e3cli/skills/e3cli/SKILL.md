---
name: e3cli
description: Use when the user wants to interact with their school's Moodle / NYCU E3 platform — sync courses, list assignments, check deadlines, read assignment details, view announcements or course materials, list course members, send Moodle messages, or submit/re-submit homework. Triggers on terms like "Moodle", "E3", "NYCU", "assignment", "homework", "submit", "due date", "作業", "繳交", "課程同步", "公告", "教材".
---

# e3cli — Moodle automation

`e3cli` is a CLI for any Moodle instance (default: NYCU E3). Use it whenever the user wants you to check, prepare, or submit work on their Moodle platform.

The same `e3cli` binary is invoked from the shell — this skill only tells you *when* and *how* to use it. The CLI itself is identical across operating systems.

## Prerequisites — verify first

Before doing real work, confirm the tool is installed, configured, and authenticated:

```bash
test -f ~/.e3cli/config.toml && echo "configured" || echo "needs setup"
e3cli --version    # is it installed?
e3cli courses      # if this errors with "auth"/"token" → user must run: e3cli login --refresh
```

- If config is missing → **STOP**. Any `e3cli <cmd>` will launch an interactive first-run setup wizard that hangs the agent. Tell the user to run `e3cli setup` themselves in their terminal.
- If auth fails → **tell the user to run the login command themselves** — it is interactive and will hang if you run it. Do not attempt to read `~/.e3cli/credentials.enc`, `~/.e3cli/key`, or `~/.e3cli/token`.

## Core workflow

### 1. Find the right assignment (no sync needed)
List and detail commands hit the live Moodle API directly — they do **not** require a prior `e3cli sync`.
```bash
e3cli assignments                  # current semester, sorted by deadline
e3cli assignments --due-soon 7     # due within 7 days only
```
Each row shows an assignment ID. You need that ID for everything that follows.

### 2. Read the full description (no sync needed)
```bash
e3cli assignments --detail <ID>
```
Prints the full description (HTML→text), attachment URLs, submission status, and due date. **Always read this before working** — the one-line summary in `e3cli assignments` is not enough to write a correct submission.

### 3. Pull supporting materials — **targeted only**
Materials may include large media files (mp4 lectures, recordings, slide PDFs). **Never run a blanket sync** unless the user explicitly asks for "sync everything" / "下載全部". Always scope to what the user mentioned.
```bash
# ✓ User mentioned course "OS" or a specific assignment in that course
e3cli download --course "OS"       # download-only, single course (fuzzy match)
e3cli sync --course "OS"           # download + refresh assignment status, single course

# ✗ Avoid these unless user explicitly says "all" / "everything" / "全部"
e3cli sync                         # blanket: every current-semester course
e3cli download                     # blanket download
```
The output prints the download directory — read the relevant files from there.

### 4. Submit (only after explicit user confirmation)
```bash
e3cli submit <ID> <file>
e3cli submit <ID> <file1> <file2>          # multiple files
e3cli submit <ID> <file> --text "notes"    # with online-text
e3cli submit <ID> <file> --force           # past deadline
```
Re-submitting is the same command — it overwrites the previous attempt.

## Other commands

```bash
e3cli courses                              # current semester
e3cli courses --all                        # all semesters
e3cli announcements -c "OS"                # list announcements
e3cli announcements -c "OS" --detail <ID>  # full announcement
e3cli members -c "OS"                      # teachers + students
e3cli message <USER_ID> "text"             # Moodle DM

# Multi-profile (different schools / accounts)
e3cli profile                                                  # list profiles + URLs
e3cli profile use <name>                                       # switch active profile
e3cli login --profile <name> --url <moodle-url> --save         # add a new school
```

## Hard rules

1. **Never run `e3cli submit` without explicit user confirmation in the same turn.** Even if earlier in the session the user said "do my homework", confirm again right before submitting. Show: assignment title, due date, file path(s), then wait for an explicit "yes/送出/OK".
2. **Academic integrity.** Help the user *work on* the assignment — don't ghostwrite-and-submit. If a request feels like the user is asking you to fully write something they should produce themselves, push back.
3. **Prioritize by deadline.** When the user vaguely asks "what should I do", run `e3cli assignments --due-soon 7` first.
4. **Never read credential files.** `~/.e3cli/credentials.enc`, `~/.e3cli/key`, `~/.e3cli/token` are encrypted/sensitive. Use CLI commands instead.
5. **Don't run `e3cli i`** (interactive TUI). It needs a real terminal and will hang the agent.
6. **Don't run `e3cli login`, `e3cli login --refresh`, or `e3cli setup` yourself.** They are interactive — instruct the user to run them.

## Data locations (reference)

| Path | Content |
|---|---|
| `~/.e3cli/config.toml` | configuration (safe to read for debugging) |
| `~/.e3cli/data/e3cli.db` | local SQLite tracking DB |
| `~/.e3cli/credentials.enc`, `~/.e3cli/key`, `~/.e3cli/token` | **do not read** |
| Download directory (printed by `e3cli sync`) | downloaded materials, organized per course |

## Troubleshooting

| Symptom | Action |
|---|---|
| Auth/token error on any command | Tell user: `e3cli login --refresh` |
| "no current semester" | Try `e3cli sync --all` once, then `e3cli courses --all` |
| Submit rejected as past deadline | Add `--force`, but reconfirm with user first |
| Wrong school or wrong account active | `e3cli profile` to inspect, `e3cli profile use <name>` to switch |
| Command not found | Tool isn't installed — point user to https://github.com/junlinwk/e3cli |
