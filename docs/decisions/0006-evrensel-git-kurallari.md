# 0006: Evrensel git kuralları tek dosyada, soru değil sabit

- **Tarih:** 2026-10-11
- **Durum:** Kabul edildi.

## Bağlam

Dört git kuralı kullanıcının bütün projelerinde geçerli ama eklenti onları güvenilir taşımıyordu. Masalino'da (2026-10-11):

- `proje-kur` commit biçimini soruyordu ve varsayılanı "tek satır, önek yok, imza yok"tu. Projenin kendi biçimi (`feat(...): ...`) seçenek olunca "imza yok" sorudan düştü; oturumun bütün commit'leri `Co-Authored-By` ile `main`'e girdi.
- `takim` 4. adım birleşen dalı siliyordu; kullanıcı geçmiş için dalların kalmasını istiyor.
- `oturum-kapat`, `gelistirici` ve `dis-ajan` yalnız "projenin commit kuralıyla" diyordu; projede eksik olan kural onlarda da eksik kalıyordu.
- Dış işçiler (Codex, agy) Claude'un hafızasını okumaz; kural onlara yalnız `dis-ajan.sh`'nin `kural=` satırıyla ulaşır.

## Kararlar

1. Sabit kurallar eklentide tek dosyada: `kurallar/git.md`. İmza yok (merge dahil), PR'da araç satırı yok, birleşen dal silinmez (yerel ve uzak; çalışma ağacı kaldırılır, dal kalır), işçi push etmez ve kancayı atlatmaz. Klasör eklenti kökünde, çünkü kural tek bir skill'e ait değil ve rollerin (`agents/`) skill klasörü yok.
2. Skill'ler ve roller metni kopyalamaz; `${CLAUDE_PLUGIN_ROOT}/kurallar/git.md` diye işaret eder (`proje-kur`, `takim`, `oturum-kapat`, `dis-ajan`, `gelistirici`). Göreli yol bırakıldı: rollerin taban klasörü yok.
3. `proje-kur` sabit kuralları sormaz. Commit sorusu yalnız projeye göre değişeni sorar (önek ve biçim, kim atar, dal, push ve PR). Kural dosyasındaki blok her yeni `CLAUDE.md`'nin `Git` bölümüne aynen yazılır; var olan dosyaya dokunulmaz, eksik satır önerilir. Böylece eklentiyi kullanmayan oturum ve ekip arkadaşı da görür.
4. Harness'in "commit'i `Co-Authored-By` ile bitir" hatırlatması: geçersiz kılındığı hem kural dosyasında hem proje bloğunda tek cümleyle yazar. Hatırlatma önceliği kullanıcının `CLAUDE.md`'sine kendisi verdiği için bağlayıcı olan proje bloğudur.
5. `takim` 4. adım: `git worktree remove`, dal kalır.
6. `dis-ajan.sh`'nin `kural=` satırı kural dosyasının bilinen tek kopyasıdır (imza yasağı ve "dal silme" eklendi). `tests/test_kurallar.py` atıfları, kopyayı, dal silen komutun yokluğunu ve `proje-kur` sorusunda imzanın geçmediğini denetler.
7. Kullanıcı düzeyindeki `~/.claude/CLAUDE.md`'yi eklenti kendiliğinden yazmaz; `proje-kur` yoksa ya da eksikse bir kez, metni göstererek önerir.
8. Sürüm 0.4.1.

## Deneme

- Boş bir geçici dizinde (`git init`), commit sorusuna "`feat(alan): özet`, İngilizce; commit Claude, push ve PR kullanıcı" cevabıyla `CLAUDE.md` üretildi. `Git` bölümünde projenin iki satırından sonra beş sabit satır (imza, PR, geçersiz kılma, dal, işçi) sorulmadan yer aldı; Masalino'daki düşme yinelenmedi.
- Sınırı: deneme bu oturumda, kaynak depodaki skill metni izlenerek ve blok kural dosyasından alınarak yapıldı; kurulu eklentiyle açılmış ayrı bir oturumda `/proje-kur` çalıştırılmadı.
- 44 birim testi yeşil (38 + 6), `claude plugin validate .` ve `bash -n` temiz.
- Bu oturumun commit'i harness hatırlatmasına rağmen imzasız atıldı.

## Açık kalan

- Gerçek bir projede, kurulu 0.4.1 ile `/proje-kur` (yeni proje ve var olan `CLAUDE.md` durumu; kullanıcı düzeyi önerisi).
- `${CLAUDE_PLUGIN_ROOT}`'un rol gövdesinde (`gelistirici`) yola çözülüp çözülmediği gerçek bir takım koşusunda doğrulanmadı. Çözülmezse yedek, projenin `CLAUDE.md`'sindeki blok.
- Var olan projelerin (Pixlender, Masalino) `CLAUDE.md`'sinde blok eksik olabilir; `proje-kur` ya da elle eklenir.
