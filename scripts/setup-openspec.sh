#!/usr/bin/env bash
# Configure global OpenSpec for Superspec + generate Claude Code skills/commands.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Configuring global OpenSpec (Superspec workflows)"
openspec config set profile custom
openspec config set delivery both

if command -v jq >/dev/null 2>&1; then
  CONFIG_PATH="$(openspec config path)"
  TMP="$(mktemp)"
  jq '.workflows = ["propose","explore","new","continue","apply","ff","sync","archive","bulk-archive","verify","onboard"]' \
    "$CONFIG_PATH" > "$TMP" && mv "$TMP" "$CONFIG_PATH"
  echo "    Workflows: $(openspec config get workflows)"
else
  echo "    Warning: jq not found. Run: openspec config profile"
  echo "    Enable all workflows manually, then re-run this script."
fi

echo "==> Initializing OpenSpec for Claude Code"
openspec init --tools claude --profile custom --force

echo "==> Writing project openspec/config.yaml"
cat > openspec/config.yaml <<'EOF'
schema: superspec

context: |
  Harness: OpenSpec (Superspec schema) + Superpowers skills in Claude Code.
EOF

echo "==> Refreshing Claude integration"
openspec update

echo "==> Validating schemas"
openspec schemas
openspec validate --specs 2>/dev/null || true

echo ""
echo "Done. Install Superpowers in Claude Code:"
echo "  /plugin marketplace add obra/superpowers-marketplace"
echo "  /plugin install superpowers@superpowers-marketplace"
