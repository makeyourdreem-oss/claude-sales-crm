#!/bin/bash
# Claude Sales CRM Toolkit — Installer
set -e

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
SKILLS_DIR="$CLAUDE_DIR/skills"

echo "Installing Claude Sales CRM Toolkit..."
echo "  → Claude dir: $CLAUDE_DIR"

mkdir -p "$SKILLS_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for skill in crm-init add-to-crm meeting-notes sync-messenger daily-digest; do
    if [ -d "$SCRIPT_DIR/skills/$skill" ]; then
        cp -r "$SCRIPT_DIR/skills/$skill" "$SKILLS_DIR/"
        echo "  ✓ /$skill"
    fi
done

if command -v pip &> /dev/null; then
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -q -r "$SCRIPT_DIR/requirements.txt" || echo "  ⚠ pip install failed — install manually: pip install -r requirements.txt"
    fi
fi

cat <<'EOF'

╔══════════════════════════════════════════════════════════╗
║  Installed!                                              ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Next: open Claude Code and run                          ║
║                                                          ║
║      /crm-init                                           ║
║                                                          ║
║  to configure your CRM (Google Sheets + .env).           ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

EOF
