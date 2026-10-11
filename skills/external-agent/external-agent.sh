#!/usr/bin/env bash
# External worker: runs a task non-interactively with Codex or agy (Antigravity) and logs everything.
#
#   external-agent.sh <codex|agy> <model> <effort|-> <read|write> <dir> <task.md> [image ...]
#   external-agent.sh quota        (current quota of Codex and agy)
#
# read : codex -s read-only, agy --mode plan. Changes no files.
# write: codex -s workspace-write, agy --mode accept-edits. Only in a git worktree;
#        refused in the main working tree. No push, no --dangerously-*.
# Log: $EXTERNAL_AGENT_LOG (default ~/.cache/polycrew/dis-ajan)/<time>-<tool>-<model>/
#   gorev.md, komut.txt, ham.jsonl|ham.json, hata.txt, rapor.md (last message), sure_sn,
#   kullanim.json (tokens), cikis_kodu, kota.json (quota before/after and the difference).
#   The last output line is the log folder's path.
# EXTERNAL_AGENT_EXTRA_DIRS="a:b": extra folders codex may write to in write mode (e.g. ~/.cache/uv).
# EXTERNAL_AGENT_TIMEOUT: seconds (default 3600).
# EXTERNAL_AGENT_NO_QUOTA=1: skip the quota reading before and after the run.
# Exit codes: 2 bad arguments, 3 write mode outside a worktree, 4 the tool is not installed;
# otherwise the tool's own exit code.
# The old variable names (DIS_AJAN_KAYIT, DIS_AJAN_EK_DIZIN, DIS_AJAN_ZAMAN_ASIMI, POLYCREW_OLAY,
# POLYCREW_OTURUM) are still read as a fallback. Log file names and event fields stay Turkish (0007).
set -uo pipefail

