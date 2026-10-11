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
- [ ] Başka bir projede `/project-setup` (ör. Go_RestApi ya da RotaWeb)
- [x] İlk gerçek takım işinde kancaların yükünü denetle (`0003`'ün açık kalanı; Pixlender oturum 15: başlatma, başlama ve bitiş olayları rol ve kimlikle geliyor; dış işçinin kopyası olay yazmıyordu, düzeltildi, `0004`)
- [x] Dinamik kadro: puan defteri, `kadro.py oneri`, iki deneyden tohum veri (`0004`)
- [ ] `izle` raporu: Claude agent'ının raporu `SubagentHandback` iletisinden gelsin (bugün transkriptin son ara cümlesi: "Now the comparison script.")
- [ ] `/takim`: dalgalar arasında `main` ilerlediyse görevin ilk satırı "önce `git merge --ff-only main`" (Claude Code'un worktree yalıtımı oturum başındaki main'den açıyor, `0004`)
- [x] `izle`: agent haritası (PM → lider → işçi ağacı; kim kimi başlattı, hangi sağlayıcı, durum). Kullanıcının isteği, 2026-10-05; `0005`: canlı sayfa ve rapor, ilişki bulunamazsa PM
- [x] `izle` kota: ölçüm yenilenme saatinden eskiyse "eski ölçüm" diye göster; Claude ölçüm betiği ve sağlayıcı/grup/pencere başına son ölçüm (`0005`)
- [x] Evrensel git kuralları tek dosyada (`kurallar/git.md`): imza yok, PR'da araç satırı yok, birleşen dal silinmez, işçi push etmez; `proje-kur` sormadan yazar, `takim` dalı silmez (`0006`, 0.4.1)
- [x] İngilizce yüzey: 7 skill ve 6 rol İngilizce adla, betik komutları ve bayrakları, `rules/`, kanca; not dosyası yeni projede `NEXT_SESSION.md`; eski veri ve `SONRAKI_OTURUM.md` tanınır (`0007`, 0.5.0)
- [ ] `0006` ve `0007`'nin açık kalanı: kurulu 0.5.0 ile gerçek projede `/project-setup`, `/session-start` ve bir takım koşusu; rol gövdesinde `${CLAUDE_PLUGIN_ROOT}` çözülüyor mu
- [ ] İç kod ve veri şeması İngilizce (Python tanımlayıcıları, JSON alanları, önbellek yolları; göç betiğiyle); katkı gelmeye başlarsa
- [ ] README ekran görüntüleri: eski rol adları görünüyorsa yenile
- [ ] `/takim` ve `kadro.md`: dağıtım üç sağlayıcıya işin ağırlığına ve ölçülmüş beceriye göre; sabit "en çok N Claude agent" yerine planda iş, ağırlık, işçi, neden tablosu (kullanıcı, 2026-10-05)

### Aşama 3: Öğrenen kadro ve dışa açılma
**Hedef:** Kadro zamanla ve yeni modellerle kendini düzeltsin; eklentiyi ilk kez kuran biri Codex ve agy olmadan da işe yarar bir takım görsün.
**Mod:** yapımcı
- [ ] 0.5.0'ı gerçek oturumda dene (Pixlender): `/session-start` eski not dosyasıyla, `/team` ile bir koşu, `external-agent.sh quota` ve bir `read` koşusu; gözlem `0007`'ye (Aşama 2'deki açık kalanla aynı iş)
- [x] Puanlama, zaman ağırlığı: `roster.py suggest` ve `summary` puanları 30 günlük yarı ömürle soldurur (eski puan başlangıç değerine yaklaşır, silinmez); `--half-life` (`0008`)
- [x] Puanlama, sürümlü işçi adı: `events.py score` Claude işçisinin sürümünü transkriptten ekler (`claude/developer/sonnet-5-5`); 2026-10-12 öncesi sürümsüz satırlar 5-5 okunur (`0008`)
- [x] Puanlama, "dene" önerisi: özet tablosunda `Try` sütunu; az verili ve rolde önselin altına düşmemiş işçi kolay bir iş için önerilir (`0008`)
- [ ] `0008`'in açık kalanı: gerçek bir takım koşusunda kancanın modeli yazdığını ve `score`'un sürümü eklediğini doğrula; yarı ömrü birkaç haftalık veriyle yeniden değerlendir
- [x] Aynı işin (proje + id) sonraki puanı öncekinin yerine geçer; defter eklemeli kalır (`0009`)
- [x] Sıralamada maliyet eşitlik bozucu: puan farkı ≤ 0,10 ise %20 az kotalı, yoksa %20 hızlı işçi öne geçer (`0009`)
- [ ] Kotanın otomatik ölçülmesi: dış işçi koşusundan önce ve sonra kota okunup puana yazılsın (bugün 106 kayıttan 5'inde kota var; maliyet puana ancak o zaman katılabilir)
- [ ] Takım yapısı önerisi: puan ortalamalarından "bu rol için lider gereksiz", "bu alanda dış işçi yeter" gibi öneriler çıksın; yapıyı kullanıcı onaylar, kendiliğinden değişmez
- [x] Codex ve agy olmadan ilk deneyim: `roster.py` kurulu olmayan aracın işçilerini önermez, `external-agent.sh` çıkış 4 ve açık iletiyle durur, `quota` "not installed" der (`0009`)
- [x] Otomatik denetim: `.github/workflows/ci.yml` (birim testleri, `bash -n`, manifest JSON, `claude plugin validate`) (`0009`)
- [ ] `0009`'un açık kalanı: ilk push'ta CI sonucuna bak (Python 3.11 ve `plugin-validate` işi yerelde denenemedi)
- [ ] `watch`: ofis görünümü. Mevcut haritanın yanında üçüncü görünüm: masalar, çalışan ve boşta karakterler, son raporu gösteren konuşma balonu, dış işçiler için ayrı oda. Tek HTML içinde canvas, derleme adımı ve dış kütüphane yok; karakterler Pixlender'dan. README'nin üst görseli olur (kullanıcı, 2026-10-11)

**Bitti sayılır:** yeni bir model çıktığında kadro onu eski modelin puanıyla değil kendi koşularıyla sıralıyor; eski puanlar sıralamayı tek başına belirlemiyor; Codex ve agy kurulu olmayan bir makinede `/team` çalışıyor.
