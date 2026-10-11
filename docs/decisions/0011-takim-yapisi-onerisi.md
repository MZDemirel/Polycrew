# 0011: Takım yapısı önerisi

- **Tarih:** 2026-10-11
- **Durum:** Kabul edildi; `0008`'in 6. kararını (yapı kendiliğinden değişmez) uygular.

## Bağlam

Kullanıcı puan ortalamalarına göre takım mimarisinin de değişmesini istedi. İşçi seçimi zaten puana göre değişiyor (`suggest`, `summary`). Yapının (bir rolde Claude mu dış işçi mi, lider var mı) az veriyle kendiliğinden değişmesi tek kötü koşudan yanlış ders çıkarır; öneri olarak sunulur.

## Kararlar

1. `roster.py structure` hiçbir şeyi değiştirmez, yalnız yazar. `/team` plan modunda çalıştırır ve geçerli satırları plana "yapı önerisi" olarak koyar; yapıyı kullanıcı onaylar.
2. Rol başına en iyi Claude işçisi ile en iyi dış işçi karşılaştırılır (solmuş puan, etkin n; önce etkin n ≥ 3 olanlardan):
   - iki tarafta da etkin n ≥ 3 ve fark > 0,25 → `prefer Claude` / `prefer external`;
   - fark ≤ 0,25 → `equal: external first, keep Claude quota` (takımın var olan kuralı: Claude kotası PM'e saklanır);
   - tek tarafta yeterli veri → `only ... measured`; hiçbirinde yok → `not enough data`.
3. `Avoid`: bir rolde etkin n ≥ 2 ve düzeltilmiş puanı < 3,0 olan işçi. Puan solduğu için kalıcı değildir.
4. Takım düzeyi olay günlüğünden: son 30 günde iş sayısı, aynı anda çalışan en çok işçi, başlatılan lider sayısı. Lider hiç başlatılmadıysa "küçük takım kullanılıyor, bu ölçekte lider gerekmiyor".
5. Eşikler `roster.py`'nin başında (`YAPI_FARK`, `KACIN_PUAN`, `KACIN_N`).

## Ölçümler (gerçek defter ve günlük, salt okunur)

| Rol | En iyi Claude (etkin n) | En iyi dış işçi (etkin n) | Öneri |
|---|---|---|---|
| developer | sonnet-5-5 4,33 (10,2) | codex sol 4,03 (21,2) | prefer Claude |
| reviewer | sonnet-5-5 4,52 (4,3) | codex sol 4,69 (7,7) | equal: external first |
| artist | opus-5-5 4,57 (6,8) | — | only Claude measured |
| image-reading | sonnet-5-5 3,93 (0,8) | codex sol 4,30 (3,7) | only external measured |
| designer, researcher, image-generation | | | not enough data |

Günlük: son 30 günde 71 iş, en çok 5'i aynı anda, lider 0. Kaçınılacak işçi çıkmadı (kötü puanlı işçilerin etkin verisi 2'nin altında).

## Testler

72 test yeşil (71 + 1): beş öneri durumu, `Avoid`, iş ve eşzamanlılık sayımı, liderin eski adla da sayılması, kurulu olmayan araçla yalnız Claude tarafı.

## Açık kalan

- `developer` için "prefer Claude", takımın "Claude kotası Z koduna saklanır" kuralıyla çelişiyor gibi görünebilir: öneri kaliteyi söyler, kota kararı PM'de. Zorluğa göre ayrım (`--difficulty`) eklenmedi; veri rol + zorlukta çok ince.
- Lider ve tasarımcı ölçülmedi; öneri bu rollerde veri birikene kadar boş.
