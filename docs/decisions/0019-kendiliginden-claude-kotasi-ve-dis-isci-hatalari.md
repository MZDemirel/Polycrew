# 0019: Claude kotası kendiliğinden, dış işçinin düşme nedeni, `0018`'in açıkları

- **Tarih:** 2026-11-13
- **Durum:** Kabul edildi; `0018`'in açık kalanlarını kapatır.

## Bağlam

0.12.1 `main`'e alındıktan sonra kullanıcı: "Masaüstünde Claude okuması hâlâ PM'e bağlı … kendiliğinden olması çok daha iyi olur", "bu açık kalanlara da devam edebiliriz". Masaüstü uygulamasının kullanım aracı (`get_usage`) yalnız PM'in elinde. Diskte aranınca iki aday çıktı:

| Dosya | İçerik | Tazelik |
|---|---|---|
| `~/.claude.json` → `cachedUsageUtilization` | `five_hour`, `seven_day`, sıfırlanma | 2026-10-03; yalnız CLI `/usage` ile güncelleniyor |
| `~/.config/Claude/plan-usage-history.json` | `{"version": 2, "samples": [{"t", "org", "u": {"fh", "sd"}}]}` | 436 örnek, 15 dakikada bir, uygulama açıkken |

İkincisi belgelenmemiş bir iç dosya; sıfırlanma saati ve model başına sınır yok. Kullanıcı yedekli kullanımı onayladı.

## Kararlar

### Claude kotası

1. **Masaüstü okuması** `hooks/quota.py`'de (`masaustu_kovalari`, `masaustu_kaydet`, `quota.py desktop`).
   - **Seçim:** en yeni örnek alınır. `~/.claude.json`'daki kuruluş varsa yalnız onun örnekleri sayılır. `fh` → 5 saat, `sd` → hafta; `kaynak: desktop`.
   - **Yaş:** 3 saatten eski örnek (uygulama kapalı) yazılmaz.
   - **Sıfırlanma:** önceki okumanın sıfırlanma anı ilerideyse taşınır. Örnek bilinen bir sıfırlanmadan önceyse, yani eski pencereye aitse, o kova yazılmaz.
   - **Yazım:** karşılaştırma, taşıma ve yazım tek kilit altında yapılır. Kilit 2 saniyede alınamazsa iş atlanır. Daha yeni bir Claude ölçümü (statusline ya da PM) varsa masaüstü örneği onu ezmez.
   - **Bozuk ya da eksik dosya:** sessizce geçilir, hiçbir şey yazılmaz.
2. **Kim çağırır:**
   - `session_start.sh` (en çok 5 sn);
   - `events.py` kancası (Agent/Task olaylarında);
   - sayfanın tazelemesi;
   - `external-agent.sh quota`;
   - `claude-quota.py` (argümansız).
3. **Okuma sırası:** üç kaynak (masaüstü, statusline, PM) aynı kovaya yazar ve en yeni ölçüm kazanır. Sayfa artık günlükteki son olayı değil en yeni ölçümü alır. `claude-quota.py` de ortak yazıcıdan yazar; böylece verdiği sıfırlanma anı durum dosyasına girer.
4. **Skill metinleri:** PM kullanım aracını yalnız Claude okuması yoksa, eskiyse ya da model başına sınır (Fable) gerekiyorsa okur.
5. **`/doctor`:** Claude satırında kaynağı gösterir (`desktop`, `statusline`, `PM`). "Claude desktop usage" satırı var: dosya yoksa ya da uygulama kapalıysa bilgi verir, tazeyken okunamıyorsa uyarır.

### Dış işçi (`external-agent.sh`)

Yazan: `codex/gpt-6.1-sol/high`, kendi worktree'sinde (`ext-dis-ajan-hatalari`). 311 sn sürdü, 5 saatlik kotadan %5 harcadı, puan 4.

