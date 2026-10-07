# 0005: Claude kotası ve agent haritası

- **Tarih:** 2026-10-07
- **Durum:** Kabul edildi; `0003`'ün kota ve görünürlük kararını tamamlıyor.

## Bağlam

Kullanıcı kendi Claude limitinin agent haritasıyla aynı sayfada görünmesini istedi. Son tek `kota` olayını almak, Claude ölçümünü sonraki dış kota ölçümünde siliyordu; eski Codex ölçümü güncel görünüyordu.

## Kararlar

1. `claude-kota.py` yalnız PM'in verdiği masaüstü ölçümünü standart kütüphaneyle yazar. Argümansız kullanım salt okunur. Hafta ≥ %70 veya 5 saat ≥ %80 dış işçiye kaydırma uyarısı verir. Plan ve bağlam isteğe bağlıdır; bağımsız bir kota okuma API'si varsayılmaz.
2. Son olay `saglayici` + `grup` + `pencere` başına korunur. `olcum` yoksa olay `ts`'i kullanılır. API, her kovada `olcum_ts`, `yenilenir_ts`, `eski` verir. Ölçüm < yenilenme ≤ şimdi ise eski sayılır. İki kısaltılmış yenilenme biçimi yerel takvimde, ölçümün yılıyla çözülür; yıl devrini veya agy'nin kısaltırken kaybolan saat dilimini tahmin etmeyiz.
3. Başlatma kancası da kısaltılmış `ham` yükünü saklar; böylece çağıran agent bilgisi kaybolmaz. İşlerde `ust_id` ve `ust_kaynak`, API'de `harita` ve düğümlerde `cocuklar` bulunur. Açık üst agent/oturum kimliği, çağıran agent kimliği, üst transkript yolu ve bilinen agent kimliğine çözülebilen oturum kimliği sırasıyla kullanılır. Agent oturumunun `agent_session_id`/`subagent_session_id` alanı varsa kimlik eşlemesine eklenir.
4. Ortak `session_id` tek başına üst agent kanıtı değildir. Eksik üst, pencere dışında kalan üst ve döngü PM altında görünür. Dış işçiler her zaman PM altındadır. PM sanal bir özettir; gerçek modeli ve bağımsız süresi bilinmez. Aynı zaman penceresindeki birden çok ana oturum bu kökte toplanır.
5. Ağaç filtrelenmiş işlerden yeniden kurulur; canlı API ve durağan rapor aynı veriyi kullanır. Harita satırları iç içe genişlik biriktirmez; girinti üç düzeyle sınırlanır, tam ilişki “başlatan” metninde korunur. Düğümler mevcut yan paneli açar.

## Ölçümler ve testler

- Gerçek günlük salt okunur incelendi: 106 Claude agent olayı; 86 `ham` yükünde `session_id` ve `transcript_path`, açık üst agent/oturum alanı yok. Eldeki kayıtların kesin lider–işçi ilişkisi kanıtlanamıyor; PM altına yerleşirler.
- Birim testleri: kota birleşmesi, ölçüm zamanı ve iki reset biçimi, Claude olayının yazılması ve salt okunur özet, eşik/girdi doğrulaması, PM → lider → işçi, dış işçi, üst kimlik kaynakları, oturum ayrımı, döngü ve pencere filtresi, rapor komutu.
- Geçici `POLYCREW_OLAYLAR` ile `rapor --saat 5 --dil tr`: Claude, Codex, agy ve ağaç gömülü; gerçek günlük yazılmadı, 8770 sunucusuna dokunulmadı.
- JavaScript çizimi, Claude sırası, bağlam, eski etiket, yan panel ve TR/EN metinleri Node ile denetlendi. Başsız Chrome sandbox'ta `setsockopt: Operation not permitted` ile açılamadı; bağlı tarayıcı yok. Gerçek dar/geniş ekran görüntüsü alınamadı.

## Açık kalan

- Gerçek bir Claude PM oturumunda masaüstü kotası aktarımı ve açık üst kimliği içeren kanca yükü henüz denenmedi; yeni alanların uyumluluğu sentetik olaylarla doğrulandı.
- Kısaltılmış yenilenme tarihleri yıl ve saat dilimi bilgisi kaybeder; mevcut sözleşme ölçümün yılını ve yerel takvimi kullanır.
