# Kadro: zorluğa göre işçi (ölçümle kuruldu, eklentinin 0002 karar notu, 2026-10-02)

Zorluk **K** kolay, **O** orta, **Z** zor. Claude kotası PM'e, sanatçıya, tasarıma ve Z koduna saklanır.
Dış işçiler `dis-ajan` skill'i ile (Codex: `codex`, Gemini ve agy üzerinden Claude: `agy`).

| Rol | K | O | Z | Yedek |
|---|---|---|---|---|
| araştırmacı | Gemini 3.1 Pro (agy, okur) | Gemini 3.1 Pro | Codex sol + Gemini Pro (karşılaştır) | Claude `arastirmaci` (haiku) |
| gözden geçirici | Codex sol (okur) | Codex sol (okur; kanıtlı, yanlış alarm yok) | Codex sol; Codex'in yazdığı işte ek olarak Claude `gozden-gecirici` (sonnet); astra xhigh yalnız en kritikte (bir inceleme 5 sa penceresinin ~%20'si) | Gemini 3.1 Pro (dar izinle güvenilmez, 2026-10-02 koşusunda 4'te 1) |
| geliştirici | Gemini 3.8 Flash (yazar; dar izinle de çalıştı) ya da Codex sol | Codex sol high (yazar; görevde dosya sınırı ve "sınır dışında gerekirse en küçük değişikliği yap, son mesajda yaz; durma" cümlesi; 5 saatte en çok 3–4 iş, iş başına ~%12) | Claude `gelistirici` (sonnet; gerekirse opus) ve isteğe bağlı Codex astra ayrı dalda, iyisi seçilir | Codex sol |
| görsel okuma ve ölçüm | Codex astra / sol (okur, `-i` resim) | Codex | Claude `sanatci` (opus): sanat yargısı | Gemini Pro |
| sanatçı (eleştiri) | Claude `sanatci` | Claude `sanatci` | Claude `sanatci` (opus) | — |
| resim üretme | Codex `image_gen` | Codex | Codex (+ Gemini konsept için ikinci görüş) | Gemini Pro |
| tasarımcı | PM | Claude `tasarimci` (opus) | Claude `tasarimci` (opus) + Gemini Pro ikinci görüş | — |
| lider | PM | PM | Claude `lider` (sonnet), yalnız gerçekten paralel büyük akışta | — |

- **Eşzamanlılık:** test koşan geliştirici en çok 2–3 (makine), Claude agent en çok 2. Dış işçilerin kotaları ayrı ama makine ortak.
- **Rollerin model ve eforu** (frontmatter):
  - lider: sonnet, medium;
  - gelistirici: sonnet, high;
  - sanatci: opus, medium;
  - gozden-gecirici: sonnet, high;
  - tasarimci: opus, high;
  - arastirmaci: haiku.
  
  `-usta` varyantları şimdilik gerekmedi: Z işte PM `model: opus` ile başlatır.

**İkinci koşu (2026-10-02, Pixlender 6.6, kayıt `deney/2026-10-02-kosu2/kayit.md`):** Codex sol yazarda 4/5, okurda 5/5; Gemini Pro okurda 4 denemede 1 başarı; Claude sanatçı 4,7/5. Claude'un haftalık limitini en çok PM'in bağlamı yedi.

**Kota (ölçüldü):** iş dağıtmadan önce `dis-ajan.sh kota`. Codex'in 5 saatlik penceresi dar: bir kodlama koşusu yaklaşık %25–30. Gemini bol: deneyin tamamı haftalığın %4'ü. agy üzerinden Claude birkaç işte tükendi. Codex penceresi %60'ı geçtiyse orta işler Gemini'ye.

Bilinen tuzaklar: agy dar izinle geliştirici olamıyor (izinsiz ilk komutta iş düşer); agy üzerinden Claude Opus'un kotası küçük; Codex AGENTS.md'yi uygulayıp PLAN ve karar notu yazabiliyor (görevde dosya sınırı yaz); Gemini Flash hızlı ama token açısından ağır.
