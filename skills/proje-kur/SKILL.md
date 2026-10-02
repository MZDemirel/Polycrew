---
name: proje-kur
description: Bir projeye çalışma düzenini kur — CLAUDE.md, PLAN.md, SONRAKI_OTURUM.md ve docs/decisions/ iskeleti. Kullanıcı "bu projeye düzeni kur", "Pixlender'daki gibi çalışalım", "yeni proje başlatıyorum, plan çıkaralım" dediğinde kullan. Var olan dosyaların üstüne yazmaz.
---

# Proje kur

Önce projeyi tanı (dil, paket yöneticisi, test ve lint komutları, git durumu). Sonra kullanıcıya toplu sor (`AskUserQuestion`):

- Konuşma ve belge dili; kod dili.
- Varsayılan mod: **yapımcı** (Claude kodu yazar ve test ekler) ya da **öğretmen** (kullanıcı yazar, Claude yönlendirir). Aşama bazında değişebilir.
- Commit: kim atar, biçim (tek satır, önek yok, imza yok), hangi dalda, push'u kim yapar.
- Yeni bağımlılık için izin gerekir mi.

## Dosyalar (varsa dokunma, eksik bölümü öner)

**CLAUDE.md**: kısa; bir paragraf proje tanımı ve şu başlıklar:
`Dil`, `Çalışma modu` (öğretmen/yapımcı, "her aşamaya plan moduyla başla", "PLAN.md checkbox'larını işaretle", "önemli kararı docs/decisions/'a yaz"), `Git`, `Bağımlılıklar`, `Mimari kurallar` (projeden çıkanlar), `Ortam`, `Komutlar` (kurulum, test, lint, tip, çalıştırma), `Bitti tanımı` (testler yeşil, lint ve tip temiz, + projeye özel görsel/ölçü kontrolleri).

**PLAN.md**: hedef, ilkeler, sonra aşamalar:

```markdown
### Aşama N: Ad
**Hedef:** bir cümle.
**Mod:** yapımcı | öğretmen
- [ ] madde
**Bitti sayılır:** gözlenebilir ölçüt.
**Öğrenme notu:** (öğretmen modunda) öğrenilecek kavramlar.
```

**SONRAKI_OTURUM.md**: `# Sonraki oturum`, "Son güncelleme" satırı, `## Nerede kaldık`, `## Sıradaki` (`### 1. ...`), `## Kullanıcıya sorulacaklar`, `## Oturum açılınca ilk iş (Claude için)`, `## Senin yapman gerekenler`, `## Başlangıç promptu` (kod bloğunda), `## Oturum sonunda`.

**docs/decisions/0001-...md**: ilk karar genellikle "neden bu yapı ve bu araçlar" (`/karar` şablonu).

Kurduktan sonra listeyi göster, ilk commit'i projenin kuralıyla at (kullanıcı commit'i kendisi atmak istiyorsa atma).
