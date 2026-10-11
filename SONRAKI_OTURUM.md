# Sonraki oturum

Son güncelleme: **2026-10-11** (git kuralları `0006`; İngilizce yüzey `0007`; öğrenen kadro `0008`, 0.6.0).

## Nerede kaldık

- **0.6.0 (2026-10-11, `0008`): öğrenen kadro.** Puanlar 30 günlük yarı ömürle soluyor (`roster.py --half-life`, 0 kapatır); tabloda `Eff. n` sayılan veri miktarı, "little data" ona bakıyor. `events.py score` Claude işçisine model sürümünü transkriptten ekliyor (`claude/developer/sonnet-5-5`); kanca biten agent'ın gerçek modelini günlüğe yazıyor. 2026-10-12 öncesi sürümsüz Claude satırları 5-5 okunuyor. Özet tablosunda `Try` sütunu. 59 test, 3,4 sn. PLAN.md'de Aşama 3 açıldı (kalanlar: yeniden puanlama, kota ve süre, takım yapısı önerisi, dış işçisiz ilk deneyim, GitHub Actions, ofis görünümü).

- **0.5.0 (2026-10-11, `0007`): adlar İngilizce.** Komutlar `/session-start`, `/session-end`, `/decision`, `/project-setup`, `/team`, `/external-agent`, `/watch`; roller `lead`, `developer`, `reviewer`, `artist`, `designer`, `researcher`; betikler `external-agent.sh read|write|quota`, `roster.py suggest|summary`, `events.py score`, `watch.py report`; zorluk E/M/H. Skill, rol ve kural metinleri İngilizce (kurallar `rules/git.md`), çıktı proje dilinde. Yeni projede not dosyası `NEXT_SESSION.md`; bu depo `SONRAKI_OTURUM.md`'yi kullanmaya devam ediyor (kanca ikisini de tanır). Eski puan verisi okurken yeni ada çevrilir, dosyalar değişmedi. İç kod ve JSON şeması Türkçe kaldı. 53 test, 2,8 sn. Eşleme tablosu `0007`'de ve `README.tr.md`'de.
- Aşağıdaki eski maddeler o günkü adlarla yazılı (`dis-ajan`, `kadro.md`, `/oturum-ac`); tarihsel kayıt, düzeltilmedi.

- **0.4.1 (2026-10-11, `0006`):** sabit git kuralları `kurallar/git.md`'de (imza yok, PR'da araç satırı yok, birleşen dal silinmez, işçi push etmez). `proje-kur` bunları sormaz, her projenin `CLAUDE.md` `Git` bölümüne yazar; `takim` 4. adım dalı silmez; `oturum-kapat`, `gelistirici`, `dis-ajan` dosyaya atıf yapar; `dis-ajan.sh` dış işçiye imza yasağını iletir. 44 test, 2,9 sn. İş `claude/universal-git-rules-ff6998` dalında; push ve birleştirme kullanıcıda, dal silinmez.

- 0.2.0: rollerde `model` ve `effort`, `dis-ajan` skill'i (Codex, agy), `takim/kadro.md`, ilk denemenin gözlemleri (ara commit, karar numarasını PM verir, küçük takım, `/oturum-ac`'ta `git worktree list`).
- **Deney (`0002`)**, Pixlender'ın gerçek işleriyle, 6 aday × 5 iş:
  - Okuma işlerinde herkes yeterli. Sonnet en hızlı, Gemini Pro en tutumlu, Codex gözden geçirmede kanıtlı ama yavaş.
  - Kodlamada Sonnet, Codex (sol ve astra) ve Gemini Flash hedefi tuttu. Gemini Pro dar izinle, agy Opus kotayla bitiremedi.
  - Resim üretmede Codex önde.
- agy izinleri: `~/.gemini/antigravity-cli/settings.json` → `permissions.allow`. Pixlender'a dar kurallar eklendi (kullanıcının onayıyla); yedek `settings.json.yedek-2026-10-02`.

