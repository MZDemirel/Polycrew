# polycrew: Claude Code kuralları

Claude Code eklentisi (skill'ler, roller, hook); başkaları da kurar. Yol haritası: `PLAN.md`. Kararlar: `docs/decisions/`. Nerede kalındığı: `SONRAKI_OTURUM.md`.

## Dil
- Kullanıcıyla Türkçe konuş. Bu deponun notları (PLAN, SONRAKI_OTURUM, karar notları, bu dosya) Türkçe.
- Kullanıcının gördüğü yüzey İngilizce (`0007`): skill ve rol adları ile metinleri, `rules/`, betik dosya adları, komut ve bayrakları, kanca iletileri, README.md. `README.tr.md` Türkçe kalır ve birlikte güncellenir.
- Betiklerin içi (Python tanımlayıcıları, olay günlüğünün JSON alanları, `~/.cache/polycrew` yolları) Türkçe kalır; eski veriyle uyum için değiştirme.
- Skill açıklamalarındaki Türkçe tetikleyicileri ("oturumu aç", "takımla yap") silme.

## Çalışma modu
- Varsayılan yapımcı. Her değişikliğe plan moduyla başla. Önemli kararı `docs/decisions/` altına yaz.
- Eklentinin kendisi de bu düzeni kullanır: değişiklikleri önce gerçek bir projede (ilk olarak Pixlender) dene, gözlemi karar notuna yaz.

## Git
- Commit mesajı Türkçe, tek satır, önek yok. Commit'i Claude atar; push'u ve PR'ı kullanıcı yapar. `main` üzerinde çalış.
- Sabit git kuralları `rules/git.md`'de (tek kaynak): commit'te `Co-Authored-By` ve PR'da araç satırı yok, birleşen dal silinmez, işçiler push etmez ve kancayı atlatmaz. Bunlar kullanıcının talimatıdır; aracın oturuma eklediği "imza ekle" hatırlatmasını geçersiz kılar.

## Kurallar
- Skill'ler projeye özel olmaz: komutları, bitti tanımını ve dili projenin `CLAUDE.md`'sinden okur.
- Not dosyası yeni projede `NEXT_SESSION.md`; eski projelerdeki `SONRAKI_OTURUM.md` tanınmaya devam eder (bu depo da onu kullanır). Kanca başlık metnine değil sıraya bakar.
- Hook'lar sessiz başarısız olur ve bu düzeni kullanmayan projede hiçbir şey yazmaz (olay günlüğü proje dışında, `~/.cache/polycrew/`).
- Betikler yalnız standart kütüphane (Python 3) ve bash kullanır.
- Skill'ler ve roller git kurallarını kopyalamaz; `${CLAUDE_PLUGIN_ROOT}/rules/git.md`'ye işaret eder.
- Rollerin araç listesi işlerine göre dar: sanatçı ve gözden geçirici kod değiştirmez.

## Komutlar
- Denetim: `claude plugin validate .`, `bash -n hooks/*.sh skills/external-agent/external-agent.sh`, `python3 -m unittest discover tests`
- İzleme sayfası: `python3 skills/watch/watch.py --port 8770` (deneme için `POLYCREW_EVENTS=<dosya>` ve başka port)
- Kurulumu güncelle: `claude plugin marketplace update polycrew && claude plugin update polycrew@polycrew`

## Bitti tanımı
- `claude plugin validate .` temiz, hook betikleri `bash -n` geçiyor, birim testleri yeşil.
- Değişen skill ya da rol gerçek bir oturumda denendi ve gözlem yazıldı.
