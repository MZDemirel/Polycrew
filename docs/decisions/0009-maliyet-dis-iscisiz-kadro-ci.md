# 0009: Yeniden puanlama, maliyet eşitlik bozucu, dış işçisiz kadro, CI

- **Tarih:** 2026-10-11
- **Durum:** Kabul edildi; `0004` ve `0008`'in sıralamasını tamamlar.

## Bağlam

Aşama 3'ten dört madde. Aynı işe verilen ikinci puan iki satır sayılıyordu; sıralama yalnız puana bakıyordu; Codex ve agy kurulu olmayan makinede kadro önerisi hâlâ onları gösteriyor, betik anlaşılmaz biçimde düşüyordu; depoda otomatik denetim yoktu.

Gerçek defter (salt okunur): 106 kayıtta tekrarlı iş kimliği yok; `kota` 5, `sure` 69 kayıtta dolu.

## Kararlar

1. **Yeniden puanlama.** Okurken aynı `(proje, id)` için son kayıt kalır (`roster.tekillestir`). `id`'siz kayıtlara dokunulmaz. Defter eklemeli kalır; geçmiş dosyada durur.
2. **Maliyet yalnız eşitlik bozucu.** Kota verisi puana katılacak kadar yok. Puana göre sıralandıktan sonra tek geçiş: komşu iki işçinin farkı ≤ 0,10 ise ve alttaki belirgin ucuzsa (ikisinde de kota varsa %20 az kota; yoksa ikisinde de süre varsa %20 kısa süre) yer değiştirir. Öne geçen `cheaper` / `faster` diye işaretlenir. `--no-cost` kapatır. Eşikler `roster.py`'nin başında (`YAKIN_PUAN`, `BELIRGIN`).
3. **Kurulu olmayan araç.** İşçi adı `codex/` ya da `agy/` ile başlıyor ve araç `PATH`'te yoksa öneriden çıkar; tablonun altına "Left out (not installed)" yazılır. `--providers` ve `POLYCREW_PROVIDERS` algılamayı ezer. `external-agent.sh` araç yoksa kayıt klasörü açmadan çıkış 4 ile durur; `quota` "not installed" der.
4. **CI.** `.github/workflows/ci.yml`: birim testleri (Python 3.11 ve 3.14), `bash -n`, manifestlerin JSON olarak okunması; ayrı bir işte `claude plugin validate .`. Doğrulama yerelde boş bir `HOME` ile (oturum açmadan) geçti, o yüzden eklendi.

## Ölçümler ve testler

- 63 test yeşil (59 + 4): yeniden puanlama ve defterin değişmemesi; eşitlik bozucunun altı durumu (yakın ve hızlı, kapalı, uzak puan, az fark, veri yok, kota önceliği); sağlayıcı süzgeci `suggest` ve `summary`'de; yapay `PATH` ile betiğin çıkış 4'ü ve `quota`'nın "not installed" demesi.
- Gerçek defterde `developer` + `py` sıralaması değişmedi: yakın puanlı tek çift (codex 3,99 ve opus 3,98) zaten hızlı olan üstte.
- `POLYCREW_PROVIDERS=claude roster.py summary`: yedi satırın hepsi Claude rolü, altta "Left out (not installed): agy, codex".

## Açık kalan

- CI yerelde çalıştırılamadı: yalnız Python 3.14 kurulu, 3.11 denenmedi; `plugin-validate` işindeki npm kurulumu denenmedi. İlk push'ta bakılmalı.
- Süre sağlayıcılar arasında aynı şeyi ölçmüyor olabilir (bekleme, kota kuyruğu); eşitlik bozucu bu yüzden dar tutuldu. Kotanın otomatik ölçülmesi ayrı madde.
- Bir aracın kurulu olması oturum açık olduğu anlamına gelmez; o durumda betik aracın kendi hatasıyla döner.
