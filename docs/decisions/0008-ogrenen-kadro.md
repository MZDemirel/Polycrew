# 0008: Öğrenen kadro: solan puan, sürümlü işçi adı, "dene" önerisi

- **Tarih:** 2026-10-11
- **Durum:** Kabul edildi; `0004`'ün (dinamik kadro) sıralamasını değiştirir.

## Bağlam

Puan defteri kalıcı ama öneri zamanı tanımıyordu: üç ay önceki puan dünküyle eşit sayılıyordu. Kullanıcının kaygısı: uzun hafıza, yeni bir model iyi olsa da onu "kötü" diye hatırlatır. İki ayrı sorun çıktı: zaman ağırlığı yoktu, ve Claude rollerinde işçi adı sürümsüzdü (`claude/developer/sonnet`), yani yeni Sonnet eskisinin puanlarını devralacaktı. Dış işçi adları zaten sürümlü. Üçüncüsü: az verili işçi hiç önerilmediği için puanı hiç oluşmuyordu.

## Kararlar

1. **Yarı ömür 30 gün.** Ağırlık `0,5 ^ (yaş / 30 gün)`; düzeltilmiş puan `(3,5·2 + Σ w·not) / (2 + Σ w)`. Puan silinmez, önsele (3,5) doğru çekilir. `--half-life` ile değişir, 0 kapatır. `ts`'siz kayıt tam ağırlık alır. Defter 8 günlük olduğu için değer ölçülmedi, seçildi: model sürümleri birkaç ayda bir değişiyor, 30 günle eski izlenim iki üç ayda silikleşiyor.
2. **Etkin n.** Tabloda ham `n` yanında `Eff. n` (Σ w). "little data" etkin n < 3'e bakar; eski verisi çok olan işçi de zamanla "little data"ya düşer ve önsel tablo (`roster.md`) söz sahibi olur.
3. **Sürümlü işçi adı.** Kanca `SubagentStop`'ta transkriptin başından gerçek modeli okur (`<synthetic>` atlanır, en çok 400 satır) ve `agent_bitti` olayına yazar. `events.py score`, sürümsüz `claude/<rol>/<ad>` verildiğinde iş kimliğinden modeli bulup adı `claude/developer/sonnet-5-5` yapar. Bulamazsa adı bırakır ve uyarır. Verilen ad modelin ailesiyle uyuşmuyorsa (`opus` yazılmış, model sonnet) dokunmaz.
4. **Eski satırlar.** 2026-10-12'den önceki sürümsüz Claude satırları okurken `sonnet-5-5` / `opus-5-5` sayılır (`SURUM_SINIRI`). Dayanak: o dönemin var olan 34 transkriptinin hepsi 5-5 ailesinden. Dosya değişmez.
5. **"Dene" sütunu.** `summary` her rol + alan için bir aday önerir: aynı rolde görülmüş, bu rol + alanda etkin n < 3, kadro ya da yedek değil, ve rolün bütününde düzeltilmiş puanı önselin altına düşmemiş. Adaylardan rolde en iyi puanlı seçilir. `session-start` bunu kolay bir işe verir; bağlayıcı değil.
6. Takım **yapısı** (lider var mı, kaç geliştirici) puana göre kendiliğinden değişmez; öneri olarak ayrı bir madde (Aşama 3).

### Denenip bırakılan

- "Dene" adayı olarak en az verili işçi: gerçek defterde `developer/py` için orada 1 puan almış işçiyi önerdi. Önselin altına düşeni dışlayan ve rolde en iyiyi seçen kurala geçildi.

## Ölçümler (gerçek defter, `developer` + `py`, salt okunur)

| İşçi | n | Solmasız | Bugün (etkin n) | 90 gün sonra, yeni puan yoksa (etkin n) |
|---|---|---|---|---|
| claude/developer/sonnet-5-5 | 11 | 4,38 | 4,35 (9,4) | 3,88 (1,2) |
| codex/gpt-6.1-sol/high | 21 | 4,00 | 3,99 (18,6) | 3,79 (2,3) |
| claude/developer/opus-5-5 | 5 | 4,00 | 3,98 (4,6) | 3,66 (0,6) |
| agy/gemini-3.1-pro-high | 1 | 2,67 | 2,79 (0,8) | 3,38 (0,1) |

Bugün sıralama değişmiyor (veri taze). Üç ayda bütün işçiler "little data"ya iniyor ve kötü puanlı işçi 3,38'e çıkıp yeniden denenebilir hâle geliyor: istenen davranış.

## Testler

59 test yeşil (53 + 6): ağırlığın yarı ömrü, 0 ve `ts`'siz durum; eski 5 puanlı işçinin yeni 4 puanlının altına düşmesi ve "little data" olması; sınır tarihinden önceki ve sonraki sürümsüz satır; `score`'un sürümü eklemesi, bulamayınca uyarması, sürümlü ve başka aileden ada dokunmaması; kancanın modeli yazması; "dene" sütununda aday, rolde en iyinin seçilmesi, kötü puanlının dışlanması.

## Açık kalan

- Gerçek bir takım koşusunda kancanın modeli yazdığı ve `score`'un sürümü eklediği denenmedi (sentetik olay ve sahte transkriptle test edildi). Transkript biçimi Claude Code sürümüyle değişirse sürüm bulunamaz; uyarı çıkar, ad elle yazılır.
- Yarı ömür birkaç haftalık veri birikince yeniden değerlendirilmeli.
- `SURUM_SINIRI` tek seferlik bir köprü; haiku satırı yoktu, eşlemede yok.
- Aynı işin yeniden puanlanması ve sıralamada kota ile süre hâlâ açık (Aşama 3).
