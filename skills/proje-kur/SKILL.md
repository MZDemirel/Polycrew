---
name: proje-kur
description: Bir projeye çalışma düzenini kur — CLAUDE.md, PLAN.md, SONRAKI_OTURUM.md ve docs/decisions/ iskeleti. Kullanıcı "bu projeye düzeni kur", "Pixlender'daki gibi çalışalım", "yeni proje başlatıyorum, plan çıkaralım" dediğinde kullan. Var olan dosyaların üstüne yazmaz.
---

# Proje kur

Önce projeyi tanı (dil, paket yöneticisi, test ve lint komutları, git durumu). Sonra kullanıcıya toplu sor (`AskUserQuestion`):

- Konuşma ve belge dili; kod dili.
- Varsayılan mod: **yapımcı** (Claude kodu yazar ve test ekler) ya da **öğretmen** (kullanıcı yazar, Claude yönlendirir). Aşama bazında değişebilir.
- Commit: kim atar, önek ve biçim (ör. öneksiz tek satır ya da `feat(...): ...`), hangi dalda; push'u ve PR'ı kim yapar.
- Yeni bağımlılık için izin gerekir mi.

**Sabit git kuralları sorulmaz** ve hiçbir sorunun seçeneğine konmaz (imza yok, PR'da araç satırı yok, birleşen dal silinmez, işçi push etmez): `${CLAUDE_PLUGIN_ROOT}/kurallar/git.md`. Kullanıcı hangi biçimi seçerse seçsin `Git` bölümüne yazılırlar.

## Dosyalar (varsa dokunma, eksik bölümü öner)

**CLAUDE.md**: kısa; bir paragraf proje tanımı ve şu başlıklar:
`Dil`, `Çalışma modu` (öğretmen/yapımcı, "her aşamaya plan moduyla başla", "PLAN.md checkbox'larını işaretle", "önemli kararı docs/decisions/'a yaz"), `Git` (kullanıcının cevapları, ardından kural dosyasındaki "Proje CLAUDE.md'sine yazılacak blok" aynen), `Bağımlılıklar`, `Mimari kurallar` (projeden çıkanlar), `Ortam`, `Komutlar` (kurulum, test, lint, tip, çalıştırma), `Bitti tanımı` (testler yeşil, lint ve tip temiz, + projeye özel görsel/ölçü kontrolleri).

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

`CLAUDE.md` zaten varsa ve `Git` bölümünde sabit kurallardan biri eksikse dosyaya dokunma; eksik satırları göster ve eklemeyi öner.

**Kullanıcı düzeyi (bir kez öner):** `~/.claude/CLAUDE.md` yoksa ya da sabit kuralları içermiyorsa, aynı bloğu oraya yazmayı metni göstererek öner (bütün projeleri etkiler). Onay olmadan o dosyayı oluşturma ve değiştirme; kullanıcı istemezse yeniden sorma.

Kurduktan sonra listeyi göster, ilk commit'i projenin biçimiyle ve sabit kurallarla at (kullanıcı commit'i kendisi atmak istiyorsa atma).
