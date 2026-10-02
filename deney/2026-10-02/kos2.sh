#!/usr/bin/env bash
# 2. dalga: A2 kodlama yarışı, dış adaylar; iki alt dalga hâlinde (makine yükü).
D=$(dirname "$(realpath "$0")")
J=<polycrew>/skills/dis-ajan/dis-ajan.sh
P=<pixlender>
export DIS_AJAN_KAYIT=$D/kayit DIS_AJAN_ZAMAN_ASIMI=3000
export DIS_AJAN_EK_DIZIN="$HOME/.cache/uv:$HOME/.cache/pyright-python:$HOME/.npm"
aday() {  # ad arac model efor
  local ad=$1; shift
  r=$(nice -n 10 "$J" "$@" yazar "$P/.claude/worktrees/deney-a2-$ad" "$D/is3-a2.md" | tail -1)
  echo "$ad is3 $r" >> "$D/dalga2.txt"
}
: > "$D/dalga2.txt"
aday codex-sol codex gpt-6.1-sol high &
aday gem-flash agy gemini-3.8-flash-high - &
wait
aday codex-astra codex gpt-6-astra xhigh &
aday gem-pro agy gemini-3.1-pro-high - &
aday agy-opus agy claude-opus-4-6-thinking - &
wait
echo bitti >> "$D/dalga2.txt"
