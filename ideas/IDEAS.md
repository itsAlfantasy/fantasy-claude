# Ideas

## Obsidian Integration
Configure Obsidian directly from the TUI configurator:
- Ask user for vault path
- Write vault path to `~/.claude/CLAUDE.md` (profile-level)
- Suggest installing obsidian-related skills (`obsidian:obsidian-cli`, `obsidian:obsidian-markdown`, etc.)
- Optionally add a statusline element showing vault note count or last modified note

## Session Git Cleanup Hook

A `SessionStart` hook that runs on every new session to keep local branches in sync with remote.

### What it does
1. Checks if the current directory is a git repo (skips otherwise)
2. Checks if there's at least one remote configured (skips otherwise)
3. Runs `git fetch --all --prune` to update all remotes and remove stale remote-tracking refs
4. Finds local branches whose remote tracking branch is gone (`[gone]`) and deletes them with **safe delete** (`git branch -d`, not `-D`) — branches with unmerged local changes are preserved

### Output
- 🔄 Fetching status
- 📥 List of updated branches (or "Nessun branch aggiornato")
- 🗑️ List of deleted local branches (or "Nessun branch locale da eliminare")
- ⚠️ Warning for branches skipped due to unmerged local changes
- 📂 Info message when not in a git repo or no remote is configured
- 🏁 Done message at the end

### How output is displayed
Hook stdout with `exit 0` is passed to Claude as context. It is shown to the user as part of Claude's **first response** in the session — not proactively. The user must send at least one message to trigger it. This is a Claude Code limitation: hooks cannot make Claude respond proactively.

### Script location
`~/.claude/hooks/session-git-cleanup.sh`

### Full script
```bash
#!/bin/bash

# Only run if we're in a git repo
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "📂 Non siamo in un repo git, skip."
  exit 0
fi

# Only run if there's at least one remote
if [ -z "$(git remote 2>/dev/null)" ]; then
  echo "📂 Repo git locale senza remote, skip."
  exit 0
fi

echo "🔄 Fetching all remotes and pruning stale branches..."
echo ""

fetch_output=$(git fetch --all --prune 2>&1)

updated=$(echo "$fetch_output" | grep -E '^\s+[a-f0-9]+\.\.[a-f0-9]+|^\s*\* \[new' | sed 's/^[[:space:]]*/  /')
if [ -n "$updated" ]; then
  echo "📥 Branch aggiornati:"
  echo "$updated"
else
  echo "📥 Nessun branch aggiornato."
fi

echo ""

gone_branches=$(git branch -vv 2>/dev/null | grep ': gone]' | awk '{print $1}')
if [ -n "$gone_branches" ]; then
  echo "🗑️  Branch locali eliminati:"
  echo "$gone_branches" | while read -r branch; do
    if git branch -d "$branch" 2>/dev/null; then
      echo "  - $branch"
    else
      echo "  ⚠️  $branch (skippato: ha modifiche locali non mergiate)"
    fi
  done
else
  echo "✅ Nessun branch locale da eliminare."
fi

echo ""
echo "🏁 Done!"

exit 0
```

### Settings entry (`~/.claude/settings.json`)
```json
{
  "SessionStart": [
    {
      "matcher": "startup",
      "hooks": [
        {
          "type": "command",
          "command": "bash ~/.claude/hooks/session-git-cleanup.sh",
          "timeout": 30,
          "statusMessage": "Fetching remotes and cleaning gone branches..."
        }
      ]
    }
  ]
}
```

### CLAUDE.md entry (`~/CLAUDE.md`)
Add this so Claude relays the hook output at the start of each session:
```markdown
## Session Start
- When you receive output from the `session-git-cleanup` hook, always relay it to the user as your first message.
```

## Attribution Settings

Configure Claude Code's commit and PR attribution settings from the TUI configurator or CLI.

Could live under the Integrations screen or a new Settings screen. Would read/write the attribution keys in `~/.claude/settings.json`.

Reference: https://code.claude.com/docs/en/settings#attribution-settings
