# Görev: B2 dalını gözden geçir (yalnız oku, dosya yazma)

Depo: <pixlender>/.claude/worktrees/b2-kontur (dal `b2-kontur`, tek commit `efc1232`, tabanı `main` `d17865f`). Diff: <pixlender>/.claude/worktrees/b2.diff (üretilen resimler hariç).
Spesifikasyon (görevin tam metni): <polycrew>/deney/2026-10-02-kosu2/b2-gorev.md. Bağlam: CLAUDE.md, docs/format/sprites-3.md, docs/decisions/0046-ic-cizgiler.md, 0049-ton-isik.md.
PM tam takımı koştu (944 geçti, Flutter, Godot, Node dahil). Dar kanıt için tek tek komut çalıştırabilirsin.

## Özellikle bak
1. Dört uygulamada (Python `export/light.py` + `combine.py`, JS `viewer/static/sprites3.js`, Flame `examples/flame/lib/pixlender.dart`, Godot `examples/godot/pixlender/pixlender_sheet.gd`) ışıklı yan kuralı, `siyah` mürekkebi (iç çizgiler dahil), `outline` bool/dizge ayrımı, `outline_color` ve `lit_side`'ın yalnız ilgili biçimde yazılması. Önceki incelemede JS ve Dart'ta `??` yüzünden açık `null` sessizce varsayılan sayılmıştı: yeni alanlarda aynı hata var mı? Dart'ta `outline` hem bool hem String olunca tip denetimi.
2. Varsayılan çıktının bayt bayt aynılığı; `--no-outline` hâlâ çalışıyor mu; proje dosyasında `outline` alanı ile eski projeler.
3. Paletli projede `siyah` paletin en koyusu mu; serbestte sabit.
4. `combine` (eşya kombinasyonu) yeni biçimleri doğru taşıyor mu.
5. Eksik test, CLAUDE.md mimari kurallarına aykırılık, kapsam aşımı.

Her bulgu: dosya:satır, ne yanlış, somut örnek (mümkünse koşup kanıtla), önem; emin değilsen "olası". Yanlış alarm puan kaybettirir.
Son mesaj: Türkçe, "Bulgular" numaralı liste; en sonda tek satır hüküm: "birleşebilir" / "düzeltmeyle birleşebilir" / "birleşmemeli".
