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

# macOS uyumu (0013): bash 3.2, BSD date (%N yok), GNU timeout yok, eski macOS'ta realpath yok.
tam_yol() { realpath "$1" 2> /dev/null || python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"; }
simdi() { python3 -c 'import time; print(time.time())'; }
# zaman_sinirli <sn> <komut...>: timeout, yoksa gtimeout, yoksa python3 (süre dolunca süreç grubu
# kesilir, çıkış 124 timeout gibi). _POLYCREW_ZAMAN=python python yolunu zorlar (test).
zaman_sinirli() {
  local sn=$1; shift
  if [ "${_POLYCREW_ZAMAN:-}" != python ]; then
    if command -v timeout > /dev/null 2>&1; then timeout "$sn" "$@"; return $?; fi
    if command -v gtimeout > /dev/null 2>&1; then gtimeout "$sn" "$@"; return $?; fi
  fi
  python3 -c '
import os, signal, subprocess, sys
p = None
bekleyen = []  # süreç doğmadan gelen sinyal kaybolmasın
def ilet(sinyal, _):
    if p is None:
        bekleyen.append(sinyal)
        return
    try:
        os.killpg(p.pid, sinyal)
    except ProcessLookupError:
        pass
signal.signal(signal.SIGINT, ilet)
signal.signal(signal.SIGTERM, ilet)
p = subprocess.Popen(sys.argv[2:], start_new_session=True)
for s in bekleyen:
    ilet(s, None)
try:
    kod = p.wait(timeout=float(sys.argv[1]))
except subprocess.TimeoutExpired:
    ilet(signal.SIGTERM, None)
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    ilet(signal.SIGKILL, None)  # lider TERM ile çıksa da gruptaki torunlar kalmasın
    p.wait()
    sys.exit(124)
sys.exit(kod if kod >= 0 else 128 - kod)
' "$sn" "$@"
}

# Olay günlüğü (polycrew izle, karar 0003). Betiğin kopyası eklentinin dışında çalışıyorsa
# (paralel koşu) events.py POLYCREW_EVENTS_SCRIPT'ten, sonra kurulu eklentiden bulunur; bulunmazsa atlanır.
OLAY="${POLYCREW_EVENTS_SCRIPT:-${POLYCREW_OLAY:-$(dirname "$(tam_yol "$0")")/../../hooks/events.py}}"
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
    def olcum_zamani(t):
        try:
            return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError, AttributeError):
            return None
    # 0018: en yeni 5 dosyada ölçüm zamanı en yeni kayıt (dosyanın değişme zamanı yanıltabilir);
    # onlarda kayıt yoksa geriye, en çok 20 dosyaya kadar.
    son = None
    for sira, f in enumerate(reversed(fs[-20:])):
        if son is not None and sira >= 5:
            break
        dosyanin = None  # dosyanın son kaydı (dosya içinde sonraki satır daha yenidir)
        try:
            satirlar = open(f, errors="ignore")
        except OSError:
            continue
        for line in satirlar:
            if '"rate_limits"' not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            rl = (e.get("payload") or {}).get("rate_limits") if isinstance(e, dict) else None
            if isinstance(rl, dict):
                dosyanin = (e.get("timestamp"), rl, olcum_zamani(e.get("timestamp")))
        # Dosyalar arasında: ilk bulunan (en yeni dosya) kalır; daha eski dosyanınki yalnız ölçüm zamanı
        # kesin olarak daha yeniyse geçer.
        if dosyanin and (son is None or (dosyanin[2] is not None and (son[2] is None or dosyanin[2] > son[2]))):
            son = dosyanin
    ETIKET = {"5 saat": "5 hours", "hafta": "week"}
    # Kayıt kendi penceresinden eskiyse (sıfırlanma geçti, ya da yaşı 5 saati / haftalıkta bir günü aştı) "stale" yazılır.
    # Codex'i yenilemek için model koşusu başlatılmaz: kayıt ancak codex kullanılınca tazelenir (0014).
    SINIR = {"5 saat": (5 * 3600, "5 hours"), "hafta": (24 * 3600, "a day")}
    def pencere_adi(b, varsayilan):
        # 0018: pencere sıradan değil süresinden (window_minutes); yoksa eski varsayım (primary 5 saat).
        dk = b.get("window_minutes")
        if isinstance(dk, (int, float)) and not isinstance(dk, bool):
            if 240 <= dk <= 360:
                return "5 saat"
            if 9000 <= dk <= 11000:
                return "hafta"
            return f"{int(dk)} min"
        return varsayilan
    if son:
        ts, rl, olcum = son
        for k, varsayilan in (("primary", "5 saat"), ("secondary", "hafta")):
            b = rl.get(k)
            if not isinstance(b, dict):
                continue
            resets = b.get("resets_at")
            if not isinstance(resets, (int, float)) or isinstance(resets, bool) or resets <= 0:
                continue  # 0018: sıfırlanma zamanı olmayan kova yazılmaz (null'da çöküyordu)
            ad = pencere_adi(b, varsayilan)
            r = datetime.datetime.fromtimestamp(resets).strftime("%m-%d %H:%M")
            # Son kayıt eski bir pencereden kalmış olabilir: yenilenme saati geçtiyse yeni pencere 0'dan başlar (0010).
            gecti = resets <= time.time()
            eski = "reset passed" if gecti else (
                f"older than {SINIR[ad][1]}" if ad in SINIR and olcum is not None and time.time() - olcum > SINIR[ad][0] else None)
            yaz(f"codex   {ETIKET.get(ad, ad):7s} used {b.get('used_percent')}%  resets {r}  (measured {ts})"
                + (f"  stale ({eski})" if eski else ""))
            kovalar.append({"saglayici": "codex", "grup": "Codex", "pencere": ad,
                            "kullanilan": b.get("used_percent"), "hassas": 0.0 if gecti else b.get("used_percent"),
                            "yenilenir": r, "olcum": ts, "yenilenir_epoch": resets})
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
  j=$(cd /tmp && zaman_sinirli 60 agy -p "/quota" --output-format json < /dev/null 2>/dev/null)
  KOTA_DOSYA=$1 python3 - "$j" <<'PY'
