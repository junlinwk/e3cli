# E3CLI — Claude Code Integration

## What is this?

e3cli is a CLI tool for NYCU's E3 Moodle platform. It can sync courses, download materials, check assignments, and submit homework.

## How to use e3cli in this project

```bash
# Check for new assignments
e3cli sync

# List upcoming assignments
e3cli assignments --due-soon 7

# Download course materials
e3cli download --course "COURSE_NAME"

# Submit completed assignment
e3cli submit <ASSIGNMENT_ID> <FILE_PATH>

# Interactive mode
e3cli i
```

## When a new assignment is detected

1. Run `e3cli sync` to pull latest data
2. Run `e3cli assignments` to see what's new
3. Check `~/e3-downloads/` for assignment descriptions
4. **Always confirm with the user before submitting**

## Token expired?

```bash
e3cli login --refresh
```

## Full agent instructions

See `e3cli/agent_prompt.md` for detailed automation workflow.
