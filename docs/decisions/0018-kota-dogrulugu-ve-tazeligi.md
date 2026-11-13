# 0018: Kotanın doğruluğu ve tazeliği

- **Tarih:** 2026-11-13
- **Durum:** Kabul edildi; `0005`'in Claude kotasını, `0010`'un koşu başına ölçümünü ve `0017`'nin tazelik kuralını düzeltir.

## Bağlam

Kullanıcının sorusu: "Tüm ajanların kotaları doğru bir şekilde ve zamanında alınıyor mu?" Oturum açılışında kod dört gözle tarandı: PM, `codex/gpt-6.1-sol/high` (331 sn, 5 saatlik kotadan %5), `agy/gemini-4-argon-high` (480 sn), `claude/reviewer/sonnet-5-5` (205 sn). Her biri 5 puan aldı. Üçünün de bulduğu ya da ölçerek doğrulanan sorunlar şunlar:

| Sorun | Ölçüm |
|---|---|
| Claude ölçümü 4 gün eskiydi ama taze görünüyordu | Kayıt: haftalık %5 (2026-11-09). Masaüstü kullanım aracı: %32. Sayfa yalnız sıfırlanmanın geçip geçmediğine bakıyordu; `roster.py` yaşa bakıyor ama Claude için not yazmıyordu |
| Claude'un model başına haftalık sınırı yazılamıyordu | Plan üç pencere gösteriyor: 5 saat, "Weekly · all models", "Weekly · Fable" |
| Argon koşusu Gemini kovasından ölçülüyordu | Bu oturumdaki Argon koşusunun `kota.json`'ında grup `agy: Gemini`, fark 0. agy'nin kendi "Gemini 4 Argon" grubu var (%17 kaldı) |
| Sayfada agy'nin sıfırlanma saati UTC idi | `11-13T16:46`, yerel saatle 19:46 |
| `quota` olayından `hassas` atılıyordu | `roster.py`'nin yuvarlanmamış eşik okuması hiç çalışmıyordu |
| Okunamayan kova sayfada %0 görünüyordu | `Number(null) \|\| 0` |
| Codex penceresi sıradan okunuyordu, `resets_at: null` gelince betik çöküyordu | Kayıtta `window_minutes` (300, 10080) var |
| Olay günlüğünün çoğu yinelenen kota olayıydı | 3,6 MB'ın 2,7 MB'ı, 3399 olay; sayfa her dakika yazıyordu |
| Günlüğe ekleme ile kırpma kilitsizdi | Kırpma arada eklenen satırı silebilirdi |

## Kararlar

1. **Tek kaynak: `hooks/quota.py`.** Eski ad eşlemesi, işçi → kova eşlemesi, sıfırlanma anı ve tazelik kuralı orada. `watch.py`, `roster.py`, `doctor.py`, `claude-quota.py` ve `claude-statusline.py` onu kullanır. `external-agent.sh` agy grubunu satır içi aynı kuralla seçer; testler ikisini birlikte denetler.
2. **Tazelik.** Okuma iki durumda eski sayılır:
   - Sıfırlanma anı geçmiştir. Ölçüm sıfırlanmadan sonra yapılmış olsa da eskidir, çünkü Codex'in son kaydı eski pencereden kalabilir (`0017`).
   - Okumanın yaşı pencereyi aşmıştır: 5 saatlik pencerede 5 saat, haftalıkta 1 gün.

   Sayfa nedeni gösterir ("bir günden eski"). `/doctor` da aynı kuralı kova başına uygular; eski sabit 5 saat sınırı kalktı.
3. **Kullanım pencere içinde yalnız artar.** Eski bir okuma eşiğin altındaysa ve sıfırlanması henüz gelmediyse işçi yine `low quota` sayılır. Eşiğin üstündeki eski okuma sırayı değiştirmez (`0017`).
4. **Kova eşlemesi.**
   - Argon işçisi `agy: Argon` kovasına bakar. En yeni agy okumasında bu kova yoksa (ortak planlar) `agy: Gemini`'ye düşer. Eski bir okumada kalan Argon kovası bu düşmeyi engellemez.
   - Claude işçisi (`claude/<rol>/<model>`) genel `Claude` kovalarına ve adı modelinde geçen `Claude: <ad>` haftalık kovasına bakar. `Claude: Fable` yalnız Fable işçisini düşürür.
5. **Zaman.** Her sağlayıcı sıfırlanma anını `yenilenir_epoch` olarak yazar; metin yerel saattir. 0.12.0 öncesi agy metni (`MM-DDTHH:MM`) UTC olarak çözülür.
6. **Claude kotası zamanında.**
   - **Statusline (CLI, kendiliğinden):** Claude Code statusline girdisinde `rate_limits.five_hour` ve `seven_day` veriyor (Pro/Max/Ultra, ilk yanıttan sonra). `claude-statusline.py` değer değişince ya da 10 dakikada bir olay yazar. Yalnız düzeni kullanan projede yazar, hiçbir hatada satırı bozmaz, var olan statusline'ı `--then` ile zincirler. Ayarı kullanıcı yapar, eklenti dokunmaz.
   - **PM (masaüstü ya da statusline yok):** `/session-start` (7. adım) ve `/team` atamadan önce Claude okumasına bakar. Okuma yoksa ya da eskiyse kullanım aracından (yoksa `/usage`) okuyup `claude-quota.py` ile yazar; model başına sınır için `--model-week` vardır. `roster.py` eski ya da eksik Claude okumasını not eder.
   - `claude-quota.py` geçmişteki ya da pencereden uzak sıfırlanmayı reddeder.
