#!/usr/bin/env bash
# 1. dalga: salt okunur işler (1 araştırma, 2 inceleme, 4 görsel), dış adaylar paralel.
D=$(dirname "$(realpath "$0")")
J=<polycrew>/skills/dis-ajan/dis-ajan.sh
P=<pixlender>
H=$P/.claude/worktrees/deney-hata
export DIS_AJAN_KAYIT=$D/kayit DIS_AJAN_ZAMAN_ASIMI=1500
aday() {  # ad arac model efor
  local ad=$1; shift
  for is in 1 2 4; do
    case $is in 1) k=$P; g=$D/is1-arastirma.md;; 2) k=$H; g=$D/is2-inceleme.md;; 4) k=$P; g=$D/is4-gorsel.md;; esac
    img=()
    [ $is = 4 ] && img=("$P/docs/decisions/img/0044-kilic-kosu.png" "$P/docs/decisions/img/0041-diller.png")
    r=$("$J" "$@" okur "$k" "$g" "${img[@]}" | tail -1)
    echo "$ad is$is $r" >> "$D/dalga1.txt"
  done
}
: > "$D/dalga1.txt"
aday codex-sol   codex gpt-6.1-sol high &
aday codex-astra codex gpt-6-astra xhigh &
aday gem-flash   agy gemini-3.8-flash-high - &
aday gem-pro     agy gemini-3.1-pro-high - &
aday agy-opus    agy claude-opus-4-6-thinking - &
wait
echo bitti >> "$D/dalga1.txt"
