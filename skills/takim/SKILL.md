---
name: takim
description: Bir aşamayı ajan takımıyla yap — ana oturum proje yöneticisi (PM) olur, aşamayı bağımsız akışlara böler, her akışa bir lider başlatır, liderler geliştirici, sanatçı ve gözden geçirici işçileri yönetir, PM birleştirir. Kullanıcı "takımla yap", "ajan takımı", "paralel çalışalım", "akışlara böl" dediğinde kullan.
---

# Takım

Sen **PM**'sin (ana oturum). Takım düzeni ve dayanağı: eklentinin `docs/decisions/0001-takim-denemesi.md`.

```
kullanıcı ── PM (ana oturum: böler, birleştirir, kullanıcıya sorar)
              ├── lider A ── geliştirici (worktree) · sanatçı · gözden geçirici
              └── lider B ── geliştirici (worktree) · sanatçı · gözden geçirici
```

## 0. Kadro (zorluğa göre)
- Her maddeye zorluk ver: **K** kolay, **O** orta, **Z** zor. Kadroyu bu skill'in klasöründeki `kadro.md`'den kur. Madde → zorluk → kadro, planda kullanıcıya gösterilir.
- **Claude kotası PM'e, sanatçıya, tasarıma ve Z koduna saklanır;** gerisi önce dış işçiye (`dis-ajan` skill'i: Codex, agy) gider.
- **Varsayılan küçük takım:** PM → bir geliştirici (+ bir yardımcı). Lider yalnız gerçekten paralel, büyük akışlarda. Claude agent en çok 2; test koşan geliştirici en çok 2–3 (makine).
- **Karar numaralarını PM dağıtır;** işçi değiştirmez.
- **Kota:** kadroyu kurmadan önce `dis-ajan.sh kota` (Codex ve agy'nin 5 saatlik ve haftalık kotası). Codex penceresi %60'ı geçtiyse orta işler Gemini'ye; Claude kotası için kullanıcı `/usage`'a bakar.

Görünürlük: işe başlarken `/izle` ile canlı sayfayı aç ve adresini kullanıcıya ver; her işçinin işi bitince PM notunu `olay.py puan` ile yazar (`izle` skill'i).

## 1. Böl (plan modunda)
- Aşamanın maddelerini **dosya kümesine göre** akışlara ayır: iki akış aynı dosyayı değiştirmesin. Ayıramıyorsan sıraya koy ya da tek akış yap.
- Her akış: maddeler (sırayla, her biri bir commit), "Bitti" ölçütleri, dokunacağı dosyalar, akışlar arası bağımlılık (ör. "B2, A3'ün ışık yönünü kullanır; önce varsayılanla yap").
- Planı kullanıcıya onaylat.

## 2. Başlat
- Dış işçi: `dis-ajan` skill'i (worktree'yi sen hazırla: git dışı varlıklar, bağımlılıklar). Görevde dosya sınırını yaz: "PLAN, SONRAKI_OTURUM ve karar notlarına dokunma; PM yazar."
- Her akış için bir **lider**: `Agent(subagent_type: "polycrew:lider", run_in_background: true)`. Rol yüklenmemişse `general-purpose` ve `agents/lider.md`'nin içeriğini prompta koy.
- Lider promptuna: akış ve maddeleri, karar notları, proje kökü, git dışı varlıkların kısayol komutu, makine sınırları, **öbür liderlerin agentId'si** (başlattıktan sonra `SendMessage` ile bildir) ve "PM'e `SendMessage(to: "main")`".
- Kısa, akışlardan bağımsız işler (ör. bir rapor) için doğrudan bir işçi başlatabilirsin.
- **Sınır:** aynı anda en çok 2–3 geliştirici (makineye göre; projenin notlarına bak). Tam test takımı yalnız PM'de, sırayla, arka planda.

## 3. Yürüt
- Liderlerden gelen mesajları oku. Soru varsa: kendin karar verebiliyorsan ver ve lidere yaz; kullanıcının kararıysa topla, `AskUserQuestion` ile toplu sor. Liderleri bekletme.
- Kullanıcıya her birleştirmede kısa bilgi ver: ne birleşti, ölçü, resim.

## 4. Birleştir (yalnız PM)
Bir madde hazır olduğunda (lider raporu, gözden geçirici "engel yok", sanatçı onayı):
1. Resme kendin de bak; ölçüyü doğrula.
2. `git -C <worktree> rebase main` (çakışma olursa lidere geri ver), sonra ana depoda `git merge --ff-only <dal>`.
3. Tam testi, lint'i ve tip denetimini arka planda koş. Kırmızıysa `main`'i geri alma; düzeltmeyi lidere ver.
4. Dal işi bittiyse `git worktree remove <yol>` ve `git branch -D <dal>`.

## 5. Kapat
- Açık worktree ve dalları (`git worktree list`) yarım işin yeriyle `SONRAKI_OTURUM.md`'ye yaz; limit ya da hata yarıda keserse önce bunu yap.
- Liderlerin son raporlarını özetle; karar notlarının yazıldığını denetle.
- Takımın nasıl çalıştığını (sorunlar, izin istemleri, süreler) eklentinin `SONRAKI_OTURUM.md`'sine ya da bir karar notuna yaz; düzen buradan gelişir.
- `/oturum-kapat`.
