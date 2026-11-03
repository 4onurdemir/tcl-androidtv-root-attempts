# 06 — Dersler

> Proje boyunca kanıtlanmış, başka cihazlara ve oturumlara taşınabilir dersler.
> Sıra: teknik dersler → metod dersleri → disiplin dersleri.

## Teknik dersler

### 1. "Protokol yanlış" sanmadan önce taşıyıcıyı ölç
Günlerce 38 kHz ile çalışıldı; zamanlama, bit düzeni, sürücü, polarite — hepsi doğruydu ve
hiçbir şey çalışmıyordu. Sebep **56 kHz taşıyıcı** idi. Kaynaklarda (Flipper IRDB, kernel
kaynağı, başka cihaz kayıtları) yazan frekans bu cihazın alıcısı için geçerli değildi.
**Ders: alıcının gerçeğini ancak vericinin kendi sinyalinden ölçersin.** Ucuz bir
kumanda-alıcı modülü (KY-022) + Arduino, pahalı analizörden önce gelsin.

### 2. Bacak sırası datasheet'te değil, cihazda
Kullanılan 2N2222A'nın bacak sırası (düz yüz bakınca C–B–E) iki kurulum PDF'inde yanlış
yazıyordu. Devre ancak transistör 180° çevrilince çalıştı. **Ders: transistörü
multimetrenin hFE yuvasıyla doğrula; PDF'e güvenme.**

### 3. Kernelde "olayı yok" ≠ "olayı işlenmiyor"
Daemon'un loglarında iz görememek, olayın üretilmediği anlamına gelmez — logcat tamponu
eski olayları taşımaz (75 saat önceki daemon açılışının logları hiçbir tampona
sığmıyordu). Kesin kanıt: `/proc/<pid>/task/*/comm` thread listesi, `getevent -t` canlı
izleme. **"Log yok" diyebilmek için izleme aracının olayı KAPSADIĞINI önce kanıtla.**

### 4. PIE binary'lerde adres sütunları
r2 sembol listesinde iki sütun var (paddr/vaddr); bu binary'de `vaddr = dosya-offset +
0x1000`. Ham python taramalarında (BL çözümü, literal havuzları) yanlış sütunla çalışınca
sonuç sessizce boş çıkar — hata mesajı yoktur. **Ders: tarama sonuçlarının boşluğunu
önce bilinen-bir-çağrıyla doğrula** (örn. bilinen bir `bl`'yi çözerek kodlayıcıyı test et).
Thumb BL ikinci yarım kelimesi: `(w2 & 0xd000) == 0xd000`.

### 5. Property katmanları ayrımı (TCL mimarisi)
Fabrika değerleri iki katmanda: DB (SQLite, socket'ten serbest yazılır) ve config
(json_sys.ini, RO mount, daemon okur). **DB'ye yazmak çoğu yolu değiştirmez.** Bu ayrım
anlaşılmadan "whitelist yok = her şeyi değiştiririm" sanılır.

### 6. Bağımlılık zincirini kanıtla, varsayma
"Reboot'ta p2p thread kalkar" makul bir varsayımdı — ve yanlıştı. Thread'i yalnız IR
commit'i doğuruyordu; reboot hiçbir şey değiştirmezdi. **Ders: riskli bir eylemi
(reboot) gerekçelendiren zincirin HER halkasını disasm + canlı gözlemle bağla.**
Aynı ders tersinden: pmode=1 iken fiş çekilirse fabrika ekranı gelir korkusu da
sorgulandı — bu cihazda soğuk açılış flag'i temizledi.

### 7. İmkansızlık da sonuçtur
"Root alamadık" ile "yazılımsal root bu firmware'de kurulamaz (kanıt: marker baytları
tablo keycode uzayında yok)" arasında fark var. İkincisi, başka modellerde aynı zinciri
deneyecek kişiye doğrudan yol gösterir: **önce tuş tablosunu aç, 0xD ailesinde 0x01/0x0C
var mı bak.**

## Metod dersleri

### 8. Statik RE, dinamik denemeden önce
Firmware paketi indirilmeden hiçbir riskli dinamik deneme yapılmadı. Daemon'un tamamı,
kernel sürücüsü dahil, kâğıtta çözüldü; canlı cihazda yalnızca doğrulamalar yapıldı.
Bu, cihazı hiç yeniden başlatmadan (aile TV'si!) 8 gün çalışmayı mümkün kıldı.

### 9. Kanıt zinciri standardı
Her "çalıştı/ölü" iddiasının ölçütü baştan tanımlandı: IR'da "ışık çıktı" değil,
**TV'de gözlenen etki + getevent/log kaydı**. Bu standart bir yanlış-pozitifi
(0x92 olayı) yakalayıp geri aldırdı — kaynak kendi kumandamızın basışlarıydı.

### 10. İşi bölmek: ölçüm ayrı, analiz ayrı
IR donanım ölçümleri ayrı bir oturumda (başka araçla) yapıldı; kök katmanı analizi ve
atışlar bu tarafta kaldı. Her taraf kendi bağlamını korudu, bilgi sızıntısı olmadan
devir prompt'larıyla çalıştı.

### 11. Ölü yolları belgeleyerek öldür
Her kapanan yol envantere yazıldı (doküman 05). Aynı yolu üçüncü kez deneme isteği
her zaman bu envanterle reddedildi. Hafızası olmayan proje, aynı taşı iki kez kaldırır.

## Disiplin dersleri

### 12. Reboot kuralı bir kazadan doğdu
P-mode açıkken atılan bir reboot TV'yi fabrika piksel-test ekranına kilitledi (kumanda
işlemez, Wi-Fi ölü; ~40 dk müdahale ile kurtarıldı). Kural bundan sonra değişmez oldu:
**kalıcı flag / reboot yalnız sahibi onayıyla.** Kazadan doğan kurallar anekdot değil,
proje anayasasıdır.

### 13. Temizlik, projenin parçasıdır
Kapanışta: DB değerleri boşaltıldı, harness jar'ları silindi, diagnostic kapısı kapatıldı,
Bluetooth (aile kumandası BT kullanıyor) geri açıldı, analiz makinesindeki tüm dinleyiciler
öldürüldü. **Cihaz, bulunduğundan daha temiz bırakıldı — çünkü "geri alınabilir" baştan
ilkeydi, son anda değil.**

### 14. Uzun projelerde devir dosyası = hayatta kalma
STATE.md her oturumda güncellendi; yeni oturum dosyayı okuyup kaldığı yerden sürdü.
60 KB'lık arşiv + güncel özet + kalıcı bellek üçlüsü, bağlam kaybını sıfıra indirdi.
