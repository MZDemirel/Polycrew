# 0014: İlk gerçek takım koşusu ve düzeltmeleri

- **Tarih:** 2026-10-19
- **Durum:** Kabul edildi; `0010`'un paralel koşu kuralına, `0009`'un özet tablosuna ve `0012`'nin sayfasına ekler.

## Bağlam

0.5.0'dan beri hiçbir özellik gerçek oturumda denenmemişti. Pixlender'da ayrı bir oturum (PM Claude Opus 5.5) Aşama 7b'nin yedinci diliminden iki işi `/team` ile yaptı: 24 blokta yaka (Codex astra, yazar), kısa etekte delen ayakkabı (Codex sol, yazar, eşikte doğru durdu); inceleme agy'deki Claude opus'a, sonra Claude `reviewer` (sonnet); görsel karne Claude `artist` (opus). Gözlem dosyası: `~/.cache/polycrew/gozlem/2026-10-19-pixlender.md`.

**Önemli ayrıntı:** polycrew'ün marketplace'i yerel klasörden eklenmiş (`"source": "directory"`). Skill'ler ve betikler önbellekteki 0.9.0'dan değil yerel depodan koştu; kullanıcı oturum sürerken `main`'i 0.10.0'a ileri sardı, koşunun sonu 0.10.0 ile geçti. GitHub'dan kuran biri `${CLAUDE_PLUGIN_ROOT}` ile önbelleği görür; "skill yolu yerel depoya açılıyor" gözlemi bundan, eklentinin hatası değil.

## Tutanlar

- `/session-start` eski not dosyasını tanıdı, Türkçe konuştu; kadro tablosunun "Try" sütunu iki işçiyi gerçekten denetti (astra geliştirici 4, agy Claude gözden geçirici 2 kota yüzünden).
- `polycrew:artist` ve `polycrew:reviewer` doğrudan yüklendi. Sanatçı asıl kusuru buldu (pelerinsiz karakterde boş kalan renk yeri); gözden geçirici "engel yok" ve 6 kanıtlı bulgu verdi.
- Kanca `agent_bitti`'ye gerçek modeli yazdı; `score` sürümlü adı ve süreyi kendiliğinden ekledi (`0008`'in açık kalanı kapandı).
- `/watch` sunucuyu arka planda başlattı; ofis okunuyor.
- `roster.py structure`'ın "lider gerek yok" önerisi doğruydu.

## Kararlar (0.11.0)