import datetime, json, os, sys
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
GRUP = {"Gemini Models": "agy: Gemini", "Claude and GPT models": "agy: Claude/GPT", "Gemini 4 Argon": "agy: Argon"}
PENCERE = {"weekly": "hafta", "5h": "5 saat"}
# Tükenmiş kovada alanlar eksik gelebilir (0014: reset_time yoktu, betik çöktü): eksik alan "?" olur.
for g in gruplar if isinstance(gruplar, list) else []:
    if not isinstance(g, dict):
        continue
    grup = GRUP.get(g.get("name"), g.get("name") or "?")
    for b in g.get("buckets") or []:
        if not isinstance(b, dict):
            continue
        rf = b.get("remaining_fraction")
        rf = rf if isinstance(rf, (int, float)) else None
        pencere = PENCERE.get(b.get("window"), b.get("window") or "?")
        etiket = {"5 saat": "5 hours", "hafta": "week"}.get(pencere, pencere)
        # 0018: reset_time UTC'dir; metin yerel saatle yazılır (Codex ve Claude gibi), kesin an epoch'ta.
        try:
            an = datetime.datetime.fromisoformat(str(b["reset_time"]).replace("Z", "+00:00"))
            if an.tzinfo is None:
                an = an.replace(tzinfo=datetime.timezone.utc)
            epoch = an.timestamp()
            yenilenir = datetime.datetime.fromtimestamp(epoch).strftime("%m-%d %H:%M")
        except (KeyError, ValueError, TypeError, OverflowError, OSError):
            epoch, yenilenir = None, "?"
        kalan = None if rf is None else round(100 * rf)
        if not sessiz:
            print(f"agy     {grup[:22]:22s} {etiket:7s} left {'?' if kalan is None else kalan}%  resets {yenilenir}")
        kova = {"saglayici": "agy", "grup": grup, "pencere": pencere,
                "kullanilan": None if kalan is None else 100 - kalan,
                "hassas": None if rf is None else round(100 * (1 - rf), 1), "yenilenir": yenilenir}
        if epoch is not None:
            kova["yenilenir_epoch"] = epoch
        kovalar.append(kova)
json.dump(kovalar, open(os.environ["KOTA_DOSYA"], "w"))
PY
}