6. **Tam metin:** aracın aldığı metin `istem.md`'ye yazılır. Codex görevini artık bu dosyadan okur; bayt bayt aynı.
7. **Düşme nedeni** (araç sıfırdan farklı çıktıysa):
   - agy'nin reddettiği eylemler varsa çıkış 6, `neden=permission`;
   - aracın hata sinyalinde kota ya da hız sınırı izi varsa çıkış 5, `neden=quota`.
   - Aracın kendi kodu olayda `arac_cikis` olarak kalır. Süre dolması (124) yeniden sınıflanmaz.
   - Hata sinyali şunlardır: `hata.txt`, Codex'in `error` ve `turn.failed` olayları, agy'nin `status` ve `error` alanları. İşçinin kendi yanıtına ya da okuduğu dosyalara bakılmaz.
   - Bu düşmeler işçinin kalitesi olarak puanlanmaz.
8. **Reddedilen agy eylemleri** başarılı koşuda da rapora yazılır; çıkış kodu değişmez.
9. **Okuma kipinde değişiklik:** git klasöründe `git status --porcelain` koşudan önce ve sonra alınır. Fark varsa rapora uyarı düşer ve olaya `degisti=1` yazılır. Önceden kirli bir dosyanın yeniden değişmesini görmez (`SKILL.md`'de yazılı).
10. **agy okuma kipi:** göreve "Headless single-turn run: do not wait for approval…" satırı eklenir. `{"response": null}` ya da sözlük olmayan JSON artık çökertmez.

### `0018`'in öbür açıkları

11. **İşçi adı:** agy'de efor modelin adındadır. `agy/X/E` → `agy/X-E`, `agy/X/-` → `agy/X` (puan, kadro, sayfa şeridi). Argon tek şeritte görünür.
12. **Puan:** not 1–5 arası sonlu sayı olmalı. `--quota`, `--duration`, `--fixes` sonlu ve negatif olmayan sayı olmalı. Uymazsa çıkış 2.
13. **Devam ettirilen agent'ın süresi:** ilk başlangıçtan, ondan sonraki son bitişe.
14. **Try:** o rol ve alanda ortalaması 3'ün altında olan işçi önerilmez.

## İnceleme

| İş | İnceleyen | Bulgu | Puan |
|---|---|---|---|
| A (PM) | `codex/gpt-6.1-sol/high`, 139 sn, %3 | 4, hepsi geçerli | 5 |
| B (Codex) | `claude/reviewer/sonnet-5-5`, 91 sn | 3 düzeltme, 2 not | 5 |

- **A'nın bulguları:**
  - Sayfa, kota olayından sonra gelen iş olayında çöküyordu: kova değişkeni `yeni()` kurucusunu gölgeliyordu. PM tarayıcıda da yakaladı; `main`'e hiç girmedi, artık testli.
  - Bilinen sıfırlanmadan önceki örnek yeniden taze sayılıyordu.
  - Daha yeni ölçüm karşılaştırması kilidin dışındaydı.
  - Session-start kancası kilitte süresiz bekleyebiliyordu.
- **B'nin bulguları:**
  - Kota deseni işçinin kendi çıktısında da eşleşiyordu: "quota" kelimesi, kimlikteki "429".
  - 124 kotaya çevriliyordu.
  - macOS bash 3.2'de `$( )` içindeki heredoc'ta kesme işareti sorun çıkarıyordu; heredoc ikamenin dışına alındı.

Codex'in yazar raporu Türkçe geldi (görev İngilizceydi). "TMPDIR not dosyalı klasörün altında" tuzağına yine düştü: kendi koşusunda 5 test düştü, normal `TMPDIR` ile hepsi geçti.

## Ölçümler

- **Testler:** 188 test, 33 sn (önce 164). `claude plugin validate .` ve `bash -n` temiz.
- **Gerçek masaüstü okuması:** 5 saat %33, hafta %36. Sıfırlanma saatleri (19:40, 21:00) PM okumasından taşındı. Sayfada Claude kartı `desktop` kaynaklı, Argon tek şeritte (15 şerit, 187 iş).
- **Hız:** `session_start.sh` 0,05 sn sürdü.

## Açık kalan

- **Statusline gerçek CLI'da denenemedi.** Bu makinedeki `claude` CLI (2.1.273) ilk açılışın tema ekranında kaldı. Kullanıcının ayarı değiştirilmesin diye geçilmedi.
- Masaüstü dosyası belgelenmemiş; uygulama güncellemesinde biçim değişirse `/doctor` uyarır.
- Model başına haftalık sınır (Fable) hâlâ yalnız PM'den gelir.
- Codex kaydı yalnız Codex kullanılınca tazelenir.
