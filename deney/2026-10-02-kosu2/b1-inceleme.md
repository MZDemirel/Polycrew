# Görev: B1 dalını gözden geçir (yalnız oku, dosya yazma)

Depo: <pixlender>/.claude/worktrees/agent-accb0e41f9e25ded5 (dal `worktree-agent-accb0e41f9e25ded5`, tek commit `309d29e`, tabanı `main` `ffbd0e7`).
Diff: <pixlender>/.claude/worktrees/b1.diff (üretilen resimler hariç). Proje kuralları: CLAUDE.md. Karar notu: docs/decisions/0046-ic-cizgiler.md; sözleşme: docs/format/sprites-3.md.
Testleri PM koştu (856 geçti, Node 24/24, Flame ve Godot uyum testleri geçti). İstersen dar bir kanıt için tek tek komut çalıştırabilirsin.

## İşin amacı
İç çizgiler (`lines: yok|ic`, proje dosyası ve `--lines`): önde kalan uzvun arkasındaki pikselde ve farklı malzeme sınırında (daha derin taraf) rampanın en koyusu; yüz (8 komşu) hariç; 3 pikselden kısa iz yok; dikiş kalınlığı `max(3, edge_step/2) + 1`; kıvrım eşiği `2 * edge_step`. Varsayılan (`yok`) çıktı bayt bayt aynı. `sprites/3` kalır; `lines` vb. yalnız varsayılan dışında yazılır; okuyucu bilinmeyen değerde hata verir. Kural dört yerde aynı olmalı: Python `export/light.py`, JS `viewer/static/sprites3.js`, Flame `examples/flame/lib/pixlender.dart`, Godot `examples/godot/pixlender/pixlender_sheet.gd`.

## Ne bekliyorum
1. **Dört uygulama arasında fark:** tamsayı/kayan nokta bölme (`edge_step / 2` JS'de ve GDScript'te farklı yuvarlanır mı?), komşu sırası, sınır pikselleri, eşitlik kuralı. Uyum verisinin bir farkı yakalamadığı bir durum varsa somut piksel/girdi örneğiyle göster.
2. Varsayılan çıktının değiştiği bir yol; `lines` anahtarının varsayılanda JSON'a yazılması; `combine` ile birleştirilen kombinasyonda çizginin unutulması.
3. Bilinmeyen `lines` değerinde üç okuyucu da hata veriyor mu?
4. Eksik test (özellikle 128 blok kolu: `edge_step/2 > 3`).
Her bulgu: dosya:satır, ne yanlış, somut örnek, önem; emin değilsen "olası". Yanlış alarm puan kaybettirir.
Son mesaj: Türkçe, "Bulgular" başlığı, numaralı liste, en sonda tek satır hüküm: "birleşebilir" / "düzeltmeyle birleşebilir" / "birleşmemeli".
