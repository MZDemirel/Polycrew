Bu bir geliştirme görevidir. Depo: Pixlender. Kuralları (AGENTS.md ya da CLAUDE.md) oku ve uy. Sen bu klasördeki git worktree'sinde, kendi dalında çalışıyorsun; `main`'e geçme, merge/rebase/push yapma.

## İş: piksel tozu temizliği (Aşama 6.6, madde 4; karar notu 0041)

Yüksek çözünürlükte (96, 128 blok) aynı malzemenin içinde tek başına kalan ışık tonu pikselleri "toz" gibi görünüyor. Elle çizilmiş HD piksel sanatında bunlar temizlenir.

- Yer: `src/pixlender/export/light.py`, `with_tones` (katman başına; ışık tonları `tones(normals(p))`).
- Kural: aynı malzemede dört komşusu (yukarı, aşağı, sol, sağ) da başka tonda olan tek piksel, komşularının çoğunluk tonunu alır (eşitlikte deterministik bir kural seç ve yaz). Dört komşusunun hepsi aynı malzemede değilse (kenar) dokunma.
- Yüz hariç: yüz `export/face.py` ile tonlardan sonra çiziliyor; yüzün çizildiği pikselleri bozmadığını denetle.
- Saf numpy, deterministik. Bağdaştırıcılar (JS, Flame, Godot) değişmez: bu katman verisi.

## Bitti
- Ölçü (PM'in ölçüsü, aynı tanım): görünen giyili katmanlarda, aynı malzemedeki dört komşusu da başka tonda olan piksel sayısı, kare başına ortalama, `Walk_Loop`, 15 kare/sn, ön-sağ yön. Bugün şövalye (`examples/characters/sovalye.yaml`) 128'de 17,1, 96'da 9,2; köylü (`examples/characters/koylu.yaml`) 48'de 1,1. Hedef: şövalye 128 ve 96'da en az yarıya; 48'de görünüm bozulmaz.
- Yeni test(ler): tek kalan ton pikseli düzeliyor, kenar pikseline dokunulmuyor, deterministik.
- İlgili testler yeşil: `uv run pytest tests/export -q` (tam takımı koşma; ağır). `uv run ruff check . && uv run ruff format --check .` ve `uv run pyright` temiz.
- Uyum verisi (`conformance/`) ışık tonlarından üretiliyorsa yeniden üret: `uv run python conformance/generate.py`, sonra `node --test tests/js/*.test.mjs`.
- Kendi dalında tek commit; mesaj Türkçe, tek satır, önek ve imza yok (örnek: "Piksel tozu temizliği: aynı malzemede tek kalan ton komşuların tonunu alır").

Son mesajın: değişen dosyalar, kural (eşitlik dahil), koştuğun komutlar ve sonuçları, ölçtüysen ölçü, commit hash'i. Kısa.
