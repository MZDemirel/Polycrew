# polycrew: yol haritası

**Hedef:** Pixlender'daki çalışma düzeni (CLAUDE.md, PLAN.md, karar notları, SONRAKI_OTURUM.md, plan modu, bitti tanımı) ve ajan takımı her projede bir komutla kullanılabilsin.

### Aşama 1: İskelet ve takım denemesi
**Mod:** yapımcı
- [x] Takım denemesi: iç içe agent, mesajlaşma, worktree (`0001`)
- [x] Oturum skill'leri: `oturum-ac`, `oturum-kapat`, `karar`, `proje-kur`
- [x] SessionStart hook'u: "Nerede kaldık" özeti
- [x] Roller: lider, geliştirici, sanatçı, gözden geçirici, tasarımcı, araştırmacı
- [x] `/takim` skill'i
- [x] Yerel marketplace ile kişisel hesaba kurulum
- [x] İlk gerçek deneme: Pixlender Aşama 6.6 takımla; limitte kesildi, gözlemler SONRAKI_OTURUM'da

**Bitti sayılır:** Pixlender'da bir aşama takımla bitti ve takımın nasıl çalıştığı yazıldı.

### Aşama 1.5: Model, efor ve dış işçiler (0.2.0)
**Mod:** yapımcı
- [x] Rollere `model` ve `effort`
- [x] `dis-ajan` skill'i ve betiği (Codex, agy; okur/yazar, kayıt)
- [x] Deney: 6 aday × 5 iş, puan tablosu ve kadro (`0002`)
- [x] `/takim`: zorluğa göre kadro, küçük takım, ara commit, karar numarasını PM verir

### Aşama 2: Düzeni oturt
**Mod:** yapımcı
- [x] Gözlemlere göre roller ve `/takim` düzeltmeleri (`0002`)
- [x] Kadroyla gerçek bir aşama (Pixlender 6.6'nın kalanı); kadronun düzeltmesi (koşu 2, `960cace`)
- [x] Ad `polycrew`, takımın görünürlüğü: olay günlüğü, canlı sayfa, oturum raporu (`0003`)
- [ ] Başka bir projede `/proje-kur` (ör. Go_RestApi ya da RotaWeb)
- [ ] İlk gerçek takım işinde kancaların yükünü denetle (`0003`'ün açık kalanı)
