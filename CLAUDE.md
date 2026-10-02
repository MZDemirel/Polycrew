# polycrew: Claude Code kuralları

Kişisel Claude Code eklentisi (skill'ler, roller, hook). Yol haritası: `PLAN.md`. Kararlar: `docs/decisions/`. Nerede kalındığı: `SONRAKI_OTURUM.md`.

## Dil
- Kullanıcıyla Türkçe konuş. Skill, agent ve belge metinleri Türkçe; dosya ve alan adları İngilizce ya da ASCII Türkçe (`oturum-ac`).

## Çalışma modu
- Varsayılan yapımcı. Her değişikliğe plan moduyla başla. Önemli kararı `docs/decisions/` altına yaz.
- Eklentinin kendisi de bu düzeni kullanır: değişiklikleri önce gerçek bir projede (ilk olarak Pixlender) dene, gözlemi karar notuna yaz.

## Git
- Commit mesajı Türkçe, tek satır, önek ve imza yok. Commit'i Claude atar; push'u kullanıcı yapar. `main` üzerinde çalış.

## Kurallar
- Skill'ler projeye özel olmaz: komutları, bitti tanımını ve dili projenin `CLAUDE.md`'sinden okur.
- Hook'lar sessiz başarısız olur ve bu düzeni kullanmayan projede hiçbir şey yazmaz (olay günlüğü proje dışında, `~/.cache/polycrew/`).
- Betikler yalnız standart kütüphane (Python 3) ve bash kullanır.
- Rollerin araç listesi işlerine göre dar: sanatçı ve gözden geçirici kod değiştirmez.

## Komutlar
- Denetim: `claude plugin validate .`, `bash -n hooks/*.sh skills/dis-ajan/dis-ajan.sh`, `python3 -m unittest discover tests`
- İzleme sayfası: `python3 skills/izle/izle.py --port 8770` (deneme için `POLYCREW_OLAYLAR=<dosya>` ve başka port)
- Kurulumu güncelle: `claude plugin marketplace update polycrew && claude plugin update polycrew@polycrew`

## Bitti tanımı
- `claude plugin validate .` temiz, hook betikleri `bash -n` geçiyor, birim testleri yeşil.
- Değişen skill ya da rol gerçek bir oturumda denendi ve gözlem yazıldı.