# Olay günlüğü (polycrew izle, karar 0003). Betiğin kopyası eklentinin dışında çalışıyorsa
# (paralel koşu) events.py POLYCREW_EVENTS_SCRIPT'ten, sonra kurulu eklentiden bulunur; bulunmazsa atlanır.
OLAY="${POLYCREW_EVENTS_SCRIPT:-${POLYCREW_OLAY:-$(dirname "$(realpath "$0")")/../../hooks/events.py}}"
if [ ! -f "$OLAY" ]; then
  for aday in "${CLAUDE_PLUGIN_ROOT:-/yok}/hooks/events.py" "$HOME"/.claude/plugins/cache/polycrew/polycrew/*/hooks/events.py; do
    [ -f "$aday" ] && OLAY=$aday
  done
fi
olay() { [ -f "$OLAY" ] && python3 "$OLAY" write "$@" 2>/dev/null; return 0; }
export OLAY

# Kota okuma (0002, 0010). Codex: son oturum kaydındaki rate_limits (zamanıyla); agy: /quota.
# Her fonksiyon kova listesini verilen dosyaya JSON olarak yazar; KOTA_SESSIZ=1 değilse satırlarını basar.
# Günlüğe Türkçe pencere adı yazılır (şema), ekrana İngilizce. "hassas" koşu başına fark içindir.
kota_codex() {
  KOTA_DOSYA=$1 CODEX_VAR=$(command -v codex > /dev/null 2>&1 && echo 1 || echo 0) python3 - <<'PY'
import glob, json, os, datetime, time
sessiz = os.environ.get("KOTA_SESSIZ") == "1"
def yaz(*a):
    if not sessiz:
        print(*a)
kovalar = []
if os.environ.get("CODEX_VAR") != "1":
    yaz("codex   not installed")
else:
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
    ETIKET = {"5 saat": "5 hours", "hafta": "week"}
    if son:
        ts, rl = son
        for k, ad in (("primary", "5 saat"), ("secondary", "hafta")):
            b = rl.get(k) or {}
            r = datetime.datetime.fromtimestamp(b.get("resets_at", 0)).strftime("%m-%d %H:%M")
            yaz(f"codex   {ETIKET[ad]:7s} used {b.get('used_percent')}%  resets {r}  (measured {ts})")
            # Son kayıt eski bir pencereden kalmış olabilir: yenilenme saati geçtiyse yeni pencere 0'dan başlar (0010).
            gecti = bool(b.get("resets_at")) and b["resets_at"] <= time.time()
            kovalar.append({"saglayici": "codex", "grup": "Codex", "pencere": ad,
                            "kullanilan": b.get("used_percent"), "hassas": 0.0 if gecti else b.get("used_percent"),
                            "yenilenir": r, "olcum": ts})
    else:
        yaz("codex   no record")
json.dump(kovalar, open(os.environ["KOTA_DOSYA"], "w"))
PY
}

kota_agy() {
  if ! command -v agy > /dev/null 2>&1; then
    [ "${KOTA_SESSIZ:-}" = 1 ] || echo "agy     not installed"
    echo "[]" > "$1"
    return 0
  fi
  local j
  j=$(cd /tmp && timeout 60 agy -p "/quota" --output-format json < /dev/null 2>/dev/null)
  KOTA_DOSYA=$1 python3 - "$j" <<'PY'
import json, os, sys
sessiz = os.environ.get("KOTA_SESSIZ") == "1"
kovalar = []
try:
    d = json.loads(sys.argv[1])
    gruplar = d["command"]["data"]["groups"]
except (ValueError, KeyError, TypeError):
    if not sessiz:
        print("agy     could not be read")
    gruplar = []
# agy'nin ham adları sayfada Codex'inkilerle aynı dilde görünsün.
GRUP = {"Gemini Models": "agy: Gemini", "Claude and GPT models": "agy: Claude/GPT"}
PENCERE = {"weekly": "hafta", "5h": "5 saat"}
for g in gruplar:
    grup = GRUP.get(g["name"], g["name"])
    for b in g["buckets"]:
        kalan = round(100 * b["remaining_fraction"])
        pencere = PENCERE.get(b["window"], b["window"])
        etiket = {"5 saat": "5 hours", "hafta": "week"}.get(pencere, pencere)
        if not sessiz:
            print(f"agy     {grup[:22]:22s} {etiket:7s} left {kalan}%  resets {b['reset_time'][5:16]}")
        kovalar.append({"saglayici": "agy", "grup": grup, "pencere": pencere, "kullanilan": 100 - kalan,
                        "hassas": round(100 * (1 - b["remaining_fraction"]), 1),
                        "yenilenir": b["reset_time"][5:16]})
json.dump(kovalar, open(os.environ["KOTA_DOSYA"], "w"))
PY
}

# kota_yuzde <araç> <model>: bu koşunun harcadığı pencerenin kullanım yüzdesi ve pencere adı;
# okunamazsa boş. Codex: 5 saatlik pencere. agy: modele göre grup, 5 saatlik pencere, yoksa haftalık.
kota_yuzde() {
  local f
  f=$(mktemp)
  KOTA_SESSIZ=1 "kota_$1" "$f" > /dev/null 2>&1
  python3 - "$f" "$1" "$2" <<'PY'
import json, sys
try:
    kovalar = json.load(open(sys.argv[1]))
except (ValueError, OSError):
    kovalar = []
arac, model = sys.argv[2], sys.argv[3].lower()
if arac == "agy":
    grup = "agy: Claude/GPT" if ("claude" in model or "gpt" in model) else "agy: Gemini"
    kovalar = [k for k in kovalar if k.get("grup") == grup]
for pencere in ("5 saat", "hafta"):
    for k in kovalar:
        if k.get("pencere") == pencere and isinstance(k.get("hassas"), (int, float)):
            print(k["hassas"], pencere)
            raise SystemExit
PY
  rm -f "$f"
}

if [ "${1:-}" = quota ]; then
  f1=$(mktemp); f2=$(mktemp)
  kota_codex "$f1"
  kota_agy "$f2"
  olay kota "kovalar=$(python3 -c 'import json,sys; print(json.dumps([{k: v for k, v in b.items() if k != "hassas"} for f in sys.argv[1:] for b in json.load(open(f))]))' "$f1" "$f2")"
  rm -f "$f1" "$f2"
  exit 0
fi

if [ $# -lt 6 ]; then
  sed -n '2,9p' "$0" >&2
  exit 2
fi
arac=$1 model=$2 efor=$3 kip=$4
klasor=$(realpath "$5") gorev=$(realpath "$6")
shift 6
resimler=("$@")
zaman_asimi=${EXTERNAL_AGENT_TIMEOUT:-${DIS_AJAN_ZAMAN_ASIMI:-3600}}

case $arac in codex|agy) ;; *) echo "tool must be codex or agy: $arac" >&2; exit 2 ;; esac
# Günlükteki kip değerleri eski adlarıyla kalır (şema); komut satırı read|write alır.
case $kip in read) kip=okur ;; write) kip=yazar ;; *) echo "mode must be read or write: $kip" >&2; exit 2 ;; esac
[ -d "$klasor" ] || { echo "no such folder: $klasor" >&2; exit 2; }
[ -f "$gorev" ] || { echo "no such task file: $gorev" >&2; exit 2; }

if [ "$kip" = yazar ]; then
  gd=$(git -C "$klasor" rev-parse --absolute-git-dir 2>/dev/null) || { echo "write mode needs a git worktree: $klasor" >&2; exit 3; }
  cd_=$(git -C "$klasor" rev-parse --path-format=absolute --git-common-dir)
  if [ "$gd" = "$cd_" ]; then
    echo "write mode does not run in the main working tree; first: git worktree add .claude/worktrees/ext-<name> -b ext-<name> main" >&2
    exit 3
  fi
fi

# Araç yoksa kayıt klasörü açmadan, anlaşılır bir iletiyle dur (0009).
if ! command -v "$arac" > /dev/null 2>&1; then
  echo "$arac is not installed or not on PATH; install it, or use a Claude role instead (see roster.md)" >&2
  exit 4
fi

kok=${EXTERNAL_AGENT_LOG:-${DIS_AJAN_KAYIT:-$HOME/.cache/polycrew/dis-ajan}}
# Her işçiye giden ortak kurallar (0002: Codex kum havuzunda kancayı atlatmayı seçebiliyor).
# rules/git.md'nin kısa kopyası (0006): dış işçi o dosyayı okuyamaz; biri değişince öbürü de değişir.
kural="Rules: do not git push. Never bypass a commit hook: no --no-verify, no changing core.hooksPath, no disabling the hook; if a hook fails, do not commit and report why. Do not add a Co-Authored-By line or any other tool signature to commit messages. Do not delete branches. Work only in this folder and on your own branch."
kayit="$kok/$(date +%Y%m%d-%H%M%S)-$arac-${model//\//_}-$$"
mkdir -p "$kayit"
cp "$gorev" "$kayit/gorev.md"

# Koşudan önce kota (0010); sonra yeniden okunur, fark kota.json'a ve isci_bitti olayına yazılır.
kota_once=""
[ "${EXTERNAL_AGENT_NO_QUOTA:-}" = 1 ] || kota_once=$(kota_yuzde "$arac" "$model")
baslangic=$(date +%s.%N)
baslik=$(grep -m1 -E '^#' "$gorev" | sed 's/^#* *//; s/^Görev: *//; s/^Task: *//')
olay isci_basladi "id=$(basename "$kayit")" "kaynak=$arac" "model=$model" "efor=$efor" "kip=$kip" \
  "klasor=$klasor" "aciklama=${baslik:-$(basename "$gorev")}" "kayit=$kayit" "oturum=${POLYCREW_SESSION:-${POLYCREW_OTURUM:-}}"
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
  ek_dizin=${EXTERNAL_AGENT_EXTRA_DIRS-${DIS_AJAN_EK_DIZIN-$HOME/.cache/uv}}
  if [ "$kip" = yazar ] && [ -n "$ek_dizin" ]; then
    IFS=: read -ra ek <<< "$ek_dizin"
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
  on="Working folder: $klasor. Run shell commands in this folder (pass this path as the working directory of the command tool)."
  # İzin listesinde olmayan ilk komut bütün işi çıktısız bitirir (0002): izinli komutlar söylenir.
  izinli=$(python3 -c 'import json,os,re;d=json.load(open(os.path.expanduser("~/.gemini/antigravity-cli/settings.json")));print(", ".join(re.sub(r"^command\((.*)\)$",r"\1",a) for a in d.get("permissions",{}).get("allow",[]) if a.startswith("command(")))' 2>/dev/null)
  [ -n "$izinli" ] && on="$on Only these shell commands are allowed: $izinli. Any other command (find, sed, python...) and commands chained with ';', '&&' or '|' stop the whole job; run each command on its own; use 'rg --files' to find files, 'rg' or 'grep' to search, and the file reading tool to read."
  for r in "${resimler[@]}"; do on="$on Image to look at: $(realpath "$r")."; done
  istem="$on $kural"$'\n\n'"$(cat "$gorev")"
  komut=(agy -p "$istem" --model "$model" --mode "$mode" --output-format json --print-timeout "${zaman_asimi}s")
  [ "$efor" != - ] && komut+=(--effort "$efor")
  printf '%q ' agy -p "<gorev.md + folder line>" --model "$model" --mode "$mode" --output-format json > "$kayit/komut.txt"
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
kota_fark=""
if [ "${EXTERNAL_AGENT_NO_QUOTA:-}" != 1 ]; then
  kota_sonra=$(kota_yuzde "$arac" "$model")
  cakisma=0
  [ -f "$OLAY" ] && cakisma=$(python3 "$OLAY" overlap "$(basename "$kayit")" "$arac" "$baslangic" 2>/dev/null || echo 0)
  kota_fark=$(python3 - "$kayit/kota.json" "$kota_once" "$kota_sonra" "$cakisma" <<'KOTA'
import json, sys
dosya, once, sonra, cakisma = sys.argv[1:5]
def ayir(m):
    p = m.split(None, 1)
    try:
        return float(p[0]), (p[1] if len(p) > 1 else None)
    except (ValueError, IndexError):
        return None, None
o, pencere = ayir(once)
s, pencere2 = ayir(sonra)
fark, neden = None, None
if o is None or s is None:
    neden = "quota could not be read"
elif pencere != pencere2 or s < o:
    neden = "the quota window reset during the run"
elif cakisma.strip() == "1":
    neden = "another run of the same tool overlapped; the share cannot be separated"
else:
    fark = round(s - o, 1)
json.dump({"once": o, "sonra": s, "fark": fark, "pencere": pencere2 or pencere, "neden": neden}, open(dosya, "w"))
print("" if fark is None else fark)
KOTA
)
fi
olay isci_bitti "id=$(basename "$kayit")" "kaynak=$arac" "cikis=$kod" "sure_sn=$(cat "$kayit/sure_sn")" \
  "kullanim=$(cat "$kayit/kullanim.json" 2>/dev/null || echo null)" "kayit=$kayit" ${kota_fark:+"kota=$kota_fark"}
echo "$kayit"
exit "$kod"
