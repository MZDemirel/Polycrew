# 0004: Dinamik kadro: her işten sonra puan, birikimli öneri

- **Tarih:** 2026-10-03
- **Durum:** Kabul edildi. Sürüm 0.4.0.

## Bağlam

- **Kullanıcının isteği** (Pixlender oturum 15): "kadroda dinamik bir yerleşim için her geliştirmede bir puanlama; hangi agent hangi yönde daha iyi, bir süre sonra daha iyi anlarız."
- **Durum:**
  - Kadro `skills/takim/kadro.md`'de iki deneyden (0002, koşu 2) elle yazılmış bir tabloydu.
  - PM'in `olay.py puan` notu işçiyi, rolü, alanı ve zorluğu taşımıyordu.
  - Olay günlüğü önbellekteydi, kalıcı değildi.
- **Kim yaptı:**
  - Kodu Gemini 3.8 Flash (agy, yazar, 6,5 dk) yazdı.
  - PM tohum veriye ilk deneyi ekledi (görevde kaynağı açık yazılmamıştı).
  - PM dış işçi kopyasının olay yazmama hatasını düzeltti.

## Kararlar

1. **Puan bayrakları:** `olay.py puan <id> <not> [gerekçe]` isteğe bağlı bayraklar alır:
   - `--isci` (`codex/gpt-6.1-sol/high`, `agy/gemini-3.8-flash-high`, `claude/<rol>/<model>`)
   - `--rol`
   - `--alan` (py, js, dart-gd, sanat, inceleme, tasarim, arastirma, belge, betik)
   - `--zorluk K|O|Z`
   - `--kota`, `--sure`, `--duzeltme`, `--proje`
   
   Bayraksız eski kullanım aynen çalışır.
2. **Kalıcı defter:** `--isci` verilen her puan `${XDG_DATA_HOME:-~/.local/share}/polycrew/puanlar.jsonl`'e de yazılır (`POLYCREW_PUANLAR`).
3. **Tohum:** `deney/puanlar-tohum.jsonl`, 38 satır.
   - Koşu 2'den 12 satır, PM'in 1–5 notlarıyla.
   - İlk deneyden (0002) 26 satır. Puan, işin en çok puanına bölünüp 5 ile çarpıldı. Başarısız iş 1 aldı.
4. **Öneri betiği:** `skills/takim/kadro.py oneri [--rol] [--alan] [--zorluk] [--tohumsuz]`.
   - Düzeltilmiş puan = (3,5·2 + toplam) / (2 + n): az veriyle tek bir 5 sıralamayı ele geçirmesin.
   - n < 3 "veri az" olarak işaretlenir.
   - Ortalama kota ve süre de gösterilir.
   - Filtresiz çalışınca rol × alan başına en iyi işçiyi verir.
5. **Kullanım:**
   - `/takim` kadroyu kurmadan önce `kadro.py oneri` çalıştırır.
   - `kadro.md` önsel olarak kalır; veri az ise o geçerli.
   - `/oturum-kapat` oturumun puan özetini SONRAKI_OTURUM'a bir satır yazar.
6. **Dış işçinin kopyası:** `dis-ajan.sh`'nin kopyası (paralel koşu için) olay günlüğünü bulamıyor ve sessizce atlıyordu. Pixlender oturum 15'te Codex ve Gemini canlı sayfada hiç görünmedi. Artık şu sırayla arıyor: `POLYCREW_OLAY`, `CLAUDE_PLUGIN_ROOT`, kurulu eklenti.

## Gözlem (Pixlender oturum 15)

- **Kancalar:** `agent_baslatildi`, `agent_basladi` ve `agent_bitti` olayları rol, kimlik ve transkriptle geliyor (0003'ün açık kalanı kapandı).
- **Claude Code'un worktree yalıtımı** agent'ı oturum başındaki `main`'den açıyor, güncel `main`'den değil. Bir agent'a mesajla `git merge --ff-only main` dedirtmek gerekti. `/takim`'e not: dalga arasında `main` ilerlediyse agent'ın görevine "önce main'i al" satırı yaz.
- **Bu oturumun ilk satırları:**
  - Codex sol: gözden geçirmede 5, 5; yazarda 5.
  - Claude geliştirici: 5; 3B'de inceleme sonrası 4.
  - Gemini Flash: yazarda 4.
