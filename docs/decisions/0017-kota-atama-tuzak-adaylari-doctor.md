# 0017: Kotaya bakan atama, tuzak adayları, `/doctor`; `0014`'ün C listesi

- **Tarih:** 2026-11-12
- **Durum:** Kabul edildi; `0009`'un sıralamasına ve `0010`'un kota ölçümüne ekler, `0014`'ün C listesini kapatır, `0016`'nın ilk kaynağını hazırlar.

## Bağlam

Kullanıcı önerilen ek geliştirmeleri onayladı: "Bu önerilerini de bir ajana yaptırabilir, ardından kontrol ve geliştirme yapabilirsin." İş iki akışa bölündü (dosyalar ayrık), PM o sırada izleme sayfasını yazdı (`0015`):

| Akış | İşçi | Süre | İnceleme |
|---|---|---|---|
| A: C listesi, kotaya bakan atama, tuzak adayları | `claude/developer/sonnet-5-5`, kendi worktree'si | 826 sn, 3 commit | `codex/gpt-6.1-sol/high`, 304 sn, 9 bulgu |
| B: `/doctor` | `codex/gpt-6.1-sol/high` yazar, kendi worktree'si | 479 sn, 5 saatlik kotadan %5 | `claude/reviewer/sonnet-5-5`, 135 sn, 10 bulgu |

Yazan model kendi işini incelemedi. İki incelemede de yanlış alarm çıkmadı.

## Kararlar

### `0014`'ün C listesi

1. `events.py score` başarıda tek satır yazar: `Scored <id>: <puan> (worker <işçi>)`.
2. `roster.py --help` ve `-h` çıkış 0 (argümansız ve bilinmeyen komut 2 kalır).
3. `roster.py structure` az verili tarafta "Claude: little data" ya da "external: little data" der ve sonunda sağlayıcı başına kalan kotayı listeler (`stale`, `low` işaretleriyle).
4. `external-agent.sh quota` Codex'in saklı ölçümünü, sıfırlanma anı geçmişse ya da yaşı pencereyi aşmışsa `stale (…)` diye işaretler. Tazelemek için model koşusu başlatmaz.
5. Çizelgenin penceresi ve ofis etiketleri `0015`'te.

### Kotaya bakan atama

6. `roster.py suggest` ve `summary` olay günlüğündeki en yeni kota okumasını (sağlayıcı, grup, pencere başına) okur. 5 saatlik pencerede **%20'nin**, haftada **%10'un** altında kotası kalan işçi satırının sonuna iner ve `low quota` yazılır (`--quota-low-5h`, `--quota-low-week`). `summary`'de kadro sütununa sıradaki işçi geçer, az kotalı yedeğe düşer. `--no-quota` hepsini kapatır.
7. Okuma yoksa ya da eskiyse **sıra değişmez**; tablonun altına tek satır not düşer. Eskilik: sıfırlanma anı geçmiş, ya da okumanın yaşı 5 saatlik pencerede 5 saati, haftalıkta 24 saati aşmış. Haftalık için 7 gün değil 24 saat: bir haftalık okumaya güvenip işçiyi düşürmek yanlış olur.
8. agy işçisi modelinin kota grubuna bakar (`external-agent.sh`'teki eşleme; `argon` kendi haftalık kovasına). Claude rollerinde günlükte Claude okuması varsa kullanılır, yoksa dokunulmaz; "bağlam" kovası kota sayılmaz.
9. Kota olaylarına `yenilenir_epoch` (kesin sıfırlanma anı, Unix saniyesi) eklendi. Eski olaylar kısaltılmış metinden okunmaya devam eder (Codex yerel saat, agy UTC). İzleme sayfası da artık bu alanı kullanır: agy'nin metnini yerel saat sanıp 3 saat kayıyordu.
10. Az kotalı işçi `Try` sütununda da önerilmez.

### Tuzak adayları

11. `events.py score` 3'ün altındaki puanı olay günlüğünün yanındaki `<günlük>-tuzak-adaylari.jsonl` dosyasına da yazar (zaman, proje, işçi, rol, alan, zorluk, puan, gerekçe, iş kimliği). Dosya `POLYCREW_EVENTS`'i izler. Aynı işin yeni puanı adayın yerine geçer; 3 ve üstü adayı siler.
12. `roster.py summary` tablodaki işçilerin son 30 gündeki en çok 5 adayını tablonun altında listeler. **Yalnız öneridir:** sıralamayı değiştirmez, hiçbir şey bunu kural diye okumaz; neyin kural olacağına kullanıcı karar verir. Ortak hafıza (`0016`) gelince PM adayları oradan ayıklar.
13. Yazma kilitlidir (`fcntl.flock`; yoksa son yazan kazanır) ve 90 günden eski aday yeniden yazımda düşer.

### `/doctor`

14. `skills/doctor/doctor.py` salt okunur kurulum denetimi: Python sürümü, PATH'te `codex`, `agy`, `node`; not dosyası, `CLAUDE.md`, `PLAN.md`; olay günlüğü (klasör, yazılabilirlik, kırpma sınırının %80'i); sağlayıcı başına son kota okumasının yaşı; agy izin dosyası; eklentinin kabuk betiklerinde tek tek `bash -n`. Satır başına `ok / warn / fail`, sonda sayım; `fail` varsa çıkış 1; `--json`.
15. Hiçbir şey yazmaz, düzeltmez, ağ çağrısı ya da model koşusu başlatmaz (`.pyc` bile yazmaz). Denetimdeki istisna o satırın uyarısına döner. Düzeltmeleri skill kullanıcıya tek tek önerir.
16. Eksik dış araç uyarıdır, hata değil (eklenti yalnız Claude rolleriyle çalışır); kurulu olmayan aracın kotası sorulmaz.

