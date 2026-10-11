# 0010: Kotanın ve sürenin otomatik ölçülmesi

- **Tarih:** 2026-10-11
- **Durum:** Kabul edildi; `0009`'un maliyet eşitlik bozucusuna veri sağlar.

## Bağlam

Maliyet sıralamaya yalnız eşitlik bozucu olarak girebildi (`0009`), çünkü 106 puan kaydının 5'inde kota, 69'unda süre vardı. İkisini PM elle yazıyordu. Betik süreyi zaten ölçüyor, kotayı okuyabiliyordu.

## Kararlar

1. Kota okuma `external-agent.sh` içinde iki fonksiyona taşındı (`kota_codex`, `kota_agy`); `quota` alt komutu ve koşu yolu aynı kodu kullanır. `quota`'nın çıktısı ve yazdığı olay değişmedi.
2. Her koşudan hemen önce ve sonra o koşunun harcadığı pencere okunur (`kota_yuzde`): Codex'te 5 saatlik pencere; agy'de modelin grubu (adında `claude` ya da `gpt` varsa Claude/GPT, yoksa Gemini), 5 saatlik pencere, yoksa haftalık. Fark `kota.json`'a (`once`, `sonra`, `fark`, `pencere`, `neden`) ve `isci_bitti` olayına (`kota`) yazılır. Birim: pencerenin yüzde puanı.
3. Codex'in kotası son oturum kaydından okunur ve eski bir pencereden kalmış olabilir: kaydın yenilenme saati geçmişse "önce" 0 sayılır (yeni pencere sıfırdan başlar). Gerçek okumada görüldü: son kayıt %11, yenilenme saati bir saat önce.
4. Fark yanıltıcı olacaksa yazılmaz ve nedeni kaydedilir: okunamadı; pencere arada yenilendi (sonra < önce ya da pencere değişti); aynı aracın başka bir koşusu çakıştı (`events.py overlap`; 6 saatten eski, bitişi gelmemiş koşu sayılmaz).
5. `events.py score` kota ve süreyi iş kimliğinden bulup yazar (`is_bilgisi`); elle verilen değer önceliklidir. Claude agent'ında süre başlangıç ve bitiş olayından gelir; Claude kotası CLI'dan okunamadığı için boş kalır.
6. `EXTERNAL_AGENT_NO_QUOTA=1` ölçümü kapatır (agy'de koşu başına iki ek `/quota` çağrısı).

## Testler

71 test yeşil (63 + 8). Yeni `tests/test_external_agent.py` betiğin koşu yolunu ilk kez sınıyor; geçici `HOME` ve `PATH`'te sahte `codex` ve `agy` ile, gerçek araç çağrılmadan: Codex'te 40 → 52 = 12; agy'de Gemini ve Claude gruplarının ayrı ölçülmesi; pencere yenilenmesi; eski pencereden kalan kaydın 0 sayılması; çakışan koşu (başka araç çakışma sayılmaz); ölçümün kapatılması; `quota` çıktısı ve şemaya yeni alan girmemesi; puana kendiliğinden yazılması ve elle verilenin ezmesi; Claude agent'ında yalnız sürenin dolması.

## Açık kalan

- `external-agent.sh quota` gerçek araçlarla, geçici günlükle çalıştırıldı: altı kova, biçim öncekiyle aynı.
- Gerçek bir Codex ya da agy koşusu yapılmadı (kota harcar). Sahte araçlar gerçek biçimi taklit ediyor ama Codex'in koşu sonunda oturum dosyasına `rate_limits` yazdığı varsayımı yalnız `quota`'nın bugüne kadarki davranışına dayanıyor.
- agy kalan oranı yuvarlayarak veriyorsa küçük koşularda fark 0 görünebilir.
- Paralel koşular ölçülmüyor; takım işinde koşuların çoğu paralelse veri yine yavaş birikir.
- Veri birikince maliyeti puana katmak ayrı karar.
