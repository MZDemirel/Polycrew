#!/usr/bin/env bash
# Dış işçi: bir görevi Codex ya da agy (Antigravity) ile etkileşimsiz çalıştırır, her şeyi kaydeder.
#
#   dis-ajan.sh <codex|agy> <model> <efor|-> <okur|yazar> <klasör> <görev.md> [resim ...]
#   dis-ajan.sh kota        (Codex ve agy'nin güncel kotası)
#
# okur : codex -s read-only, agy --mode plan. Dosya değiştirmez.
# yazar: codex -s workspace-write, agy --mode accept-edits. Yalnız bir git worktree'sinde;
#        ana çalışma ağacında reddedilir. Push, --dangerously-* yok.
# Kayıt: $DIS_AJAN_KAYIT (varsayılan ~/.cache/polycrew/dis-ajan)/<zaman>-<araç>-<model>/
#   gorev.md, komut.txt, ham.jsonl|ham.json, hata.txt, rapor.md (son mesaj), sure_sn,
#   kullanim.json (token), cikis_kodu. Son satırda kayıt klasörünün yolunu yazar.
# DIS_AJAN_EK_DIZIN="a:b": codex'in yazar kipte yazabileceği ek klasörler (ör. ~/.cache/uv).
# DIS_AJAN_ZAMAN_ASIMI: saniye (varsayılan 3600).
set -uo pipefail

