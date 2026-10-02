---
name: izle
description: Takımın agent'larını ve dış işçilerini (Codex, Gemini) canlı gösteren yerel sayfayı aç; oturum sonunda paylaşılabilir raporunu üret. Kullanıcı "agent'ları göster", "kim ne yapıyor", "takımı izle", "izleme sayfası", "oturum raporu" dediğinde ya da /takim ile iş dağıtılırken kullan.
---

# İzle

Olaylar tek bir günlükte toplanır (`hooks/olay.py`, karar `0003`): Claude alt agent'ları kancalardan (`PreToolUse` Agent, `SubagentStart`, `SubagentStop`), dış işçiler `dis-ajan.sh`'den (başladı, bitti, kota), puanlar PM'den.

## Canlı sayfa

1. Sunucu açık mı: `curl -s -o /dev/null -w '%{http_code}' http://localhost:8770/api/durum`. 200 değilse arka planda başlat (Bash `run_in_background`):
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/izle/izle.py" --port 8770`
2. Kullanıcıya adresi ver: VS Code'da `Ctrl+Shift+P → Simple Browser: Show → http://localhost:8770` (ya da tarayıcı).
3. Sayfa İngilizce ve Türkçedir (tarayıcı diline göre; EN/TR düğmesi ya da `?lang=tr`). 3 saniyede bir yenilenir: şimdi çalışanlar, zaman çizelgesi (Claude turuncu, Codex yeşil, Gemini mavi), kota çubukları (dakikada bir `dis-ajan.sh kota`), işler ve puanlar. Bir işe tıklayınca son raporu ve görevi yan panelde.

## Puan

Bir işçinin işi bitip PM ölçtüğünde (kadro deneyi, `kadro.md`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/olay.py" puan <iş id> <1-5> "<kısa gerekçe>"
```

İş id'si: dış işçide kayıt klasörünün adı (`dis-ajan.sh`'nin son satırı), Claude agent'ında sayfadaki satırın kimliği (Agent aracının `tool_use_id`'si ya da agent kimliği).

## Oturum raporu

`/oturum-kapat`'ta, oturumda takım ya da dış işçi kullanıldıysa:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/izle/izle.py" rapor --saat <oturumun saati> --dil <projenin dili: tr|en> --cikti <scratchpad>/takim-raporu.html
```

Sonra dosyayı Artifact olarak yayımla (başlık "Takım izleme" sayfada hazır, ikon `chart`) ve bağlantıyı `SONRAKI_OTURUM.md`'ye yaz. Rapor, raporları ve görevleri gömülü taşır; yayımlamadan önce içinde gizli bilgi (anahtar, parola) olmadığına bak.

## Notlar

- Günlük: `${XDG_CACHE_HOME:-~/.cache}/polycrew/olaylar.jsonl` (`POLYCREW_OLAYLAR` ile değişir). Silmek güvenli; sayfa boş başlar.
- Claude'un kotası CLI'dan okunmaz; sayfa `/usage`'a yönlendirir.
- Kancanın alan adları Claude Code sürümüyle değişebilir; olaylar kısaltılmış ham yükü de saklar (`ham`).
