#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="${HOME}/.claude/skills/youtube-techcrush"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills/youtube-techcrush"

if [ ! -f "${SRC}/SKILL.md" ]; then
  echo "Error: run this from the repository root." >&2
  exit 1
fi

mkdir -p "${SKILL_DIR}"
cp -R "${SRC}/." "${SKILL_DIR}/"
echo "Installed to ${SKILL_DIR}"
echo "Next: cd to your project and run"
echo "  node ${SKILL_DIR}/scripts/doctor.js"