## İncelemelerden çıkanlar

**Kadro dalı (Codex, 9 bulgu, hepsi düzeltildi):** sıfırlanma anı ölçümden önceyse geçmiş sıfırlanma taze sayılıyordu; daha yeni ama okunamayan kova eski "az" okumasını yürürlükte bırakıyordu; tek bozuk olay (`kovalar` liste değil) bütün sağlayıcıların kotasını kapatıyordu; eski Codex metninde yıl UTC'den okunuyordu (yerel olmalı); agy'nin yuvarlanmış yüzdesi eşiği kaçırıyordu (%19,6 kalan "ok"); paralel iki puan birbirinin adayını eziyordu; bozuk aday satırı `summary`'yi düşürüyordu; `Try` kotaya bakmıyordu; aday dosyası sınırsız büyüyordu.

**`/doctor` (Claude reviewer, 10 bulgu, 9'u düzeltildi):** yeni kurulumda "günlük klasörü yok, oluştur" uyarısı (kanca onu ilk olayda kendisi açar); salt okunur günlük "ok" görünüyordu; gelecek tarihli kayıt eski ölçümü "0 saat" diye gizliyordu; tek bozuk kota satırı üç sağlayıcının satırını düşürüyordu; Codex ve agy satırında Claude ipucu; eksik betikte "sözdizimini düzelt"; olmayan `--project` yolu söylenmiyordu; günlük üç kez okunuyordu; README'lerde `/doctor` yoktu. Bırakılan: `TMPDIR` not dosyası olan bir klasörün altındaysa iki test düşer.

## Ölçümler

- 137 test yeşil (85'ten): izleme sayfası 6, doctor 24, kadro ve puan 18, inceleme düzeltmeleri 4.
- Gerçek kurulumda `doctor.py`: 14 ok, 1 uyarı (Claude kota ölçümü 70 saatlik). Boş `HOME` ile: klasör satırı ok ("ilk olayda açılır"), üç kota satırı uyarı.
- Gerçek günlükle `roster.py structure`: "codex: 5 hours 97% left, week 77% left", "claude: … (stale: reset passed)".
- Codex 5 saatlik kotası iki koşuda %0 → %9.

## Gözlemler (takım düzeni)

- **Codex'in commit'i:** git "`packed-refs.lock` salt okunur" hatası verdi ama commit atıldı. `external-agent.sh` sandbox'a `refs/heads` ve `logs` ekliyor, `packed-refs`'i değil.
- **Codex salt okunur kipte testleri koşamadı** (geçici dosya açamıyor); bulgularını bellek içi denemeyle kanıtladı. İnceleme görevine "testleri koş" yazmak boşuna.
- **`polycrew:developer` (sonnet)** sandbox'ında uzun bileşik komutlar reddedildi; yamaları betik dosyasına yazıp ayrı komutla koşarak ilerledi.
- **Kadro testleri gerçek günlüğü okuyordu** (`POLYCREW_EVENTS` verilmeyince); işçi yalıttı.
- **PM işçinin worktree'sini düzenlemedi:** iki dal da birleştirildikten sonra PM'in dalında düzeltildi. Dallar duruyor.
- `polycrew:developer` rolü ilk kez gerçek oturumda koştu (`0006`'nın açığı): commit'leri Türkçe, tek satır, imzasız; push yok.

## Açık kalan

- `external-agent.sh` argon koşularını hâlâ Gemini grubuna karşı ölçüyor; `roster.py` argon'u kendi kovasına bağlıyor. Biri öbürüne uydurulmalı.
- Kota eşikleri (%20, %10) tahmin; birkaç oturumluk veriyle yeniden bakılacak.
- `/doctor` izleme sunucusunun ayakta olup olmadığına bakmıyor.
- Python 3.9'da yerelde koşulmadı (kurulu değil); CI'ın 3.9 işi push'tan sonra gösterecek.
