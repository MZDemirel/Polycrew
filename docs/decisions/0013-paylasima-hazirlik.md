# 0013: Paylaşıma hazırlık: günlük kapısı, sayfanın açılışı, macOS

- **Tarih:** 2026-10-19
- **Durum:** Kabul edildi; `0003`'ün olay günlüğü kararına ve `0012`'nin sayfasına ekler.

## Bağlam

Kullanıcı eklentiyi başkalarıyla paylaşmak istiyor ve iki şey sordu: eksikler neler, `/session-start` izleme sayfasını neden açmıyor. Bakınca:

- Kanca (`hooks/events.py`) her projedeki her agent'ın görev metnini `~/.cache/polycrew/olaylar.jsonl`'a yazıyordu. Kullanıcının günlüğünde polycrew kullanmayan projeler vardı (`graphify-project-review`, `demo-cafe-system`); dosya 2269 satır, 2 MB idi ve hiç kırpılmıyordu. CLAUDE.md'nin "bu düzeni kullanmayan projede hiçbir şey yazmaz" kuralına ruhça aykırı, README'deki gizlilik bölümü de söylemiyordu.
- Sayfa yalnız `/watch` ya da `/team` ile açılıyordu: `session-start` skill'inde adımı yok, SessionStart kancası yalnız metin basıyor (kancadan başlatılan sunucu kancayla ölür; Pixlender'da `nohup &` ile iki kez kapandı), açıldığında da yalnız adres veriliyordu.
- `external-agent.sh` macOS'ta çalışmazdı: GNU `timeout` yok, BSD `date` `%N` bilmiyor, `/bin/bash` 3.2'de boş dizi `set -u` ile düşüyor. CI yalnız Ubuntu ve Python 3.11+.

## Kararlar

