---
name: oturum-kapat
description: Bir çalışma oturumunu düzenli kapat. Kullanıcı "oturumu kapat", "bugünlük bu kadar", "notları güncelle", "SONRAKI_OTURUM'u yaz" dediğinde ya da oturumun hedefi bitince kullan. Checkbox'ları işaretler, karar notlarını tamamlar, SONRAKI_OTURUM.md'yi ve yeni başlangıç promptunu yazar, commit atar.
---

# Oturum kapat

## Adımlar

1. **Durum:** `git status` ve `git log` ile bu oturumun commit'lerini listele. Bitmemiş iş varsa kullanıcıya söyle; yarım kodu commit'leme.
2. **Bitti tanımı:** `CLAUDE.md`'deki bitti tanımını son kez denetle (testler, lint, tip denetimi; görsel çıktı varsa bakıldı mı).
3. **PLAN.md:** biten maddelerin checkbox'larını işaretle; maddeye karar numarasını ekle. Yeni çıkan işleri doğru aşamaya madde olarak yaz.
4. **Kararlar:** bu oturumda alınan ama yazılmamış kararlar için `/karar`.
5. **SONRAKI_OTURUM.md** (bölümleri koru):
   - Başlıktaki "Son güncelleme" tarihi ve oturumun bir satırlık özeti.
   - **Nerede kaldık:** bu oturumda ne yapıldı (sırayla, karar numaralarıyla, ölçülerle); test sayısı ve süresi; "Açık kalanlar" listesi güncel (kapananı sil, yeniyi ekle); yeni bağımlılık varsa yaz.
   - **Sıradaki:** öncelik sırasıyla, her biri "İş" ve "Bitti" ile.
   - **Kullanıcıya sorulacaklar** ve **Senin yapman gerekenler** (kullanıcının bakacağı resimler, yeniden başlatılacak sunucular).
   - **Başlangıç promptu:** bir sonraki oturumu açacak metin; `<geri bildirim>` yer tutucusuyla.
6. **Takım raporu:** oturumda alt agent ya da dış işçi çalıştıysa `izle` skill'indeki "Oturum raporu" adımı: `izle.py rapor` ile HTML üret, Artifact olarak yayımla, bağlantıyı `SONRAKI_OTURUM.md`'ye yaz.
7. **Hafıza:** proje dışı, kalıcı bir şey öğrenildiyse (kullanıcının tercihi, makine sınırı) hafızaya yaz; depoda zaten yazanı yazma.
8. **Commit:** projenin commit kuralıyla (CLAUDE.md). Push etme.

Son mesajda: commit'ler, kullanıcının yapması gerekenler ve başlangıç promptu.
