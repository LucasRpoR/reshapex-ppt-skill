#!/usr/bin/env bash
# ReshapeX Brief Skill — setup script
# Installs the MCP server and registers the skill in Claude Code.
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/reshapex-mcp"
VENV_DIR="$INSTALL_DIR/.venv"
CONFIG_DIR="$HOME/.config/reshapex-mcp"
SKILL_DIR="$HOME/.claude/skills/reshapex-brief"

echo "=== ReshapeX Brief Skill — Setup ==="
echo ""

# 1. Copy server
echo "[1/5] Installing MCP server..."
mkdir -p "$INSTALL_DIR"
cp "$REPO_DIR/server.py" "$INSTALL_DIR/server.py"

# 2. Create venv
echo "[2/5] Creating Python environment..."
if command -v uv &>/dev/null; then
  uv venv "$VENV_DIR" --python python3
  "$VENV_DIR/bin/pip" install -q -r "$REPO_DIR/requirements.txt"
else
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install -q -r "$REPO_DIR/requirements.txt"
fi

# 3. Copy skill
echo "[3/5] Installing skill..."
mkdir -p "$SKILL_DIR"
cp "$REPO_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"

# 4. Check for credentials.json
echo "[4/5] Checking Google credentials..."
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/credentials.json" ]; then
  if [ -f "$REPO_DIR/credentials.json" ]; then
    cp "$REPO_DIR/credentials.json" "$CONFIG_DIR/credentials.json"
    echo "     credentials.json copied from repo."
  else
    echo ""
    echo "  ! credentials.json not found."
    echo "    Ask your team lead for the file and place it at:"
    echo "    $CONFIG_DIR/credentials.json"
    echo "    Then re-run this script or continue manually."
    echo ""
  fi
else
  echo "     credentials.json already present."
fi

# 5. Register MCP server in Claude Code
echo "[5/5] Registering MCP server in Claude Code..."
CLAUDE_JSON="$HOME/.claude.json"
PYTHON_PATH="$VENV_DIR/bin/python"
SERVER_PATH="$INSTALL_DIR/server.py"

if [ -f "$CLAUDE_JSON" ]; then
  python3 - <<PYEOF
import json, pathlib, sys

path = pathlib.Path("$CLAUDE_JSON")
d = json.loads(path.read_text())
if "mcpServers" not in d:
    d["mcpServers"] = {}
d["mcpServers"]["reshapex-slides"] = {
    "type": "stdio",
    "command": "$PYTHON_PATH",
    "args": ["$SERVER_PATH"],
    "env": {}
}
path.write_text(json.dumps(d, indent=2, ensure_ascii=False))
print("     MCP server registered in ~/.claude.json")
PYEOF
else
  echo "     ~/.claude.json not found — creating it..."
  python3 - <<PYEOF
import json, pathlib
path = pathlib.Path("$CLAUDE_JSON")
d = {"mcpServers": {"reshapex-slides": {"type": "stdio", "command": "$PYTHON_PATH", "args": ["$SERVER_PATH"], "env": {}}}}
path.write_text(json.dumps(d, indent=2, ensure_ascii=False))
print("     ~/.claude.json created with MCP server entry.")
PYEOF
fi

echo ""
echo "=== Done! ==="
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code so it picks up the new MCP server."
if [ ! -f "$CONFIG_DIR/credentials.json" ]; then
echo "  2. Place credentials.json in $CONFIG_DIR/"
echo "  3. Use /reshapex-brief in Claude Code — the first run will ask you to authenticate with Google."
else
echo "  2. Use /reshapex-brief in Claude Code — the first run will ask you to authenticate with Google."
fi
echo ""
