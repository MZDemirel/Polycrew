# 0007: İngilizce yüzey: adlar, metinler, komutlar

- **Tarih:** 2026-10-11
- **Durum:** Kabul edildi. `0006`'nın kural dosyasını `rules/` altına taşır.

## Bağlam

Kullanıcı eklentiyi başkalarının da kurmasını istiyor. README İngilizceydi ama komutlar (`/oturum-ac`), roller (`lider`), betik komutları (`dis-ajan.sh okur`) ve üretilen not dosyası (`SONRAKI_OTURUM.md`) Türkçeydi: İngilizce kullanıcı komutu yazamıyor, projesine Türkçe adlı dosya giriyordu.

## Kararlar

1. Tek takım, İngilizce adla. Skill: `session-start`, `session-end`, `decision`, `project-setup`, `team`, `external-agent`, `watch`. Rol: `lead`, `developer`, `reviewer`, `artist`, `designer`, `researcher`.
2. Skill, rol ve kural metinleri İngilizce. Çıktı dili projenin `CLAUDE.md`'sinden okunur; Türkçe projede Claude Türkçe konuşur ve yazar. Skill açıklamalarında Türkçe tetikleyiciler kalır ("oturumu aç", "takımla yap").
3. Betikler: `external-agent.sh <read|write>` ve `quota`; `roster.py suggest|summary` (`--role --field --difficulty --no-seed --days`); `events.py write|score` (`--worker --role --field --difficulty --quota --duration --fixes --project`); `watch.py report --hours --out --lang`; `claude-quota.py --five-hour[-resets] --week[-resets] --context[-tokens]`. Zorluk E/M/H. Çıktılar İngilizce, ondalık nokta ve `35%` biçimiyle. Komut ve bayraklarda eski ad tutulmaz: çağıranlar skill'lerdir, birlikte değişti.
4. İç kod ve veri şeması değişmez: Python tanımlayıcıları, olay günlüğünün alanları (`tur`, `rol`, `isci`, `kip`, `pencere` değerleri dahil), kayıt klasöründeki dosya adları (`rapor.md`, `sure_sn`), `~/.cache/polycrew` ve `puanlar.jsonl` yolları. Komut satırı ile şema arasındaki çeviri `hooks/events.py`'de (`BAYRAK`) ve `external-agent.sh`'de (`read`→`okur`).
5. Eski veri okurken çevrilir, dosya değişmez (`events.kayit_adlari`, `rol_adi`): rol (`polycrew:` öneki dahil), işçi adındaki rol parçası, alan (`sanat`, `arastirma`, `inceleme`, `tasarim`, `betik`), zorluk (K/O/Z ve `hafif`/`orta`/`agir`). Eski ve yeni satırlar aynı kovada toplanır. Eski ortam değişkenleri (`DIS_AJAN_*`, `POLYCREW_OLAYLAR/PUANLAR/OLAY/OTURUM`) yedek olarak okunur.
6. Not dosyası yeni projede hep `NEXT_SESSION.md`; başlıklar ve metin proje dilinde. Eski projelerde `SONRAKI_OTURUM.md` tanınır ve istenmeden yeniden adlandırılmaz. Kanca (`hooks/session_start.sh`) başlık metnine değil sıraya bakar: ilk `## ` bölümü, ikincinin `### ` satırları.
7. Bu deponun kendi notları (PLAN, SONRAKI_OTURUM, karar notları, CLAUDE.md) Türkçe kalır. `README.tr.md` yeni adlarla ve bir eşleme tablosuyla güncellendi. Sürüm 0.5.0.

### Denenip bırakılan

- Her skill için ikinci, ince bir İngilizce takma ad klasörü: skill listesi 14'e çıkardı.
- Her şeyi çevirip yalnız komut adlarını Türkçe bırakmak: İngilizce kullanıcının elle yazdığı tek şey komut adı; asıl engel yerinde kalırdı.
- Dile göre iki not dosyası adı: her skill ve kanca iki adı kalıcı taşırdı.

## Ad eşlemesi

| Eski | Yeni |
|---|---|
| `/oturum-ac`, `/oturum-kapat`, `/karar`, `/proje-kur` | `/session-start`, `/session-end`, `/decision`, `/project-setup` |
| `/takim`, `/dis-ajan`, `/izle` | `/team`, `/external-agent`, `/watch` |
| `lider`, `gelistirici`, `gozden-gecirici`, `sanatci`, `tasarimci`, `arastirmaci` | `lead`, `developer`, `reviewer`, `artist`, `designer`, `researcher` |
| `dis-ajan.sh`, `kadro.py`, `kadro.md`, `izle.py`, `claude-kota.py`, `sayfa.html` | `external-agent.sh`, `roster.py`, `roster.md`, `watch.py`, `claude-quota.py`, `page.html` |
| `hooks/olay.py`, `hooks/nerede_kaldik.sh`, `kurallar/git.md` | `hooks/events.py`, `hooks/session_start.sh`, `rules/git.md` |

## Testler ve denemeler

- 53 birim testi yeşil (44 + 9): eski ve yeni adların aynı kovaya düşmesi ve defterin değişmemesi, eski ortam değişkeni, skill ve rol adları, metinlerde eski ad kalmaması, dış işçi betiğinin argüman denetimi, kancanın iki dosya adı ve iki dille çalışması.
- `roster.py suggest --role developer --field py --difficulty H` tohum verideki `gelistirici`/`Z` satırlarını `claude/developer/sonnet` altında getirdi; `summary` kullanıcının gerçek defterini (salt okunur) yeni adlarla gösterdi.
- Geçici günlükle `watch.py report`: eski `polycrew:gelistirici` olayı raporda `polycrew:developer`.
- Kanca bu depoda (`SONRAKI_OTURUM.md`, Türkçe başlıklar) doğru bölümleri bastı.
- Bir hata yakalandı: `watch.py` içinde komut karşılaştırması eski adla kalınca rapor testi 8770'te sunucu başlattı; düzeltildi, başıboş süreç kapatıldı.

## Açık kalan

- Kurulu 0.5.0 ile gerçek oturum denenmedi: `/session-start`, `/project-setup`, bir takım koşusu, gerçek Codex/agy koşusu ve `external-agent.sh quota`.
- Kullanıcının yapacakları: Pixlender ve Masalino'nun başlangıç promptlarında `/oturum-ac` → `/session-start`; izin listelerinde `dis-ajan.sh` ya da `kadro.py` geçen kurallar; `~/.cache/polycrew/dis-ajan-kopya.sh` eski kopya (yeni `events.py`'yi bulamaz).
- `docs/img` ekran görüntülerinde eski rol adları görünüyor olabilir.
- İç kod ve şemanın çevirisi ayrı iş (göç betiği gerekir); `deney/` kayıtları eski adlarla tarihsel kayıt olarak kalır.
