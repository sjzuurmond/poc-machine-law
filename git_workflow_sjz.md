# Git Workflow for Forked Repository

## Branch Structure

- **`main`** - Clean mirror of upstream (never commit here)
- **`develop-sjz`** - Your primary working branch (default)
- **`feature/*`** - Temporary branches for specific features

## Day-to-Day Development

### Starting a new feature

```bash
# Switch to your working branch and update
git checkout develop-sjz
git pull origin develop-sjz

# Create a new feature branch
git checkout -b feature/your-feature-name
```

### Working on your feature

```bash
# Make changes, then commit
git add .
git commit -m "descriptive message"

# Continue working with more commits as needed
```

### Completing a feature

```bash
# Switch back to develop-sjz
git checkout develop-sjz

# Merge your feature
git merge feature/your-feature-name

# Push to your fork
git push origin develop-sjz

# Clean up the feature branch
git branch -d feature/your-feature-name
```

## Syncing with Upstream

Run this weekly or whenever you want to pull in upstream changes:

```bash
# Update main from upstream
git checkout main
git fetch upstream
git reset --hard upstream/main
git submodule update --init --recursive
git push origin main --force

# Bring upstream changes into your work
git checkout develop-sjz
git merge main
# Resolve any conflicts if they arise
git push origin develop-sjz
```

## Quick Reference Commands

```bash
git checkout develop-sjz              # Switch to your working branch
git checkout -b feature/xyz           # Create new feature branch
git merge feature/xyz                 # Merge feature into develop-sjz
git branch -d feature/xyz             # Delete feature branch after merge
git remote -v                         # Check your remotes (origin + upstream)
git status                            # Check current state
git log --oneline -10                 # View recent commits
```

## Key Principles

- **Never commit directly to `main`** - it should always mirror upstream
- **Always branch off `develop-sjz`** for new work
- **Merge upstream updates regularly** into `develop-sjz` to avoid big conflicts later
- **Feature branches are optional** - for small changes, you can commit directly to `develop-sjz`
- **Force push to `main` is safe** - you're just syncing with upstream

## Remotes

```bash
origin     → Your fork (git@github.com:sjzuurmond/repo-name.git)
upstream   → Original repo (where you pull updates from)
```

You have **read/write** access to `origin` and **read-only** access to `upstream`.