# Görev: A1 dalını gözden geçir (yalnız oku, hiçbir dosyayı değiştirme)

Depo: <pixlender>/.claude/worktrees/agent-a3caee5ddac3de62e
Dal: worktree-agent-a3caee5ddac3de62e, tek commit `35b8a80` "Serbest rampada renk tonu kayması ve geniş değer basamakları", tabanı `main`.
Proje kuralları: <pixlender>/CLAUDE.md (oku).
Diff hazır: <pixlender>/.claude/worktrees/a1.diff (src ve tests; conformance/ resimleri yeniden üretildi, onlara bakma). Dosyaları depo klasöründen oku.

**Komut kuralı:** HİÇBİR kabuk komutu çalıştırma (git, grep, pytest dahil); izinsiz ilk komut bütün işini çıktısız bırakır. Yalnız dosya okuma aracını kullan: diff dosyasını ve depodaki kaynak/test dosyalarını oku. Testler PM tarafından koşuldu: dalda 820 test geçti.

## İşin amacı (PLAN, Aşama 6.6 madde 1)
`src/pixlender/palette/ramps.py` `free_ramp`: serbest (palete bağlı olmayan) rampada
- gölge soğuğa (mora-maviye), aydınlık sıcağa (sarıya) kayar; değer basamakları genişler;
- ten gölgesi kırmızıya gider, maviye değil; tende kayma ≤ 15°;
- gri ve düşük doygunluklu renkler kaymaz; palet kipinde hiçbir şey değişmez;
- ölçütler: aydınlık − orta ≥ 0,10 OKLab L; gölgede ton kayması 15–30°; en koyu basamak L ≥ 0,12; ten aydınlığı L ≤ ~0,90;
- koyu malzemelerde 0,12 tabanı kontur farkından (`MIN_OUTLINE_DROP`) önce gelir; palet çıkarma (`extract.py`) 0,2'de kalır.

## Ne bekliyorum
1. Gerçek hatalar: yanlış işaret, sınır/eşik hatası, açı sarması (hue wrap, 0/360), NaN, gri renkte bölme, palet kipinin etkilenmesi, determinizm.
2. Ölçütlerin testlerle gerçekten denetlenip denetlenmediği (`tests/palette/test_free_ramp.py`); eksik test.
3. Silinen testler (`tests/palette/test_library.py` 8 satır silindi): gerekçeli mi, bir davranış korumasız mı kaldı?
4. Proje kurallarına uyum (CLAUDE.md "Mimari kurallar").

Her bulgu için: dosya:satır, ne yanlış, somut örnek (girdi → yanlış çıktı), önem (yüksek/orta/düşük). Emin olmadığını "olası" diye işaretle. Yanlış alarm puan kaybettirir; bulgu yoksa "bulgu yok" yaz.

Son mesaj biçimi: Türkçe, başlık "Bulgular", numaralı liste; en sonda tek satır hüküm: "birleşebilir" / "düzeltmeyle birleşebilir" / "birleşmemeli".
