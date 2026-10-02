# 0003: Ad `polycrew` ve takımın görünürlüğü

- **Tarih:** 2026-10-02
- **Durum:** Kabul edildi. Sürüm 0.3.0.

## Bağlam

- Kullanıcı eklentiyi GitHub'a koymak istedi; önce İngilizce bir ad. "Kadro"yu ve füzyon fikrini beğendi.
- Pixlender'ın on dördüncü oturumunda (6.6'nın beş akışı, ikinci dış işçi koşusu) kullanıcı öbür agent'ların ne yaptığını göremediğini söyledi: VS Code eklentisinde alt agent'lar katlanmış satırlar, dış işçiler (Codex, Gemini) arka planda bir kabuk komutu. PM her işçinin süresini, token'ını ve notunu elle `kayit.md`'ye yazdı.

## Kararlar

1. **Ad: `polycrew`** (poly: Claude, Codex, Gemini; crew: kadro). Marketplace de `polycrew`; kurulum `polycrew@polycrew`. Komutlar `polycrew:oturum-ac`, `polycrew:takim`, `polycrew:izle`; roller `polycrew:<rol>`. İçerik Türkçe kalır, README'nin başında bir İngilizce paragraf. Yerel klasör `claude-eklenti` değişmedi.
2. **Tek olay günlüğü:** `${XDG_CACHE_HOME:-~/.cache}/polycrew/olaylar.jsonl` (proje dışında; bu düzeni kullanmayan projeye bir şey yazılmaz). Yazanlar:
   - kancalar (`hooks/olay.py`): `PreToolUse` (Agent aracı: rol, model, açıklama, kısaltılmış istem), `SubagentStart`, `SubagentStop`. Alan adları Claude Code sürümüyle değişebildiği için kısaltılmış ham yük de saklanır. Kanca hiç hata vermez, çıktı yazmaz.
   - `dis-ajan.sh`: `isci_basladi`, `isci_bitti` (süre, çıkış kodu, token, kayıt klasörü), `kota` (yapılı kovalar).
   - PM: `olay.py puan <id> <not> <gerekçe>`.
3. **Canlı sayfa, yerel:** `skills/izle/izle.py` (standart kütüphane `http.server`, 8770), tek HTML (`sayfa.html`, dış kaynak yok). Şimdi çalışanlar, zaman çizelgesi (sağlayıcıya göre renk), kota çubukları, iş ve puan tablosu; bir işe tıklayınca son raporu ve görevi. 3 saniyede bir yenilenir; kota dakikada bir.
   - Neden yerel sayfa: kullanıcı VS Code eklentisinde çalışıyor; Claude Code'un terminal paneli orada görünmeyebilir. Pixlender'ın `serve`'ü gibi Simple Browser'da açılır.
   - Claude agent'ı ile başlatma kaydı, aynı roldeki son başlatmaya (180 sn içinde) bağlanır: `SubagentStart` yükünde Agent aracının kimliği yok.
   - 6 saattir bitmeyen iş "bilinmiyor" sayılır (kesilen oturum, limit).
4. **Oturum raporu:** `izle.py rapor` aynı sayfayı veriyi, raporları ve görevleri gömerek durağan üretir; `/oturum-kapat` bunu Artifact olarak yayımlar. Paylaşılabilir; yayımlamadan önce gizli bilgiye bakılır.
5. **Bağımlılık yok:** Python 3 standart kütüphanesi ve bash.

## Doğrulama

- `tests/test_izle.py` (8): kanca yükünden olay, ilgisiz araç ve bozuk girdi sessiz, komutla olay ve puan, başlatma-başlama-bitiş tek iş, çalışan/hatalı/eski işçi, başlangıcı olmayan bitiş, pencere ve son kota, durağan raporda gömülü veri (`</script>` kaçışı).
- Bugünkü gerçek dış işçi kayıtlarından kurulan günlükle sayfa geniş ve dar (420 px) ekranda çekildi (`docs/img/izle.png`).

## Açık kalan

- Kancaların gerçek yükü: yeniden kurulumdan sonra ilk takım işinde `olaylar.jsonl` gözle denetlenecek (özellikle `SubagentStart`/`SubagentStop` alanları, transkript yolu, son mesaj).
- Claude agent'larının token'ı ve kotası yok (CLI'dan okunmuyor).
- Dış işçilerin oturum kimliği yok (`POLYCREW_OTURUM` verilirse yazılır); sayfa zaman penceresiyle süzer.
