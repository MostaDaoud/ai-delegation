#!/usr/bin/env bash
# Install script for ai-delegation
# Usage: bash install.sh

set -euo pipefail

SKILL_DIR="$HOME/.agents/skills"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing ai-delegation skill..."

# Create skills directory
mkdir -p "$SKILL_DIR"

# Copy main skill
cp -r "$SCRIPT_DIR/ai-delegation" "$SKILL_DIR/"
echo "  Installed: ai-delegation"

# Copy sub-skills (installed as sibling folders, Agent Skills layout)
for skill in "$SCRIPT_DIR/skills"/ai-delegation-*/; do
    if [ -d "$skill" ]; then
        skill_basename=$(basename "$skill")
        cp -r "$skill" "$SKILL_DIR/"
        echo "  Installed: $skill_basename"
    fi
done

echo ""
echo "Installation complete!"
echo "Test with: /ai-delegation"
echo "  or: /ai-delegation decide | wire | cost | audit"