- **Koşu 2 (2026-10-02, Pixlender 6.6'nın beş akışı):** kayıt `deney/2026-10-02-kosu2/kayit.md`. Codex sol okur 5/5, yazar 4/5; astra okur 4/5 ama altı kat pahalı; Gemini Pro okur 4'te 1; Claude sanatçı 4,7. Kadro güncellendi (`960cace`): gözden geçirme Codex sol. Claude haftalık limiti PM'in uzun bağlamıyla doldu.
- Gözlemler (rollere işlenecek): dış işçi görevinde "dosya sınırı dışında gerekirse en küçük değişikliği yap ve yaz; durma" cümlesi şart; agy görevlerinde `git -C` gibi kurala uymayan komut yazma; sanatçıya "en çok N üretim komutu" sınırı kotayı korudu.

## Sıradaki

### 1. Kadroyla gerçek bir aşama
- Pixlender 6.6'nın kalanı: A1 (dalda) ve B1 (dalda, yarım), A3, B2. Kadro `kadro.md`'den, maddelere zorluk.
- Gözlem: kadro tuttu mu, Claude kotası ne kadar uzadı?
- Kullanıcının isteği (2026-10-02): bir sonraki koşuda **çıktı kalitesine göre** sistemi (kadro, roller, `dis-ajan`) revize et. Her işçinin çıktısını kaydet: kalite notu, süre, kota (`dis-ajan.sh kota` öncesi ve sonrası).

### 2. Açık kalanlar
- `0008`: gerçek bir takım koşusundan sonra `agent_bitti` olayında `model` var mı, `events.py score ... --worker claude/developer/sonnet` adı sürümlü yazdı mı bak. Bitti: gözlem `0008`'e yazıldı.
- `0007`: kurulu 0.5.0 ile gerçek oturum denemesi: `/session-start` eski bir projede (Pixlender: `SONRAKI_OTURUM.md` tanınıyor mu, çıktı Türkçe mi), `/team` ile bir koşu (`polycrew:developer` yükleniyor mu), `external-agent.sh quota` ve bir `read` koşusu. Bitti: gözlem `0007`'ye yazıldı.
- `0006`: kurulu sürümle gerçek bir projede `/project-setup` (yeni proje, var olan `CLAUDE.md`, `~/.claude/CLAUDE.md` önerisi). Bitti: `Git` bölümünde sabit satırlar sorulmadan var.
- `0006`: bir takım koşusunda `developer`'ın `${CLAUDE_PLUGIN_ROOT}/rules/git.md`'yi okuyabildiğini doğrula.
- README ekran görüntülerinde eski rol adları varsa yenile.
- Pixlender ve Masalino `CLAUDE.md`'lerine sabit git bloğunu ekle (kullanıcının onayıyla).
- Gemini Pro ve agy Opus kodlamayı yeniden denemek (geniş izin kullanıcının kararı; Opus kotası).
- Tasarımcı ve lider rolleri ölçülmedi.
- Yeni model çıkınca `deney/` ile tekrar.
- Başka bir projede `/project-setup`.

## Senin yapman gerekenler

- `claude/universal-git-rules-ff6998` dalındaki üç commit'i (`0007`) gözden geçir, `main`'e al ve push et (dalı silme).
- Sonra kurulumu güncelle: `claude plugin marketplace update polycrew && claude plugin update polycrew@polycrew`.
- Pixlender ve Masalino'nun not dosyalarındaki başlangıç promptlarında `/oturum-ac` → `/session-start`.
- İzin listelerinde (`.claude/settings*.json`, agy `settings.json`) `dis-ajan.sh`, `kadro.py`, `olay.py`, `izle.py` geçen kuralları yeni adlara çevir.
- `~/.cache/polycrew/dis-ajan-kopya.sh` eski betiğin kopyası; yeni `events.py`'yi bulamaz, sil ya da yenisinden kopyala.
- `~/.claude/CLAUDE.md`'ye sabit kuralları yazmak isteyip istemediğine karar ver (blok `rules/git.md`'de).

## Başlangıç promptu

```text
Merhaba Claude, polycrew eklentisine devam ediyoruz. /session-start
```
