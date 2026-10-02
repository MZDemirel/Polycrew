---
name: oturum-ac
description: Bir çalışma oturumunu düzenli başlat. Kullanıcı "devam ediyoruz", "oturumu aç", "nerede kalmıştık", "önce notları oku" dediğinde ya da projede SONRAKI_OTURUM.md varsa oturumun başında kullan. Notları okur, git ve testleri denetler, geri bildirimi sorar, plan moduna geçer.
---

# Oturum aç

Projenin düzeni: `CLAUDE.md` (kurallar, komutlar, bitti tanımı), `PLAN.md` (aşamalar, her birinde **Mod:** satırı ve checkbox'lar), `docs/decisions/NNNN-*.md` (numaralı kararlar), `SONRAKI_OTURUM.md` (nerede kaldık, sıradaki, ilk iş, başlangıç promptu).

## Adımlar

1. **Oku:** `SONRAKI_OTURUM.md`'nin tamamı, `CLAUDE.md`, `PLAN.md`'de açık aşama, kullanıcının adını verdiği ya da "Sıradaki"de geçen karar notları. Dosya yoksa `/proje-kur` öner ve dur.
2. **Git:** `git worktree list` ile yarım dalları göster (önceki oturumdan kalan iş). `git status` temiz mi, son commit bir önceki oturumun notları mı? Worktree'deysen git dışı varlıkları (SONRAKI_OTURUM'da yazıyorsa) kısayolla bağla.
3. **Testler:** `CLAUDE.md`'deki test komutunu **arka planda** başlat (uzun sürebilir). Sonucu beklerken sonraki adıma geç.
4. **"Oturum açılınca ilk iş"** bölümü varsa onu sırayla uygula; bu skill'in adımlarıyla çakışırsa o bölüm geçerli.
5. **Geri bildirim:** kullanıcı başlangıç promptunda geri bildirim verdiyse her birini ciddiye al. Ölçülebilir olanı (bir hata, bir görüntü) ölç, sebebini bul, kısa raporla. Vermediyse "Kullanıcıya sorulacaklar"ı sor.
6. **Plan modu:** kullanıcının hedefini plan moduna girerek planla. Önce soruları `AskUserQuestion` ile toplu sor (en çok 4, her birinde önerilen seçenek ilk ve "(Önerilen)"). Aşama büyükse böl. Mod satırına uy (öğretmen modunda kod verme).
7. **Ağır işler:** `SONRAKI_OTURUM.md` ya da hafıza bir makine sınırı söylüyorsa (ör. süreç sayısı) ona uy.

## Rapor biçimi

Kısa: git durumu, test sonucu (sayı ve süre), geri bildirimin ölçümü, sorular. Ardından plan.