# Olay günlüğü (polycrew izle, karar 0003). Betiğin kopyası eklentinin dışında çalışıyorsa
# (paralel koşu) olay.py POLYCREW_OLAY'dan, sonra kurulu eklentiden bulunur; bulunmazsa atlanır.
OLAY="${POLYCREW_OLAY:-$(dirname "$(realpath "$0")")/../../hooks/olay.py}"
if [ ! -f "$OLAY" ]; then
  for aday in "${CLAUDE_PLUGIN_ROOT:-/yok}/hooks/olay.py" "$HOME"/.claude/plugins/cache/polycrew/polycrew/*/hooks/olay.py; do
    [ -f "$aday" ] && OLAY=$aday
  done
fi
olay() { [ -f "$OLAY" ] && python3 "$OLAY" yaz "$@" 2>/dev/null; return 0; }
export OLAY

# dis-ajan.sh kota: iki sağlayıcının güncel kotası (0002). Codex: son oturum kaydındaki
# rate_limits (zamanıyla); agy: /quota.
if [ "${1:-}" = kota ]; then
  KOTA_DOSYA=$(mktemp); export KOTA_DOSYA
  python3 - <<'PY'
import glob, json, os, datetime
fs = sorted(glob.glob(os.path.expanduser("~/.codex/sessions/*/*/*/*.jsonl")), key=os.path.getmtime)
son = None
for f in reversed(fs[-20:]):
    for line in open(f, errors="ignore"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        rl = (e.get("payload") or {}).get("rate_limits")
        if rl:
            son = (e.get("timestamp"), rl)
    if son:
        break
kovalar = []
if son:
    ts, rl = son
    for k, ad in (("primary", "5 saat"), ("secondary", "hafta")):
        b = rl.get(k) or {}
        r = datetime.datetime.fromtimestamp(b.get("resets_at", 0)).strftime("%m-%d %H:%M")
        print(f"codex   {ad:7s} kullanılan %{b.get('used_percent')}  yenilenir {r}  (ölçüm {ts})")
        kovalar.append({"saglayici": "codex", "grup": "Codex", "pencere": ad,
                        "kullanilan": b.get("used_percent"), "yenilenir": r, "olcum": ts})
else:
    print("codex   kayıt yok")
json.dump(kovalar, open(os.environ["KOTA_DOSYA"], "w"))
PY
  j=$(cd /tmp && timeout 60 agy -p "/quota" --output-format json < /dev/null 2>/dev/null)
  python3 - "$j" <<'PY'
import json, os, sys
kovalar = json.load(open(os.environ["KOTA_DOSYA"]))
try:
    d = json.loads(sys.argv[1])
    gruplar = d["command"]["data"]["groups"]
except (ValueError, KeyError, TypeError):
    print("agy     okunamadı")
    gruplar = []
# agy'nin ham adları sayfada Codex'inkilerle aynı dilde görünsün.
GRUP = {"Gemini Models": "agy: Gemini", "Claude and GPT models": "agy: Claude/GPT"}
PENCERE = {"weekly": "hafta", "5h": "5 saat"}
for g in gruplar:
    grup = GRUP.get(g["name"], g["name"])
    for b in g["buckets"]:
        kalan = round(100 * b["remaining_fraction"])
        pencere = PENCERE.get(b["window"], b["window"])
        print(f"agy     {grup[:22]:22s} {pencere:7s} kalan %{kalan}  yenilenir {b['reset_time'][5:16]}")
        kovalar.append({"saglayici": "agy", "grup": grup, "pencere": pencere,
                        "kullanilan": 100 - kalan, "yenilenir": b["reset_time"][5:16]})
json.dump(kovalar, open(os.environ["KOTA_DOSYA"], "w"))
PY
  olay kota "kovalar=$(cat "$KOTA_DOSYA")"
  rm -f "$KOTA_DOSYA"
  exit 0
fi

if [ $# -lt 6 ]; then
  sed -n '2,10p' "$0" >&2
  exit 2
fi
arac=$1 model=$2 efor=$3 kip=$4
klasor=$(realpath "$5") gorev=$(realpath "$6")
shift 6
resimler=("$@")
zaman_asimi=${DIS_AJAN_ZAMAN_ASIMI:-3600}

case $arac in codex|agy) ;; *) echo "araç codex ya da agy olmalı: $arac" >&2; exit 2 ;; esac
case $kip in okur|yazar) ;; *) echo "kip okur ya da yazar olmalı: $kip" >&2; exit 2 ;; esac
[ -d "$klasor" ] || { echo "klasör yok: $klasor" >&2; exit 2; }
[ -f "$gorev" ] || { echo "görev dosyası yok: $gorev" >&2; exit 2; }

if [ "$kip" = yazar ]; then
  gd=$(git -C "$klasor" rev-parse --absolute-git-dir 2>/dev/null) || { echo "yazar kipi bir git worktree'si ister: $klasor" >&2; exit 3; }
  cd_=$(git -C "$klasor" rev-parse --path-format=absolute --git-common-dir)
  if [ "$gd" = "$cd_" ]; then
    echo "yazar kipi ana çalışma ağacında çalışmaz; önce: git worktree add .claude/worktrees/dis-<ad> -b dis-<ad> main" >&2
    exit 3
  fi
fi

kok=${DIS_AJAN_KAYIT:-$HOME/.cache/polycrew/dis-ajan}
# Her işçiye giden ortak kurallar (0002: Codex kum havuzunda kancayı atlatmayı seçebiliyor).
kural="Kurallar: git push yapma. Commit kancasını (hook) asla atlatma: --no-verify, core.hooksPath değiştirme ya da kancayı kapatma yok; kanca çalışmazsa commit atma ve nedenini yaz. Yalnız bu klasörde ve kendi dalında çalış."
kayit="$kok/$(date +%Y%m%d-%H%M%S)-$arac-${model//\//_}-$$"
mkdir -p "$kayit"
cp "$gorev" "$kayit/gorev.md"

baslangic=$(date +%s.%N)
baslik=$(grep -m1 -E '^#' "$gorev" | sed 's/^#* *//; s/^Görev: *//')
olay isci_basladi "id=$(basename "$kayit")" "kaynak=$arac" "model=$model" "efor=$efor" "kip=$kip" \
  "klasor=$klasor" "aciklama=${baslik:-$(basename "$gorev")}" "kayit=$kayit" "oturum=${POLYCREW_OTURUM:-}"
