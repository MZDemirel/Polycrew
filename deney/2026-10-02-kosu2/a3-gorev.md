# Görev: Pixlender Aşama 6.6 madde 5 — ton sayısı ve ışık yönü (A3)

Çalışma klasörü (git worktree, kendi dalın): <pixlender>/.claude/worktrees/a3-ton-isik , dal `a3-ton-isik`.
Önce `AGENTS.md` ve `CLAUDE.md`'yi oku. Bütün komutlarda mutlak yol kullan.

## Dosya sınırı
Yalnız şu dosyalara dokun:
- `src/pixlender/export/light.py`
- `src/pixlender/export/sprites.py`, `src/pixlender/project.py`, `src/pixlender/cli.py`
- `with_tones` ya da `light.tones`'u çağıran öteki modüller (grep ile bul; yalnız yeni parametreyi geçirmek için)
- yeni test dosyası `tests/export/test_light_tones.py` ve mevcut testlerde gerekli küçük güncellemeler
- `docs/format/sprites-3.md` (yalnız `light` nesnesinin satırı)
`PLAN.md`, `SONRAKI_OTURUM.md`, `docs/decisions/` ve `spikes/`'a dokunma; karar notunu PM yazar. Yeni paket ekleme. Git kancasını atlatma ya da kapatma. Push yok, `main`'e birleştirme yok.

## İş
Bugün ışık sabit: `light.LIGHT` (sol üstten) ve üç ton (SHADOW, MID, LIT). Projeye iki seçenek eklenecek:

1. **`light.py`:**
   - `LIGHTS: dict[str, np.ndarray]`: `"sol_ust"` = bugünkü `LIGHT` (değeri aynı kalsın), `"sag_ust"` = x'i aynalanmış hâli, `"ust"` = x'i 0 olan hâli (normalize). `DEFAULT_LIGHT = "sol_ust"`, `DEFAULT_TONES = 3`. `LIGHT` adı geriye dönük kalsın (`LIGHTS["sol_ust"]`).
   - `light_vector(direction: str) -> np.ndarray`; bilinmeyen yönde `ValueError`.
   - `tones(normal, direction=DEFAULT_LIGHT, count=DEFAULT_TONES)`:
     - `count == 3`: bugünkü kural, aynı eşikler.
     - `count == 2` (cel): yalnız SHADOW ve MID. Eşik `TWO_TONE_SPLIT` (n·L bunun altındaysa SHADOW); değeri sen seç ve gerekçesini sabitin yorumuna yaz (öneri: SHADOW_BELOW ile LIT_ABOVE arasında, gölge gövdenin bir yanında tek büyük şekil olsun).
     - `count == 1` (düz renk): her şey MID.
     - başka değerde `ValueError`.
   - `with_tones(p, direction=DEFAULT_LIGHT, count=DEFAULT_TONES)`: `remove_specks` (0045) bütün sayılarda çalışmaya devam eder.
2. **Proje dosyası** (`project.py`, `pixlender.yaml`): `light: sol_ust|sag_ust|ust` ve `tones: 1|2|3` alanları; varsayılanlar yukarıdaki. `project init`'in yazdığı şablona yorum satırıyla ekle (`view:` satırı gibi).
3. **CLI:** `animate` ve `build`'e `--light` ve `--tones` (proje dosyasındaki değeri ezer; CLAUDE.md'deki "seçenekler her zaman önce gelir" kuralı). Görev (Task) ya da çağrı zincirinde bu değerler `with_tones`'a ulaşsın; yön süreçlere dağıtıldığında (`sample_tasks`, `--jobs`) da.
4. **JSON (`sprites/3`):** `light` nesnesine `direction` ve `tones` **yalnız varsayılan dışında** yazılır. Varsayılan çıktı bayt bayt aynı kalmalı: `conformance/` hiç değişmemeli (`uv run python conformance/generate.py` sonrası `git status` temiz). Tonlar sayfalara pişmiş olduğu için bağdaştırıcılar (JS, Flame, Godot) değişmez; ama bu anahtarlar onları bozmamalı. `docs/format/sprites-3.md`'deki `light` satırına iki anahtarı ekle ("bilgi amaçlı; okuyucu yok sayabilir").

## Bitti ölçütü
- `tests/export/test_light_tones.py`: `count=1` her pikselde MID; `count=2` yalnız SHADOW ve MID; `sag_ust`, x'i aynalanmış bir normale `sol_ust`'un o normale verdiği tonu verir; `ust` simetrik; bilinmeyen yön ve sayı `ValueError`; proje dosyası alanları okunuyor ve yanlış değer hata veriyor; CLI'daki seçenek proje dosyasını eziyor; varsayılanla JSON'da `direction`/`tones` yok, `--tones 2` ile var.
- Koş: `uv run pytest -q tests/export tests/test_project.py tests/test_cli.py` (adlar farklıysa ilgili dosyaları bul), sonra `nice -n 10 uv run pytest -q` (tam takım; UAL `assets/ual` kısayolunda). `uv run ruff check . && uv run ruff format --check .` ve `uv run pyright` temiz.
- Karşılaştırma resmi: `nice -n 10 uv run pixlender animate examples/characters/sovalye.yaml --anim Walk_Loop --res 48 --fps 4 --dirs 1 --jobs 2 --out <worktree>/out/a3/<ad>` ile dört çeşit: varsayılan, `--tones 2`, `--tones 1`, `--light sag_ust`; aynısı `examples/characters/koylu.yaml`. Dört satırı tek resimde birleştir: `<worktree>/out/a3/a3-karsilastirma.png` (3× büyütülmüş, nearest). `out/` git dışında; commit'leme.
- Commit (tek, Türkçe, tek satır, imza yok): `Ton sayısı ve ışık yönü: proje seçeneği, --tones ve --light`.

## Son mesaj
Türkçe, en çok 250 kelime: ne değişti (dosya listesi), `TWO_TONE_SPLIT`'in değeri ve gerekçesi, test sayıları ve süre, ruff/pyright, `conformance/` değişmedi mi, resim yolu, commit hash'i, yapamadığın ya da emin olmadığın şey.
