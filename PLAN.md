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
- [x] İlk gerçek takım işinde kancaların yükünü denetle (`0003`'ün açık kalanı; Pixlender oturum 15: başlatma, başlama ve bitiş olayları rol ve kimlikle geliyor; dış işçinin kopyası olay yazmıyordu, düzeltildi, `0004`)
- [x] Dinamik kadro: puan defteri, `kadro.py oneri`, iki deneyden tohum veri (`0004`)
- [ ] Kadro önerisinde kota ve süreyi de tartan bir sıralama (veri biriktikçe)
- [ ] `kadro.py`: aynı iş kimliğinin sonraki puanı öncekinin yerine geçsin (inceleme sonrası güncelleme; bugün iki satır olur)
- [ ] `izle` raporu: Claude agent'ının raporu `SubagentHandback` iletisinden gelsin (bugün transkriptin son ara cümlesi: "Now the comparison script.")
- [ ] `/takim`: dalgalar arasında `main` ilerlediyse görevin ilk satırı "önce `git merge --ff-only main`" (Claude Code'un worktree yalıtımı oturum başındaki main'den açıyor, `0004`)
- [x] `izle`: agent haritası (PM → lider → işçi ağacı; kim kimi başlattı, hangi sağlayıcı, durum). Kullanıcının isteği, 2026-10-05; `0005`: canlı sayfa ve rapor, ilişki bulunamazsa PM
- [x] `izle` kota: ölçüm yenilenme saatinden eskiyse "eski ölçüm" diye göster; Claude ölçüm betiği ve sağlayıcı/grup/pencere başına son ölçüm (`0005`)
- [ ] `/takim` ve `kadro.md`: dağıtım üç sağlayıcıya işin ağırlığına ve ölçülmüş beceriye göre; sabit "en çok N Claude agent" yerine planda iş, ağırlık, işçi, neden tablosu (kullanıcı, 2026-10-05)