if [ "$arac" = codex ]; then
  sandbox=read-only
  [ "$kip" = yazar ] && sandbox=workspace-write
  komut=(codex exec -C "$klasor" -m "$model" -s "$sandbox" --json -o "$kayit/rapor.md")
  [ "$efor" != - ] && komut+=(-c "model_reasoning_effort=\"$efor\"")
  for r in "${resimler[@]}"; do komut+=(-i "$(realpath "$r")"); done
  if [ "$kip" = yazar ]; then
    # Worktree'nin git verisi ana deponun .git'inde: commit için yalnız gereken yerler (0002).
    for e in "$gd" "$cd_/objects" "$cd_/refs/heads" "$cd_/logs"; do [ -d "$e" ] && komut+=(--add-dir "$e"); done
  fi
  DIS_AJAN_EK_DIZIN=${DIS_AJAN_EK_DIZIN-$HOME/.cache/uv}
  if [ "$kip" = yazar ] && [ -n "$DIS_AJAN_EK_DIZIN" ]; then
    IFS=: read -ra ek <<< "$DIS_AJAN_EK_DIZIN"
    for e in "${ek[@]}"; do [ -d "$e" ] && komut+=(--add-dir "$e"); done
  fi
  printf '%q ' "${komut[@]}" > "$kayit/komut.txt"; echo "< gorev.md" >> "$kayit/komut.txt"
  { echo "$kural"; echo; cat "$gorev"; } | timeout "$zaman_asimi" "${komut[@]}" - > "$kayit/ham.jsonl" 2> "$kayit/hata.txt"
  kod=$?
  python3 - "$kayit" <<'EOF'
import json, sys
k = sys.argv[1]
use = None
for line in open(f"{k}/ham.jsonl", errors="ignore"):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("type") == "turn.completed":
        use = e.get("usage")
json.dump(use, open(f"{k}/kullanim.json", "w"))
EOF
else
  mode=plan
  [ "$kip" = yazar ] && mode=accept-edits
  # agy komutları kendi çalışma klasörünü bilmeden boş bir klasörde çalıştırabiliyor (0002):
  # görevin başına klasör satırı eklenir.
  on="Çalışma klasörü: $klasor. Kabuk komutlarını bu klasörde çalıştır (komut aracının çalışma klasörü alanına bu yolu ver)."
  # İzin listesinde olmayan ilk komut bütün işi çıktısız bitirir (0002): izinli komutlar söylenir.
  izinli=$(python3 -c 'import json,os,re;d=json.load(open(os.path.expanduser("~/.gemini/antigravity-cli/settings.json")));print(", ".join(re.sub(r"^command\((.*)\)$",r"\1",a) for a in d.get("permissions",{}).get("allow",[]) if a.startswith("command(")))' 2>/dev/null)
  [ -n "$izinli" ] && on="$on Yalnız şu kabuk komutları izinli: $izinli. Başka bir komut (find, sed, python...) ve ';', '&&', '|' ile birleştirilmiş komutlar işi durdurur; her komutu tek başına çalıştır; dosya bulmak için 'rg --files', aramak için 'rg' ya da 'grep', okumak için dosya okuma aracını kullan."
  for r in "${resimler[@]}"; do on="$on Bakılacak resim: $(realpath "$r")."; done
  istem="$on $kural"$'\n\n'"$(cat "$gorev")"
  komut=(agy -p "$istem" --model "$model" --mode "$mode" --output-format json --print-timeout "${zaman_asimi}s")
  [ "$efor" != - ] && komut+=(--effort "$efor")
  printf '%q ' agy -p "<gorev.md + klasör satırı>" --model "$model" --mode "$mode" --output-format json > "$kayit/komut.txt"
  (cd "$klasor" && timeout "$((zaman_asimi + 60))" "${komut[@]}" < /dev/null > "$kayit/ham.json" 2> "$kayit/hata.txt")
  kod=$?
  python3 - "$kayit" <<'EOF'
import json, sys
k = sys.argv[1]
try:
    d = json.load(open(f"{k}/ham.json"))
except (ValueError, OSError):
    d = {}
open(f"{k}/rapor.md", "w").write(d.get("response", ""))
json.dump({"usage": d.get("usage"), "status": d.get("status"),
           "denied_actions": d.get("denied_actions"), "conversation_id": d.get("conversation_id")},
          open(f"{k}/kullanim.json", "w"))
EOF
fi
bitis=$(date +%s.%N)
python3 -c "print(round($bitis - $baslangic, 1))" > "$kayit/sure_sn"
echo "$kod" > "$kayit/cikis_kodu"
olay isci_bitti "id=$(basename "$kayit")" "kaynak=$arac" "cikis=$kod" "sure_sn=$(cat "$kayit/sure_sn")" \
  "kullanim=$(cat "$kayit/kullanim.json" 2>/dev/null || echo null)" "kayit=$kayit"
echo "$kayit"
exit "$kod"
