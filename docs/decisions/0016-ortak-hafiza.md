# 0016: Ortak hafıza (taslak)

- **Tarih:** 2026-11-12
- **Durum:** İncelemede. Yön kullanıcıyla kararlaştırıldı; kod yazılmadı, açık sorular aşağıda.

## Bağlam

Kullanıcı: "Bu eklentinin amacı tüm CLI araçlarını tek yerden kontrol edebilmek. Öbür ajanların hafızasını da burada birleştirerek ortak bir hafıza kurmak iyi olur; ama sadece proje bazlı değil, genel kurallar da olsun: bir genel hafıza, bir de proje özelinde hafıza."

Bu makinede araçların kendi hafızaları (2026-11-12):

| Araç | Yer | Biçim |
|---|---|---|
| Codex | `~/.codex/memories_1.sqlite` | iç boru hattı (`stage1_outputs`, `jobs`), belgelenmemiş; `AGENTS.md` yok |
| agy | `~/.gemini/antigravity-cli/brain/`, `knowledge/` | oturum başına klasörler, iç biçim; `GEMINI.md` yok |
| Claude | `~/.claude/projects/<proje>/memory/*.md` | düz markdown, madde başına dosya ve `MEMORY.md` dizini; genel `CLAUDE.md` yok |

Dış işçiler bugün Claude'un hafızasını da `rules/git.md`'yi de okumuyor; kurallar onlara yalnız `external-agent.sh`'in göreve eklediği satırla ulaşıyor (`0006`).

## Kararlar

1. **Hafızanın sahibi polycrew'dür.** Codex ve agy'nin depolarına yazılmaz, oradan okunmaz: biçimleri belgelenmemiş, sürümle değişir. Ortak hafıza düz markdown dosyalarıdır; araçlara polycrew'ün zaten elinde olan iki kapıdan verilir.
2. **İki katman.**
   - **Genel:** `~/.config/polycrew/memory/`. Kullanıcının her projede geçerli tercihleri ve işçi tuzakları ("Gemini Pro dar izinle bitiremiyor"). `~/.cache` değil: önbellek silinebilir, hafıza silinmemeli.
   - **Proje:** proje klasöründe, git'te. O projenin öğrenilmiş dersleri; projeyi kuran başkası da alır, worktree'lerde hazır gelir.
3. **Okuma.** Dış işçiye `external-agent.sh` görev metnine ekler; Claude oturumuna `SessionStart` kancası basar. Bütün hafıza değil: dizin ve işin rolüne, alanına uyan maddeler, karakter bütçesiyle. Düzeni kullanmayan projede hiçbir şey okunmaz ve yazılmaz (kancaların kuralı).
4. **Yazma PM'dedir.** İşçi hafızaya yazmaz; raporuna "Lessons" satırı koyar. PM `/session-end`'de adayları ayıklar ve yazar. Paralel yazma çakışması ve çöp birikmesi böyle önlenir.
5. **Sağlayıcı sınırı.** Genel hafıza Codex ve Gemini'ye, yani başka şirketin modeline gider. Madde "yalnız Claude" işareti taşıyabilir; işaretli madde dış işçinin görevine eklenmez.
6. **Hafıza kural değildir.** Projenin `CLAUDE.md`'si ve `rules/git.md` önce gelir; çelişen madde uygulanmaz, PM'e bildirilir.
7. **İçe aktarma.** Claude'un proje hafızaları düz markdown olduğu için tek seferlik, kullanıcının onayıyla madde madde. Codex ve agy için içe aktarma yok.
8. **Tuzak adayları** (`0017`): düşük puanın gerekçesi hafızanın ilk otomatik kaynağıdır; yine yalnız aday, PM ayıklar.

## Açık sorular

- Proje içindeki klasörün adı (`.polycrew/memory/`, `docs/memory/`?) ve `/project-setup`'ın onu kurup kurmayacağı.
- Madde biçimi: Claude'unki gibi ön bilgili dosya mı (ad, tür, rol, alan, sağlayıcı sınırı), tek dosyada liste mi.
- Bütçe: görev başına kaç karakter; aşılınca hangi madde düşer (yaş mı, eşleşme mi).
- Eskime: bir madde ne zaman silinir; yeni model çıkınca işçi tuzakları sıfırlanır mı.
- Claude oturumunun kendi otomatik hafızasıyla (aynı proje için ikinci bir hafıza) çakışma: hangisi kaynak, çift kayıt nasıl önlenir.
- Proje hafızası git'te olduğu için gizli bilgi sızması: yazmadan önce denetim.

## Sıradaki adım

Açık sorular kullanıcıyla kapatılır, sonra en küçük dilim: iki klasör, `memory.py` (listele, ekle, role göre seç), `external-agent.sh`'e ekleme, `/session-end`'e ayıklama adımı; ilk deneme Pixlender'da.
