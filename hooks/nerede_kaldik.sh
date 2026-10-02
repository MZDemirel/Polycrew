#!/usr/bin/env bash
# SessionStart: projenin SONRAKI_OTURUM.md dosyası varsa "Nerede kaldık" bölümünün başını
# bağlama koyar. Dosya yoksa hiçbir şey yazmaz; bu düzeni kullanmayan projeler etkilenmez.
set -euo pipefail
dir="${CLAUDE_PROJECT_DIR:-$PWD}"
file="$dir/SONRAKI_OTURUM.md"
[ -f "$file" ] || exit 0
echo "Bu proje çalışma düzenini kullanıyor (polycrew eklentisi)."
echo "Oturuma /oturum-ac ile başla; kapanışta /oturum-kapat."
echo
sed -n '1,4p' "$file"
echo
awk '/^## Nerede kaldık/{on=1} /^## Sıradaki/{exit} on' "$file" | head -n 40
echo
awk '/^## Sıradaki/{on=1} on && /^### /{print}' "$file" | head -n 10
