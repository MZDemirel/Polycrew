"""Ton öksüzü (0041): görünen giyili katmanlarda, aynı malzemedeki dört komşusu da başka ışık
basamağında olan piksel. Kare başına ortalama. Kullanım: python oksuz.py <tarif> <res> [kare]."""
import sys
from pathlib import Path

import numpy as np

from pixlender.character.animations import find_animation
from pixlender.character.build import load_worn
from pixlender.character.gltf import TEMPLATE_PATH
from pixlender.core.animation import frame_times
from pixlender.core.skeleton import load_template
from pixlender.export.sprites import Task, sample_direction

recipe, res = Path(sys.argv[1]), int(sys.argv[2])
ch = load_worn(recipe)
a = find_animation("Walk_Loop")
times = tuple(frame_times(a, 15))
s = sample_direction(ch, load_template(TEMPLATE_PATH), Task(a, times, res, "front_right", 0.0))
counts = []
for f in s.frames:
    n = 0
    for lid in s.shown:
        p = f[lid]
        m, t = np.asarray(p.material), np.asarray(p.tone)
        h = m > 0
        ok = h.copy()
        diff = h.copy()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            mm = np.roll(m, (dy, dx), (0, 1)); tt = np.roll(t, (dy, dx), (0, 1))
            ok &= mm == m
            diff &= tt != t
        ok[0, :] = ok[-1, :] = False; ok[:, 0] = ok[:, -1] = False
        n += int((ok & diff).sum())
    counts.append(n)
print(f"{recipe.stem} {res}: kare başına ton öksüzü ort {np.mean(counts):.1f} (en az {min(counts)}, en çok {max(counts)}, {len(counts)} kare)")