7. **Yazım.** `quota.py record` içeriği değişmeyen okumayı yazmaz; değişmese de 30 dakikada bir yazar.
   - Sıfırlanma anı karşılaştırmaya girer: yeni pencere yeni okumadır. Tek istisna kullanılmayan agy penceresidir; onun sıfırlanma anı her okumada "şimdi + 5 saat" olarak kayar.
   - Codex'in ölçüm zamanı karşılaştırmaya girer.
   - Okuma, karşılaştırma ve yazım tek kilit altındadır (`olaylar-son-kota.json.lock`): statusline ile `quota` aynı anda yazabilir.
   - Sayfanın tazelemesi 60 saniyeden 300 saniyeye çıktı.
8. **Koşu başına fark.** Codex koşudan sonra yeni kayıt yazmadıysa fark boş kalır ("no new reading after the run"), 0 yazılmaz.
9. **Günlük.** `yaz` ve `kirp` aynı `flock`'u alır (`olaylar.jsonl.lock`). `fcntl` yoksa kilitsiz çalışır.
10. **Bir kerelik sıkıştırma (kullanıcı onayladı).** Önce `olaylar.jsonl.yedek-20261113` yedeği alındı. Ardışık, içeriği değişmeyen kota olayları atıldı: 4269 → 2048 satır, 3,63 → 1,89 MB, 2221 olay. Sayfanın gördüğü 183 iş ve en yeni 10 kova yedektekiyle aynı.
11. Küçük düzeltme: `session_start.sh`'te `| head` yerine sınır awk'ın içinde; `pipefail` altında SIGPIPE (141) kancayı düşürebiliyordu.

## Ölçümler

- **Testler:** 164 test, 21 sn (önce 137). `claude plugin validate .` ve `bash -n` temiz.
- **Gerçek okuma** (`external-agent.sh quota`, 15:11):
  - Argon kendi kovasında: hafta %17 kaldı, sıfırlanma 11-16 15:43 yerel.
  - agy saatleri yerel.
  - Aynı okuma ikinci kez yazılmadı (4269 → 4269 satır).
- **Claude:** kullanım aracından 5 saat %21, hafta %35, Fable %23 yazıldı.
  - `roster.py structure`: `claude: 5 hours 79% left, week 65% left`, `Claude: Fable: week 77% left`.
  - `/doctor`: üç sağlayıcı `ok`.
- **Sayfa** (8771, gerçek günlük, 560 px):
  - Yatay taşma yok, konsol hatası yok.
  - Altı kart: Claude, Claude: Fable, Codex, agy: Gemini, agy: Claude/GPT, agy: Argon. Sıfırlanma saatleri yerel.
  - Eklenen sahte kovalarda "stale reading (older than a day)" ve `?` göründü.
- **Statusline betiği:** örnek girdiyle satır `Opus · 5h 12.5% · week 33%`. İkinci çağrıda olay yazılmadı. Bozuk girdide ve düzensiz projede yazmadı.

## İnceleme

`codex/gpt-6.1-sol/high`, okuma kipinde, 188 sn, 5 saatlik kotadan %4 (bu düzeltmeyle ölçüldü). Beş bulgu verdi, beşi de geçerliydi ve düzeltildi; puan 5:
- sıfırlanma anı imzadan bütünüyle çıkınca yeni pencerenin aynı yüzdesi yazılmıyordu;
- durum dosyası kilitsizdi;
- eski bir Argon okuması Gemini'ye düşmeyi engelliyordu;
- `/doctor` haftalık kovaya da 5 saat sınırı uyguluyordu;
- `--model-week Fable x` iz basıyordu (artık çıkış 2).

## Açık kalan

- Statusline betiği gerçek bir CLI oturumunda denenmedi (bu oturum masaüstünde). `rate_limits` alanının en düşük Claude Code sürümü belgelenmemiş.
- Masaüstü uygulamasında Claude okuması hâlâ PM'e bağlı; skill adımı bunu hatırlatıyor ama kendiliğinden değil.
- Codex kaydı yalnız Codex kullanılınca tazelenir.
- İşçi adlarında efor bazen modelin içinde (`gemini-4-argon-high`), bazen ayrı (`gemini-4-argon` + `high`); çizelgede iki şerit oluyor.
- Taramanın kapsam dışı bulguları:
  - puan aralığı denetimi (999, `nan`);
  - agy'de `response: null`;
  - devam ettirilen agent'ın süresi;
  - `Try`'ın alan düzeyi;
  - dış işçiye giden tam metnin (`istem.md`) saklanması;
  - kota ya da izin yüzünden düşen koşu için ayrı çıkış kodu;
  - okuma kipinde `git status` denetimi.
