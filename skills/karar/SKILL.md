---
name: karar
description: Önemli bir kararı docs/decisions/ altına numaralı kısa bir not olarak yaz. Bir mimari, biçim, sözleşme ya da davranış seçimi yapıldığında, kullanıcı "bunu karar olarak yaz" dediğinde ya da bir seçenek bırakılıp diğeri alındığında kullan.
---

# Karar notu

1. Sonraki numara: `ls docs/decisions/ | grep -E '^[0-9]{4}-' | sort | tail -1` + 1, dört haneli.
2. Dosya adı: `NNNN-kisa-turkce-ad.md` (ASCII, tire). Resimler `docs/decisions/img/NNNN-*.png`.
3. Şablon (projenin dili; Pixlender'da Türkçe):

```markdown
# NNNN: Başlık

- **Tarih:** YYYY-AA-GG
- **Durum:** Kabul edildi | İnceleme | Değiştirildi (→ NNNN). Hangi kararı tamamlıyor ya da değiştiriyor.

## Bağlam

Neden gerekti: kullanıcının sözü, hata, ölçüm.

## Kararlar

Numaralı; her biri ne ve neden. Sabitlerin değerleri ve birimleri.

### Denenip bırakılan

Ne denendi, neden olmadı (ölçüyle).

## Ölçümler

Önce/sonra tablo; resim.

## Testler

Hangi testler neyi güvenceye alıyor.

## Açık kalan

Bilinen eksikler; sonraki aşamaya bağlantı.
```

4. Kısa tut: kararı yeniden okuyan biri "neden böyle" sorusunun cevabını bulsun. Kodu kopyalama; dosya ve fonksiyon adını ver.
5. İlgili `PLAN.md` maddesine ve `SONRAKI_OTURUM.md`'ye numarayı ekle.