1. **Proje süzgeci (gizlilik).** Pixlender'ın yayımladığı takım raporu, aynı saatlerde polycrew'de koşan Codex incelemesini ve raporunu da taşıyordu. İşin projesi: Claude olayında `cwd`, dış işçide `klasor`; `/.claude/worktrees/` öncesindeki son klasör adı (worktree'ler ana projeye sayılır). Sayfa `?project=<ad>` ve seçici; rapor varsayılan olarak çalıştırıldığı klasörün projesi (`--project`, `--all-projects`), proje listesi rapora girmez. Projesi bilinmeyen eski işler süzgeçte düşer. Kota süzülmez: hesap genelidir. Rapor başlığı "Polycrew · <proje> · <tarih>", `lang` raporun dili.
2. **agy kotası.** Tükenmiş kovada `reset_time` yoktu, `quota` çöktü (ardından boş dosyadan `JSONDecodeError`). Alanlar artık isteğe bağlı, eksik "?" olur, JSON her durumda yazılır. Ölçüm 5 saatlik pencereyi seçiyordu (%0) ama koşu haftalık sınırda (%68 → 100) düştü: agy'de grubun **en dolu** penceresi seçilir, koşu sonrası aynı pencere okunur, `kota.json`'da `grup`. Codex'te 5 saat önceliği kalır (testli eski davranış).
3. **Düşen koşunun raporu.** agy 429 ile düştüğünde `rapor.md` yarım bir düşünceyle bitiyordu. Çıkış kodu 0 değilse raporun sonuna kod, anlamı (124 süre sınırı) ve `hata.txt`'nin son 5 satırı eklenir.
4. **Ortak kota farkı.** Üç paralel Codex koşusu pencereyi 14 dakikada %2 → %82 yaptı; hiçbirine fark yazılmadı ve kullanıcıya hiçbir şey kalmadı. `events.py overlap` çakışanların kimliklerini de verir (`1 a,b`; eski okuyucu ilk sütuna bakar). Çakışmada `kota.json`'a `ortak_fark` ve `cakisanlar`, `isci_bitti`'ye ve puana `kota_ortak`. `kota` değil: maliyet eşitlik bozucusu (`0009`) yalnız ayrılabilen payı kullanır.
5. **Kadro özeti.** `summary --days 7` yalnız penceredeki puanlarla sıralıyordu: bugün tek puan alan Codex astra (n 1) 11 puanlı Claude sonnet'i (4,32) `developer/py` satırından attı, bugün 5 alan sanatçı önsele çekilip 4,52'den 4,00'a düştü. Artık her satır bütün geçmişle (yarı ömürle sönümlü, gelecek tarihli kayıt hariç) sıralanır; pencere yalnız dayanağı belirler (kadro işçisinin pencerede puanı varsa `window`, yoksa `stale`). Eşitlikte son puanı yeni olan önde. `0009`'daki "pencere dışı kadro ya da yedek olmaz" testi bilinçli olarak değişti.
6. **Zaman ekseni.** Etiketlerin üçü de `03:00` idi: 12 saatlik pencereye bitişi gelmemiş günler önceki bir iş (bilinmiyor) giriyor, çizelge günlere yayılıyor, günlük adımda etiket UTC gece yarısına (yerelde 03:00) düşüyordu. Bilinmiyor iş pencereye başlangıcıyla girer; bir günden uzun aralıkta etiket gün ve saat.
7. **agy rengi.** agy'deki Claude modeli Claude Code agent'ı gibi turuncu görünüyordu; agy işleri hep dış işçi (mavi) renginde, model adı kartta.
8. **Skill metinleri.** `session-start`: worktree'nin tabanın kaç commit gerisinde olduğu (bu oturumda 20; notlar eskiydi), "Try" işçisine E iş yoksa en hafif M. `team`: PM işçinin worktree'sindeki dosyayı düzenleyemez (uygulama engelliyor; işçiye geri ver ya da birleştirip kendi dalında düzelt); gözden geçiricinin önerisini uygulamadan önce dokunduğu testleri koş (bir öneri 12 testi kırdı).

## Denemeler

- 85 test yeşil (80 + 5): proje adı ve süzgeç, rapor başlığı ve dili, başka projenin işinin rapora girmemesi; bilinmiyor işin pencere dışında kalması; agy'nin en dolu penceresi ve grup; tükenmiş kovada `quota` ve düşen koşunun raporu (sahte agy 429 ile); çakışmada `ortak_fark`, `cakisanlar` ve puandaki `kota_ortak`; özette tek yeni puanın kadroyu çevirmemesi.
- Gerçek günlükle tarayıcı panesinde: `?project=Pixlender` yalnız Pixlender'ın 5 işini gösterdi, seçici "Tüm projeler"e geçince adres güncellendi, eksen 16:30–17:45, agy'nin düşen işi mavi ve "!".
- Gerçek defterle `summary --days 7`: sanatçı 4,58 (n 9, window), `developer/py` yine Claude sonnet 4,32 (stale).

## İnceleme (agy `gemini-3.8-flash-high`, read, 1136 sn; Codex %97, Claude %72 olduğu için kadronun "Try" işçisi)

Dokuz bulgu; yedisi düzeltildi: `score` projeyi `Path.cwd().name` ile yazıyordu, worktree'de dalın adı çıkıyordu (artık `events.proje_adi`, tek kaynak; `--worker`'sız puan da proje taşır, yoksa sayfanın süzgeci onu düşürüyordu); gelecek tarihli kayıt "Try" sütununa sızıyordu (en başta süzülür, test bütün sütunlara bakar); rapor başlığını sayfanın JavaScript'i eziyordu; `printf '%s' | cut` sonunda satır sonu yok (BSD için `\n`); grubun tek kovası tükenmişse durum testsizdi. Biri yanlış alarm (`roster.py`'de `from __future__` var), biri değiştirilmedi (eksik `remaining_fraction`'ı tükenmiş saymak tahmin olurdu). Puan 4.

Bu koşu ilk gerçek agy ölçümü oldu: `kota.json` → Gemini haftalık %0,3 → %1,3, fark 1,0 (`0010`'un açık kalanı: agy'de grup doğru).

## Açık kalan (C listesi, sonraki oturum)

- `events.py score` başarıda sessiz; bir satır onay.
- `roster.py --help` çıkış kodu 1.
- `structure`: az verili Claude satırında "only external measured" diyor; kalan kotayı hesaba katmıyor.
- Codex ölçümü iki günlükken "eski" uyarısı yok.
- Ofis: aynı modeldeki işçiler ayırt edilmiyor (masada etiket yok), okur ve yazar aynı görünüyor.
- Zaman çizelgesi varsayılan 12 saatte; bir saatlik oturumun çubukları sağ kenarda çizgi. Varsayılan pencere işlerin aralığına otursun ya da "oturum" düğmesi.
- Kota verisi: bu oturumda Claude 5 saat %29 → %56 (PM ≈ 290 bin bağlam, sanatçı opus 29 bin, gözden geçirici sonnet 76 bin token); Codex %2 → %97 (bir astra xhigh ve bir sol high yazar, artı bir sol okur); agy Claude/GPT haftalık %32 → %0 tek bir yarım incelemeyle. `roster.md`'deki "Codex ağır yazar ≈ %20–25" tahmini tutmadı; tek tek ölçülemediği için güncellenmedi, ortak farkla veri birikince bakılacak.
- Pixlender'ın yayımladığı rapor (https://claude.ai/artifact/LjJu9LQQRwaG4NHLmrxBgb) 0.11.0 öncesinden: polycrew'deki Codex incelemesini de taşıyor. Özel, ama paylaşılmadan önce yeniden üretilmeli.
- `polycrew:developer`'ın `rules/git.md`'yi okuması ve `/project-setup` gerçek oturumda denenmedi.
- Marketplace'i GitHub kaynağıyla yeniden eklemek (paylaşılan kurulumu denemek için) kullanıcının kararı.
