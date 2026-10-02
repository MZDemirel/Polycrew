# Görev: Pixlender Aşama 6.6 madde 3 — kontur biçimi (B2)

Çalışma klasörü (git worktree, kendi dalın): <pixlender>/.claude/worktrees/b2-kontur , dal `b2-kontur`.
Önce `AGENTS.md`, `CLAUDE.md`, `docs/format/sprites-3.md`, `docs/decisions/0046-ic-cizgiler.md` (iç çizgiler; sözleşmeye seçenek nasıl eklendi, örnek o) ve `docs/decisions/0049-ton-isik.md` (ışık yönü) oku. Bütün komutlarda mutlak yol.

## Dosya sınırı
Dokunabileceğin dosyalar:
- `src/pixlender/export/light.py`, `src/pixlender/export/sprites.py`, `src/pixlender/export/combine.py`, `src/pixlender/project.py`, `src/pixlender/cli.py`, `src/pixlender/character/build.py`, ve `light.finish`/`draw`/`still`'i çağıran öteki modüller (yalnız yeni parametreyi geçirmek için)
- `src/pixlender/viewer/static/sprites3.js`, `examples/flame/lib/pixlender.dart`, `examples/flame/test/conformance_test.dart`, `examples/godot/pixlender/pixlender_sheet.gd`, `examples/godot/tests/conformance.gd`
- `conformance/generate.py`, `conformance/sprites-3/cases.json` ve `conformance/` altındaki üretilen dosyalar (elle değil, `uv run python conformance/generate.py` ile)
- testler: `tests/export/test_outline_styles.py` (yeni), `tests/js/sprites3.test.mjs` ve mevcut testlerde gerekli küçük güncellemeler
- `docs/format/sprites-3.md`, `CLAUDE.md`'deki `animate` komut satırı (yalnız yeni seçeneği bir cümleyle anmak için)
`PLAN.md`, `SONRAKI_OTURUM.md`, `docs/decisions/` ve `spikes/`'a dokunma (karar notunu PM yazar). Yeni paket ekleme. Git kancasını atlatma. Push ve `main`'e birleştirme yok. Dosya sınırı yüzünden bir şey yapamıyorsan, dosyayı en küçük değişiklikle düzenle ve son mesajında gerekçesini yaz (durup bekleme: kimse cevap veremez).

## İş
Bugün kontur `light.outline` bool: `true` = renkli (en yakın dolu komşunun malzemesinin 0. basamağı), `false` = yok. Dört biçim olacak: `outline: renkli|siyah|secici|yok` (proje dosyası `pixlender.yaml`; CLI `animate` ve `build`'de `--outline <biçim>`; mevcut `--no-outline` `yok` anlamında çalışmaya devam etsin).

1. **renkli:** bugünkü kural, bayt bayt aynı.
2. **yok:** bugünkü `false`, bayt bayt aynı.
3. **siyah (JRPG):** dış kontur tek bir mürekkep rengiyle. Renk: paletli projede paletin en koyu rengi; serbest kipte saf siyah değil, çok koyu renkli bir ton (öneri `(24, 20, 37)`, koyu mor-lacivert; sabit olarak yaz). İç çizgiler açıksa (`lines: ic`) iç çizgiler de aynı mürekkeple.
4. **secici (sel-out):** ışık alan yandaki kontur pikseli 0. basamak yerine **1. basamak** (malzemenin gölge tonu) alır; öteki yanlar 0. basamak. Işık yanı A3'ün ışık yönünden: `sol_ust` → `[-1, 1]` (sol ve üst), `sag_ust` → `[1, 1]`, `ust` → `[0, 1]`. Bir kontur pikseli, kendisinden ışık yönüne bakan komşusu boşsa ve karşı yandaki komşusu doluysa ışıklı yandadır (kuralı belgeye açıkça, komşu sırası ve eşitlikle yaz; dört uygulama aynı sonucu vermeli).
5. **Sözleşme (`sprites/3` kalır):** `light.outline` `true`/`false` (renkli/yok, bugünkü gibi) ya da `"siyah"`/`"secici"` dizgesi. `siyah`ta `light.outline_color: [r, g, b]`, `secici`de `light.lit_side: [sx, sy]` yazılır; ikisi de yalnız o biçimde. Okuyucu (Python `combine`, JS, Flame, Godot) bilinmeyen değerde hata verir; her birinde testi olsun.
6. **Uyum verisi:** `conformance/` altına iki yeni vaka: `siyah` (iç çizgili, mürekkep aynı) ve `secici`. Var olan vakalar bayt bayt aynı kalmalı. Üç bağdaştırıcı yeni vakaları geçmeli.

## Bitti ölçütü
- `tests/export/test_outline_styles.py`: renkli ve yok bugünküyle bayt bayt aynı; siyahta bütün kontur pikselleri tek renk ve iç çizgi aynı renk; seçicide ışıklı yandaki kontur pikselleri 1. basamak, öbürleri 0; `sag_ust`'ta ışıklı yan aynalanır; bilinmeyen biçim hata; proje alanı ve CLI önceliği.
- Koş: `uv run pytest -q tests/export tests/js`, `uv run pytest -q tests/test_engine_adapters.py` (Flame ve Godot; kum havuzunda Flutter önbelleği yazılamayabilir: o zaman Dart ve GDScript kodunu dikkatle elle yaz, PM dışarıda koşar; söyle), sonra `nice -n 10 uv run pytest -q`. `uv run ruff check . && uv run ruff format --check .`, `uv run pyright` temiz.
- Karşılaştırma resmi: köylü ve şövalye, 48, `Walk_Loop`, `--fps 4 --dirs 1 --jobs 2`, dört biçim (renkli, siyah + `--lines ic`, secici, yok), hem koyu (`#20202a`) hem açık (`#e8e4d8`) zeminde: `<worktree>/out/b2/b2-karsilastirma.png` (3×, nearest). `out/` commit'lenmez.
- Tek commit (Türkçe, tek satır, imza yok): `Kontur biçimi: renkli, siyah, seçici, yok; proje seçeneği ve üç bağdaştırıcı`.

## Son mesaj
Türkçe, en çok 300 kelime: değişen dosyalar, ışıklı yan kuralının tam tanımı, test sayıları ve süre (tam takım, JS, Flame, Godot ayrı), ruff/pyright, eski vakalar bayt bayt aynı mı, resim yolu, commit hash'i, dosya sınırının dışına çıktıysan nerede ve neden, emin olmadığın şey.
