# 0001: Takım denemesi: iç içe agent, mesajlaşma, worktree

- **Tarih:** 2026-10-01
- **Durum:** Kabul edildi. Takım düzeni (`skills/takim`) bu sonuçlara göre kuruldu.

## Bağlam

Kullanıcının tarifi: ana oturum proje yöneticisi (PM); takım liderleri PM ile konuşur; aynı taban üzerinde çalışanlar birbirine doğrudan yazabilir. Önce bunun Claude Code'da (2.1.273) yapılabildiği denendi. Deneme Pixlender oturumunda, iki arka plan agent'ıyla yapıldı.

## Bulgular

1. **İç içe agent: var.** `general-purpose` bir alt agent'ın `Agent` aracı var; başlattığı "torun" da çalıştı ve onun da `Agent` aracı vardı. Torunun raporu ebeveynine "SubagentHandback" mesajı olarak geldi.
2. **Mesajlaşma: var, adresle.**
   - Agent → PM: `SendMessage(to: "main")` çalıştı; PM'e "Another Claude session sent a message" olarak geldi.
   - PM → agent: `SendMessage(to: <agentId>)` çalıştı; alıcıya bir sonraki araç turunda "The coordinator sent a message" olarak geldi. Çalışan bir komutun ortasında değil, araç turlarının arasında teslim edilir.
   - **`ListAgents` alt agent'larda her zaman yok** (birinci seviyede yoktu, torunda vardı). Kardeşin adresi agentId'dir; onu başlatan (PM ya da lider) verir.
3. **Worktree (`isolation: "worktree"`):**
   - Yer `<depo>/.claude/worktrees/agent-<id>`, dal `worktree-agent-<id>`, ana dalın başından.
   - Agent'ın commit'i ana depoda dal olarak görünür; değişiklik varsa worktree silinmez, PM birleştirip `git worktree remove` + `git branch -D` ile temizler.
   - **Git dışı dosyalar yok** (Pixlender'da `assets/ual`, `out/`): kısayolla bağlanmalı.
   - İlk `uv run` worktree'ye kendi `.venv`'ini kurar (yaklaşık 26 paket, saniyeler). Paket worktree'den yüklenir.
   - Commit kancası (`core.hooksPath` mutlak yol) worktree'de de çalışır.
4. **`claude plugin init`** eklentiyi `~/.claude/skills/<ad>/` altına kurar ve yeni skill çalışan alt agent'lara canlı yansır. Bu eklenti bunu kullanmaz; yerel marketplace ile kurulur.

## Kararlar

1. **Üç katman:** PM (ana oturum) → akış lideri (arka plan agent'ı) → işçiler (geliştirici, sanatçı, gözden geçirici). Liderin kendisi kod yazmaz; akışı böler, işçileri başlatır, sonuçlarını birleştirip PM'e özetler.
2. **Adresler:** PM her lidere başlatırken diğer liderlerin agentId'sini ve "PM'e `to: "main"`" bilgisini verir. Lider kendi işçilerinin agentId'lerini başlatırken öğrenir. Akışlar arası yazışma liderler üzerinden.
3. **Sorular:** lider kullanıcıya soramaz; soruyu PM'e yazar ve beklemeden devam edebileceği işe geçer. PM soruları toplayıp kullanıcıya toplu sorar.
4. **Dal:** geliştirici worktree'de kendi dalında commit atar. `main`'e yalnız PM birleştirir (`rebase main` + `merge --ff-only`), sonra worktree'yi ve dalı temizler.
5. **Sınır:** aynı anda en çok 2–3 geliştirici; tam test takımı yalnız PM'de ve sırayla.

## Açık kalan

- Eklentinin `agents/*.md` rollerinin kurulumdan sonra aynı oturumda `subagent_type` olarak çağrılıp çağrılamadığı kurulumda denenecek; çağrılamazsa rol tanımı `general-purpose` agent'ın promptuna konur.
- Liderin işçisinin izin istemleri (Bash, Edit) kullanıcıya nasıl düşüyor: ilk gerçek denemede (Pixlender Aşama 6.6) gözlenecek.
