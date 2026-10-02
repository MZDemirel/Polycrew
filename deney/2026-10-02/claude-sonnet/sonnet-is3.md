dal deney-a2-sonnet, commit 17b62cf "Piksel tozu temizliği: aynı malzemede tek kalan ton komşuların tonunu alır"
light.py remove_specks(p, tone), with_tones çağırıyor; tests/export/test_light_specks.py; conformance yeniden üretildi.
Kural: 4 komşu aynı malzeme ve hepsi başka ton → çoğunluk; 2-2 eşitlik: kendi tonuna en yakın, sonra koyu. Kenar/boş/başka malzeme: dokunma. Girdi tonlarından karar.
Kendi ölçüsü: şövalye 128 17,05→1,2; 96 9,2→1,0; köylü 48 1,1→0,0. 48 önizlemesine bakmadı.
Komutlar: pytest tests/export 89 geçti (conformance yeniden üretildikten sonra), node 18, ruff, pyright temiz.
süre 297,6 sn; 58827 token; 18 araç
