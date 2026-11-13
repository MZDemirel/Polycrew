#!/usr/bin/env bash
# SessionStart: if the project has a notes file (NEXT_SESSION.md, or SONRAKI_OTURUM.md from before
# 0.5.0), put the start of its first section into the context. Without the file it prints nothing,
# so projects that do not use this workflow are not affected.
# Sections are found by position, not by heading text, so the file can be in any language:
# the first "## " section is "where we left off", the second one is "next".
set -euo pipefail
dir="${CLAUDE_PROJECT_DIR:-$PWD}"
file="$dir/NEXT_SESSION.md"
[ -f "$file" ] || file="$dir/SONRAKI_OTURUM.md"
[ -f "$file" ] || exit 0
# 0019: Claude kotası masaüstü uygulamasından (varsa); sessiz, en çok birkaç saniye.
python3 "$(dirname "$0")/quota.py" desktop > /dev/null 2>&1 || true
echo "This project uses the polycrew workflow (notes: $(basename "$file"))."
echo "Start the session with /session-start; close it with /session-end."
echo
sed -n '1,4p' "$file"
echo
# 0018: sınır awk'ın içinde; "| head" pipefail altında SIGPIPE (141) ile kancayı düşürebiliyordu.
awk '/^## /{n++} n==2{exit} n==1 && c++<40' "$file"
echo
awk '/^## /{n++} n==3{exit} n==2 && /^### / && c++<10' "$file"
