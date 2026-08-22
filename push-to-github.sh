#!/bin/bash
set -e

REPO_DIR="/root/the tank project"
REMOTE="git@github.com:shashiguptaazm-droid/The-Tank-Project.git"
LOG="/root/push-tank.log"

exec > "$LOG" 2>&1

echo "===== $(date): Starting push ====="

cd "$REPO_DIR"

# Remove any embedded .git dirs inside tools (leftover from cloned repos)
echo "Removing nested .git dirs..."
find . -name ".git" -not -path "./.git/*" -type d -exec rm -rf {} + 2>/dev/null || true

# Init if needed
if [ ! -d ".git" ]; then
    git init
    echo "Initialized git repo"
fi

# Add remote if not present
if ! git remote | grep -q origin; then
    git remote add origin "$REMOTE"
    echo "Added remote origin"
fi

# Stage everything
echo "Staging files..."
git add -A

# Commit
echo "Committing..."
git commit -m "Initial commit: The Tank Project

- TankOS architecture and modules
- ROS2 workspace (tank_ws)
- Hardware schematics, wiring diagrams
- CAD files and firmware
- Documentation and runbooks

🤖 Generated with Codebuff
Co-Authored-By: Codebuff <noreply@codebuff.com>" || echo "Nothing to commit"

# Push
echo "Pushing to GitHub..."
git branch -M main
git push -u origin main --force

echo "===== $(date): Done ====="