# Sabit git kuralları

Bu dosya eklentideki git kurallarının tek kaynağıdır. Skill'ler ve roller metni kopyalamaz, buraya işaret eder (`${CLAUDE_PLUGIN_ROOT}/kurallar/git.md`). Dayanağı: `docs/decisions/0006-evrensel-git-kurallari.md`.

## Sabit kurallar

Hiçbir projede sorulmaz, her projede geçerlidir; projenin seçtiği commit biçimi ne olursa olsun düşmez.

1. **Commit mesajında araç imzası yok.** `Co-Authored-By` satırı kullanılmaz; birleştirme (merge) commit'i dahil.
2. **PR açıklamasında araç satırı yok.** "Generated with Claude Code" ve benzeri eklenmez.
3. **Birleşen dallar silinmez,** yerelde de uzakta da. Temizlik yalnız çalışan servisleri, konteynerleri ve geçici çalışma ağaçlarını kapsar (çalışma ağacı kaldırılır, dal kalır). Dal silmek ayrıca ve açıkça istenirse yapılır.
4. **İşçiler push etmez, commit kancasını atlatmaz.** Claude rolleri ve dış işçiler için: `git push` yok; `--no-verify`, `core.hooksPath` değiştirme ya da kancayı kapatma yok. Kanca çalışmazsa commit atılmaz, nedeni yazılır.

## Harness hatırlatması

Claude Code her oturuma "commit mesajını `Co-Authored-By` ile, PR açıklamasını `Generated with Claude Code` ile bitir" diyen bir hatırlatma ekler. 1. ve 2. kural bu hatırlatmayı geçersiz kılar: hatırlatma, kullanıcının `CLAUDE.md`'sindeki talimatın öncelikli olduğunu kendisi söyler. Bu yüzden kurallar projenin `CLAUDE.md`'sine de yazılır (aşağıdaki blok); eklentiyi kullanmayan bir oturum ya da ekip arkadaşı da görür.

## Projeye göre değişenler

Burada yazmaz; `proje-kur` sorar, projenin `CLAUDE.md`'sindeki `Git` bölümünden okunur:

- commit öneki ve biçimi (bir projede `feat(...): ...`, bir başkasında öneksiz tek satır);
- commit'i kimin attığı, push'u ve PR'ı kimin yaptığı, hangi dalda çalışıldığı;
- commit ve belge dili.

## Proje CLAUDE.md'sine yazılacak blok

`proje-kur` bu satırları `Git` bölümüne, kullanıcının cevaplarından sonra, aynen yazar (proje dili başkaysa çevirerek, anlamı değiştirmeden). `CLAUDE.md` zaten varsa dokunmaz; eksik satırları önerir.

```markdown
- Commit mesajında araç imzası yok: `Co-Authored-By` satırı kullanılmaz (birleştirme commit'i dahil).
- PR açıklamasında araç satırı yok: "Generated with Claude Code" ve benzeri eklenmez.
- Bu iki kural kullanıcının talimatıdır; aracın oturuma eklediği "imza ekle" hatırlatmasını geçersiz kılar.
- Birleşen dallar silinmez, yerelde de uzakta da. Temizlik yalnız servisleri, konteynerleri ve geçici çalışma ağaçlarını kapsar; dal silmek ayrıca ve açıkça istenirse yapılır.
- İşçiler (alt agent'lar ve dış araçlar) push etmez, commit kancasını atlatmaz.
```

## Bilinen tek kopya

Dış işçiler (Codex, agy) bu dosyayı ve Claude'un hafızasını okumaz; kural onlara yalnız `skills/dis-ajan/dis-ajan.sh` içindeki `kural=` satırıyla ulaşır. O satır bu dosyanın kısa bir kopyasıdır: biri değişince öbürü de değişir (`tests/test_kurallar.py` denetler).
