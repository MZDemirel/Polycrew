Bu bir kod gözden geçirme görevidir. Hiçbir dosyayı değiştirme, commit atma. Depo: Pixlender (kurallar AGENTS.md ya da CLAUDE.md'de). Bu klasör `deney-hata` dalında; `main`'e göre tek bir commit var.

`git diff main...HEAD` (ve gerekirse `git show HEAD`) ile değişikliği incele. İlgili bağlam: docs/decisions/0044-kosuda-tasima-pozu.md ve 0042-eldeki-esya-bedene-girmez.md, src/pixlender/core/held.py, src/pixlender/core/animate.py.

Commit mesajı bunun bir sadeleştirme olduğunu söylüyor. Davranışı değiştiren bir hata var mı? Her bulgu için: dosya:satır, ne yanlış, hangi durumda yanlış sonuç verir, önem (engel / düzelt / not). Davranışı değiştirmeyen değişiklikleri hata olarak raporlama. Emin olmadığın şeyi "belirsiz" diye işaretle.

Son mesajın yalnız bulgu listesi olsun (bulgu yoksa "bulgu yok").
