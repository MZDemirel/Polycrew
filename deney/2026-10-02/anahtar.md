# Cevap anahtarı (adaylara gösterilmez)

## İş 1 (her soru: doğru 2, kısmen 1; kanıt dosya:satır doğruysa +0,5 bonus, en çok 12,5)
1. Sıra yukarı, aşağı, sol, sağ; önce gelen kalır. Python `src/pixlender/export/light.py:40` (`_NEIGHBOURS`, `finish` 146), JS `src/pixlender/viewer/static/sprites3.js:12`, Flame `examples/flame/lib/pixlender.dart:151`, Godot `examples/godot/pixlender/pixlender_sheet.gd:11`. Ayrıca belge `docs/format/sprites-3.md:113`.
2. `loop and speed >= RUN * character.height` (RUN = 1,5 boy/sn; speed = ground_speed, m/sn), `core/held.py` `keep_clear`; `carry` olan eşya. Test: `test_a_walk_or_an_attack_is_not_carried` (237) ve/veya `test_only_a_fast_loop_carries` (152), `tests/core/test_held.py`.
3. `free_ramp`, `src/pixlender/palette/ramps.py:165`; `FREE_RAMP = (90, 184, 256, 292)` /256 (satır 29).
4. `edge_step(resolution) = max(2, round(3 * resolution / 48))` → 96'da 6; `src/pixlender/export/light.py:139`.
5. `~/.cache/pixlender/blender/<id>/` (XDG_CACHE_HOME varsa o); `src/pixlender/render/blender.py` (satır 5 belge, 60 kod).

## İş 2 (gizli hatalar: her biri bulundu 2, yeri doğru ama açıklama eksik 1; yanlış alarm −1; en çok 8)
H1 döngü şartı: `runs = loop or speed >= ...` (and olmalı) — `held.py keep_clear`.
H2 işaret: `carry_moves` içinde `(grip[1] - MARGIN)` (MARGIN - grip[1] olmalı): uç yere girer.
H3 eşik: `_Frame.turn` içinde `> DEPTH` (>= -DEPTH olmalı): bedene 1 cm'den az giren de… aslında DEPTH'e kadar dışarıdakiler bile döner; sürtünme kuralı bozulur.
H4 birim: `animate.clip_moves` `keep_clear(..., speed / character.height)` (m/sn yerine boy/sn; eşik RUN*height ile karşılaştırıldığı için koşu hiç taşımaz).
Zararsız (alarm verilmemeli): `own` → `turned` yeniden adlandırma, docstring cümlesi, yorum.

## İş 4 (görsel; her soru doğru 1, kısmen 0,5; en çok 7)
V1 iki karakter: köylü kadın (kılıç seçenek) ve şövalye; 4'er satır (sağ önce, sağ sonra, ön-sağ önce, ön-sağ sonra), 10'ar kare.
V2 "sonra (0044)": bıçak aşağı-geri, ucu yere doğru / kabzanın altında, kareler arası tutarlı.
V3 "önce (0042)" ilk iki kare: bıçak dik, yukarı, kafanın arkasında/üstünde.
V4 köylü kadın mavi elbise (uzun etek); "sonra" satırlarında bıçak eteğin üstünden/önünden geçiyor.
V5 şövalyenin pelerini kırmızı, arkasında (sağa bakarken solda / geride).
V6 0041-diller.png: 17 sütun, 3 satır (köylü, şövalye, yolcu).
V7 13. sütun (Game Boy) yeşil tonlu, karakterler tek yeşil kütle.