1. **Günlük kapısı:** kanca yolu yalnız proje dizinlerinden birinde (`CLAUDE_PROJECT_DIR` ya da yükteki `cwd`; agent başka bir polycrew projesine geçmiş olabilir, ikisine de bakılır) ya da üstünde `NEXT_SESSION.md` / `SONRAKI_OTURUM.md` varsa yazar; `session_start.sh` ile aynı ölçüt. Üst dizinlere bakılır, çünkü agent bir alt klasörde ya da `.claude/worktrees/` altında çalışabilir. Yolun hem yazıldığı hâline hem sembolik bağları çözülmüş hâline bakılır (proje içindeki bağ dışarıyı gösterebilir). `POLYCREW_WATCH_ALL=1` eski davranış. `write` ve `score` komutları kapılanmaz: onları skill'ler ve dış işçi betiği bilerek çağırır.
2. **Kırpma:** günlük 10 MB'ı aşınca en yeni satırlardan sınırın yarısı kalır (benzersiz geçici dosya ve `os.replace`). `POLYCREW_EVENTS_MAX_MB`, `0` kapatır. Kırpma ile eşzamanlı bir ekleme kaybolabilir; 5 MB'da bir olduğu için kabul. Kırpmanın hatası yutulur: puanın kalıcı deftere yazılmasını durduramaz.
3. **Kullanıcının mevcut günlüğüne dokunulmaz.** README'de 0.10.0 öncesi satırları istemeyen dosyayı silsin diye yazar.
4. **Sayfanın açılışı:** plan onaylanınca, planda takım ya da dış işçi işi varsa `/session-start` `watch`'un "Live page" adımlarını yapar; yoksa açmaz (kullanıcının seçimi: "takım işi varsa"). `watch` skill'i sayfayı Claude masaüstü uygulamasında yerleşik tarayıcı panesinde açar, VS Code'da Simple Browser'ı söyler, yoksa adres verir; sunucu yalnız Bash'in kendi arka plan koşusuyla.
5. **macOS:** `zaman_sinirli` önce `timeout`, sonra `gtimeout`, sonra Python (yeni süreç grubu; süre dolunca grup TERM, 5 sn sonra KILL, çıkış 124; SIGINT ve SIGTERM gruba iletilir). `date +%s.%N` yerine Python `time.time()`, `realpath`'e Python yedeği, boş dizi `${d[@]+"${d[@]}"}`. Alt sınır Python 3.9 (macOS'un Xcode araçlarındaki sürüm); testler uv ile 3.9'da yeşil. CI matrisi 3.9, 3.11, 3.14 ve `macos-latest` + 3.9; testler betiği `/usr/bin:/bin` PATH'iyle koştuğu için macOS'ta `/bin/bash` 3.2 ve `timeout`suz yol denenir.
6. **Sürüm:** 0.10.0, ilk `CHANGELOG.md` (İngilizce, kullanıcı yüzeyi; 0.3.0'dan bu yana kısa).

## Paylaşım için değerlendirme (2026-10-19)

Bu oturumda kapananlar yukarıda. Kalanlar, önem sırasıyla:

- **Gerçek oturum denemesi:** 0.5.0'dan beri hiçbir özellik gerçek oturumda denenmedi; Pixlender'da ayrı oturumda başladı (gözlem dosyası `~/.cache/polycrew/gozlem/2026-10-19-pixlender.md`).
- **Tohum veri tek kişiden:** kadronun başlangıç puanları yazarın Pixlender koşuları; işçi adları o günün modelleri. Yeni kullanıcının ilk önerileri buna dayanır ("stale" satırlar).
- **Katkı engeli:** karar notları, `deney/`, `PLAN.md` ve Python iç adları Türkçe (`0007` bilerek). Kullanana engel değil, katkı verecek olana engel.
- **Windows:** yalnız WSL. Kancalar bash, `python3` adı.
- **CLI'da Claude kotası:** yalnız masaüstü uygulamasının aracından okunuyor; CLI kullanıcısında kart boş.
- **Genel komut adları:** `/team`, `/watch`, `/decision` başka eklentiyle çakışabilir; `/polycrew:<ad>` her zaman çalışır.
- **Sürüm etiketleri ve GitHub açıklaması** yok (push ve depo ayarı kullanıcıda).

## Denemeler

- 80 test yeşil (76 + 4): notsuz projede yazmaz, alt dizinde ve `SONRAKI_OTURUM.md`'de yazar, `POLYCREW_WATCH_ALL` ile yazar, `write` kapılanmaz; kırpma yarıya iner ve yeni satır kalır, `0` kapatır; `timeout`suz (Python) yolda resimli codex ve agy koşusu; iki yolda süre aşımı 124 ile 15 saniyenin altında kesilir.
- Python 3.9 (uv) ile 80 test yeşil.
- Masaüstü uygulamasının tarayıcı panesinde örnek günlükle sayfa açıldı (ofis ve kartlar).

## İnceleme (Codex `gpt-6.1-sol` high, read, 225 sn)

Sekiz bulgu, hepsi düzeltildi:
- Python süre sınırlayıcı: lider TERM ile çıkınca torunlar SIGKILL'siz kalıyordu (artık grup her durumda KILL alır); süreç doğmadan gelen sinyal kayboluyordu (işleyiciler önce kurulur, bekleyen sinyal iletilir).
- Kırpma: iki süreç aynı `.kirp` adını kullanınca ikincisi hata verip puanı deftere yazdırmıyordu (benzersiz geçici dosya, hata yutulur).
- Kapı: sembolik bağlı alt klasör projeyi kaybettiriyordu; yazılan karar "`CLAUDE_PROJECT_DIR`, yoksa `cwd`" diyordu, kod ikisine bakıyordu (karar düzeltildi).
- `bash -n a b` yalnız ilk dosyayı denetler, ötekiler argüman olur: CI, CLAUDE.md ve README'lerdeki denetim komutu bu yüzden `external-agent.sh`'yi hiç denetlemiyordu (döngüye çevrildi).
- Testler: `0` sınırı varsayılanın üstündeki günlükle denenmiyordu; sahte codex görevin stdin'den geldiğini doğrulamıyordu.

Koşunun kendi gözlemi (`0010`): `kota.json` farkı yazmadı, çünkü Pixlender'daki iki Codex işçisi aynı anda koşuyordu ("overlapped"). Tasarlandığı gibi; paylaşılan araçta koşu başına fark ancak tek koşuda ölçülür.

## Açık kalan

- ~~CI'ın macOS ve 3.9 işleri~~ Bitti (2026-10-19, koşu 39260672957): beş iş de yeşil, `macos-latest` + 3.9 dahil; Mac'teki `/bin/bash` 3.2 ve `timeout`suz yol testlerden geçti.
- Sayfanın `/session-start`'ta kendiliğinden açılması gerçek oturumda denenmedi (kurulu 0.9.0'da yok).