# kota_yuzde <araç> <model> [pencere]: bu koşunun harcadığı pencerenin kullanım yüzdesi, pencere, grup ve
# ölçüm zamanı (Codex kaydının; agy'de boş), sekmeyle ayrılmış; okunamazsa boş. Pencere verilirse o
# (koşu sonrası, öncekiyle aynı pencere). agy grubu hooks/quota.py'nin agy_grubu'yla aynı kuraldır:
# Argon'un kendi kovası varsa o, yoksa Gemini (0018).
# Codex: 5 saatlik pencere, yoksa haftalık. agy: modele göre grup, en dolu pencere (0014: Claude/GPT'nin
# 5 saati %0 iken haftası %68'di; koşu haftalık sınırda düştü).
kota_yuzde() {
  local f
  f=$(mktemp)
  KOTA_SESSIZ=1 "kota_$1" "$f" > /dev/null 2>&1
  python3 - "$f" "$1" "$2" "${3:-}" <<'PY'
import json, sys
try:
    kovalar = json.load(open(sys.argv[1]))
except (ValueError, OSError):
    kovalar = []
arac, model, istenen = sys.argv[2], sys.argv[3].lower(), sys.argv[4]
grup = "Codex"
if arac == "agy":
    gruplar = {k.get("grup") for k in kovalar}
    if "claude" in model or "gpt" in model:
        grup = "agy: Claude/GPT"
    elif "argon" in model and "agy: Argon" in gruplar:
        grup = "agy: Argon"
    else:
        grup = "agy: Gemini"
    kovalar = [k for k in kovalar if k.get("grup") == grup]
olcu = [k for k in kovalar if isinstance(k.get("hassas"), (int, float))]
if istenen:
    olcu = [k for k in olcu if k.get("pencere") == istenen]
elif arac == "agy":
    olcu.sort(key=lambda k: -k["hassas"])
else:
    olcu.sort(key=lambda k: {"5 saat": 0, "hafta": 1}.get(k.get("pencere"), 2))
if olcu:
    print(f"{olcu[0]['hassas']}\t{olcu[0].get('pencere')}\t{grup}\t{olcu[0].get('olcum') or ''}")
PY
  rm -f "$f"
}

if [ "${1:-}" = quota ]; then
  f1=$(mktemp); f2=$(mktemp)
  kota_codex "$f1"
  kota_agy "$f2"
  # 0018: içeriği değişmeyen okuma yeniden yazılmaz (hooks/quota.py); "hassas" artık atılmaz
  # (roster.py agy'de yuvarlanmamış değeri okur). Modül bulunamazsa eski yol: her okuma yazılır.
  kota_py="$(dirname "$OLAY")/quota.py"
  if [ -f "$kota_py" ]; then
    python3 "$kota_py" record "$f1" "$f2" 2>/dev/null || true
  else
    olay kota "kovalar=$(python3 -c 'import json,sys; print(json.dumps([b for f in sys.argv[1:] for b in json.load(open(f))]))' "$f1" "$f2")"
  fi
  rm -f "$f1" "$f2"
  exit 0
fi

if [ $# -lt 6 ]; then
  sed -n '2,9p' "$0" >&2
  exit 2
fi
arac=$1 model=$2 efor=$3 kip=$4
klasor=$(tam_yol "$5") gorev=$(tam_yol "$6")
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
baslangic=$(simdi)
baslik=$(grep -m1 -E '^#' "$gorev" | sed 's/^#* *//; s/^Görev: *//; s/^Task: *//')
olay isci_basladi "id=$(basename "$kayit")" "kaynak=$arac" "model=$model" "efor=$efor" "kip=$kip" \
  "klasor=$klasor" "aciklama=${baslik:-$(basename "$gorev")}" "kayit=$kayit" "oturum=${POLYCREW_SESSION:-${POLYCREW_OTURUM:-}}"
if [ "$arac" = codex ]; then
  sandbox=read-only
  [ "$kip" = yazar ] && sandbox=workspace-write
  komut=(codex exec -C "$klasor" -m "$model" -s "$sandbox" --json -o "$kayit/rapor.md")
  [ "$efor" != - ] && komut+=(-c "model_reasoning_effort=\"$efor\"")
  for r in ${resimler[@]+"${resimler[@]}"}; do komut+=(-i "$(tam_yol "$r")"); done
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
  { echo "$kural"; echo; cat "$gorev"; } | zaman_sinirli "$zaman_asimi" "${komut[@]}" - > "$kayit/ham.jsonl" 2> "$kayit/hata.txt"
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
  for r in ${resimler[@]+"${resimler[@]}"}; do on="$on Image to look at: $(tam_yol "$r")."; done
  istem="$on $kural"$'\n\n'"$(cat "$gorev")"
  komut=(agy -p "$istem" --model "$model" --mode "$mode" --output-format json --print-timeout "${zaman_asimi}s")
  [ "$efor" != - ] && komut+=(--effort "$efor")
  printf '%q ' agy -p "<gorev.md + folder line>" --model "$model" --mode "$mode" --output-format json > "$kayit/komut.txt"
  (cd "$klasor" && zaman_sinirli "$((zaman_asimi + 60))" "${komut[@]}" < /dev/null > "$kayit/ham.json" 2> "$kayit/hata.txt")
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
# 0014: kesilen ya da düşen koşunun raporu yarım kalabilir; sonuna neden düştüğü yazılır.
if [ "$kod" != 0 ]; then
  case $kod in
    124) anlam="stopped by the time limit, EXTERNAL_AGENT_TIMEOUT=${zaman_asimi}s" ;;
    *) anlam="the tool's own exit code" ;;
  esac
  { echo; echo "---"; echo "**Run failed:** exit code $kod ($anlam). Last lines of hata.txt:"
    tail -n 5 "$kayit/hata.txt" 2> /dev/null | sed 's/^/    /'; } >> "$kayit/rapor.md"
