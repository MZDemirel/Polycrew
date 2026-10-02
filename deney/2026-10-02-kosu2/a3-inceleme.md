# Görev: A3 değişikliğini gözden geçir (yalnız oku, hiçbir dosyayı değiştirme)

Depo: <pixlender>/.claude/worktrees/a3-ton-isik (dal `a3-ton-isik`, değişiklikler henüz commit'lenmedi).
Diff hazır: <pixlender>/.claude/worktrees/a3.diff (src, tests, docs). Proje kuralları: <pixlender>/CLAUDE.md.

**Komut kuralı:** HİÇBİR kabuk komutu çalıştırma (git, grep, pytest dahil); izinsiz ilk komut bütün işini çıktısız bırakır. Yalnız dosya okuma aracını kullan. Testler PM tarafından koşuluyor.

## İşin amacı (Aşama 6.6 madde 5)
- `light.py`: `LIGHTS` (`sol_ust` = eski `LIGHT`, `sag_ust`, `ust`), `DEFAULT_LIGHT`, `DEFAULT_TONES = 3`, `light_vector`, `tones(normal, direction, count)`: 1 ton hep MID, 2 ton SHADOW/MID (`TWO_TONE_SPLIT`), 3 ton eski kural. `with_tones(p, direction, count)`; piksel tozu temizliği (`remove_specks`) her sayıda çalışır.
- Proje dosyası `light:` ve `tones:`; CLI `animate` ve `build`'de `--light`, `--tones` proje dosyasını ezer; yönler süreçlere dağıtılınca da değerler ulaşır.
- JSON `light` nesnesine `direction` ve `tones` yalnız varsayılan dışında; varsayılan çıktı bayt bayt aynı.
- Yüz (`export/face.py`) aynı ışıkla çizilir.

## Ne bekliyorum
1. Gerçek hatalar: bir çağrı yolunda değerin düşmesi (varsayılana dönmesi), süreç havuzunda (pickle) kaybolması, yüzün farklı ışıkla çizilmesi, `sag_ust`'un aynalanmasında işaret hatası, JSON'a varsayılanda anahtar yazılması, proje doğrulamasının yanlış değeri kabul etmesi.
2. Eksik test.
3. Kurallara uyum.

Her bulgu: dosya:satır, ne yanlış, somut örnek, önem (yüksek/orta/düşük); emin değilsen "olası". Yanlış alarm puan kaybettirir; bulgu yoksa "bulgu yok".
Son mesaj: Türkçe, başlık "Bulgular", numaralı liste; en sonda tek satır hüküm: "birleşebilir" / "düzeltmeyle birleşebilir" / "birleşmemeli".