fi
bitis=$(simdi)
python3 -c "print(round($bitis - $baslangic, 1))" > "$kayit/sure_sn"
echo "$kod" > "$kayit/cikis_kodu"
kota_fark="" kota_ortak=""
if [ "${EXTERNAL_AGENT_NO_QUOTA:-}" != 1 ]; then
  kota_sonra=$(kota_yuzde "$arac" "$model" "$(printf '%s\n' "$kota_once" | cut -f2)")
  cakisma=0
  [ -f "$OLAY" ] && cakisma=$(python3 "$OLAY" overlap "$(basename "$kayit")" "$arac" "$baslangic" 2>/dev/null || echo 0)
  kota_sonuc=$(python3 - "$kayit/kota.json" "$kota_once" "$kota_sonra" "$cakisma" <<'KOTA'
import datetime, json, sys
dosya, once, sonra, cakisma = sys.argv[1:5]
def ayir(m):
    p = (m.split("\t") + ["", "", ""])[:4]
    try:
        return float(p[0]), p[1] or None, p[2] or None, p[3] or None
    except ValueError:
        return None, None, None, None
def ani(t):
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, AttributeError):
        return None
o, pencere, grup, olcum = ayir(once)
s, pencere2, grup2, olcum2 = ayir(sonra)
c = cakisma.split()
cakisanlar = c[1].split(",") if len(c) > 1 else []
fark = ortak = neden = None
if o is None or s is None:
    neden = "quota could not be read"
elif pencere != pencere2 or s < o:
    neden = "the quota window reset during the run"
elif ani(olcum) is not None and ani(olcum2) is not None and ani(olcum2) <= ani(olcum):
    # 0018: Codex kayıt yazmadan düştüyse sonraki okuma öncekinin aynısıdır; fark 0 değil, bilinmiyor.
    neden = "no new reading after the run"
elif c and c[0] == "1":
    # 0014: pay ayrılamaz ama pencerenin birlikte ne kadar dolduğu kalır (maliyete girmez).
    neden = "another run of the same tool overlapped; the share cannot be separated"
    ortak = round(s - o, 1)
else:
    fark = round(s - o, 1)
kayit = {"once": o, "sonra": s, "fark": fark, "pencere": pencere2 or pencere, "grup": grup2 or grup, "neden": neden}
if ortak is not None:
    kayit.update(ortak_fark=ortak, cakisanlar=cakisanlar)
json.dump(kayit, open(dosya, "w"))
print(("" if fark is None else str(fark)) + "\t" + ("" if ortak is None else str(ortak)))
KOTA
)
  kota_fark=$(printf '%s\n' "$kota_sonuc" | cut -f1)
  kota_ortak=$(printf '%s\n' "$kota_sonuc" | cut -f2)
fi
olay isci_bitti "id=$(basename "$kayit")" "kaynak=$arac" "cikis=$kod" "sure_sn=$(cat "$kayit/sure_sn")" \
  "kullanim=$(cat "$kayit/kullanim.json" 2>/dev/null || echo null)" "kayit=$kayit" ${kota_fark:+"kota=$kota_fark"} \
  ${kota_ortak:+"kota_ortak=$kota_ortak"}
echo "$kayit"
exit "$kod"
