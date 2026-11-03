# 03 — IR Savaşı: 38 kHz Ölümlerinden 56 kHz Kırılışına

> Faz: gün 3–7. Projenin en uzun cephesi. Kaç kez "ölü" denip geri döndüğü bir kanalın
> hikâyesi — ve derslerin en değerlisi: **başarısızlığın sebebi yanlış taşıyıcı frekansıydı,
> protokol değil.**

## 1. Neden IR?

Root işlemcisine (doküman 02) üç kanaldan girişten IR, fiziksel müdahale gerektirmeyen
tek yoldu. Fabrika kumandası dizisi (ARM + 13 hane) IR ile gönderilebilirse p2p thread'i
doğuyor ve TV **kendisi** analiz makinesine bağlanıyordu.

## 2. Ölümler defteri (sırayla, hepsi belgelendi)

1. **Telefon IR (Redmi blaster):** ConsumerIrManager ile HAL seviyesinde transmit
   kanıtlandı; TV'de tek decode yok. (Nedeni sonra anlaşıldı: 38 kHz gönderiyorduk.)
2. **Arduino v1–v12 (kendi Timer2 CTC taşıyıcısı):** VOL+ kodu 7+ kez SENT-OK —
   TV loglarında tek satır yok. BC557 PNP sürücü, invert mantığı,Idle-high... hepsi doğru
   yapıldı, sonuç aynı.
3. **LED ışığı sorgusu:** telefon kamerasıyla parıltı görüldü → donanım ışık ÜRETİYOR,
   sorun sinyalde.
4. **Fotodiyot kaydı (v9/v9B):** 106 kayıt — hepsi 50 Hz şebeke flicker'ı çıktı.
   Fotovoltaik LED ölçümü ortam ışığına boğuluyor; bu yöntem öldü.
5. **Flipper-IRDB TCL kayıtları:** zamanlamamızı doğruladı (header 4000+4000µs,
   500µs bit, 1000/2000µs boşluk) ama taşıyıcı 38 kHz yazıyordu → bizi yanlış frekansta
   ısrar ettirdi.
6. **Kernel kaynağı (TCLOpenSource rt2875p):** protokolün RCA olduğunu, fabrika
   adres setini, bit dönüşümlerini verdi — ve yine 38 kHz varsayımı.

## 3. Kırılış: KY-022 alıcıyla ölçüm

Hazır kumanda-alıcı modülü (KY-022) Arduino'ya bağlandı ve **kumandanın kendi
gönderdikleri ölçüldü** — tahmin değil, ölçüm:

- **Taşıyıcı: 56 kHz.** (KY-022'nin 38 kHz bandı dışıydı; yakından okuyordu ama TV
  tam çözüyordu. Bütün 38 kHz denemelerinin ölüm sebebi buydu — protokol doğru,
  frekans yanlış.)
- Başlık: **4000 µs ışık + 4000 µs boşluk**
- 24 bit, **MSB-ilk**: `ADDR(4) | CMD(8) | ~ADDR(4) | ~CMD(8)` — TV hata kontrolünü
  ters 12 bit üzerinden yapıyor
- Bit: **500 µs ışık** + boşluk **2000 µs = '1'**, **1000 µs = '0'**; sonda 500 µs kapanış
- Kumanda her basışta frame'i **2 kez** yolluyor
- Bu TV'nin kumandası her tuşta **ADDR = 0xF**

## 4. 40 tuşun tam tablosu

Güç, ses, kanal, yön, renk, YouTube/Netflix/Disney+/Prime ve dahası — 40 tuşun hepsi
kayıt edildi, ADDR+CMD+ters+kontrol sütunlarıyla doğrulandı (kaynak hali
`data/TCL-kumanda-kodlari.md`'de). İçlerinden üçü TV'de kendi devremizle test edildi:
**VOL+, VOL−, Mute — çalıştı.** Artık TV'yi kumandasız kontrol edebilen kendi
donanımımız vardı.

## 5. Verici donanımı ve errata

- Devre: Arduino Uno pin 3 → 2N2222A sürücü → 940 nm IR LED.
- **Errata:** eldeki 2N2222A'nın bacak sırası, düz yüz sana bakarken **C–B–E**.
  Kullanılan kurulum PDF'lerinde **E–B–C** yazıyordu — devre ancak transistör 180°
  çevrilince çalıştı. Başka 2N2222A'da multimetrenin hFE yuvasıyla kontrol önerilir.
- Yazılım: `tools/arduino/fabrika/fabrika.ino` — seri komutlarla her frame'i 56 kHz'te yollayan evrensel atıcı:
  `H/G <24-bit hex>` (RCA frame 2×/1×), `N/M/O` (NEC varyantları), `B/C` (toplu seri),
  `P` (ping). Ateşleme scripti: `fabrika_atess.py`.

## 6. Bu fazdan kalan iki hatırlatma

1. **Ölçmeden inanma:** ne Flipper veritabanı ne kernel kaynağı ne de başka cihazın
   kaydı bu TV'nin alıcısının gerçeği yerine geçmiyor. Tek gerçek kaynak, kumandanın
   kendi sinyalinin ta kendisi.
2. Kanal "çözüldü" ilanunun ölçütü hiçbir zaman "ışık çıktı" olmadı — **TV'de gözlenen
   etki + getevent/log kaydı** ikilisi şarttı. (Daha önce 0x92 yanlış-pozitifi bu yüzden
   geri alındı: kaynağı kendi kumandamızın basışlarıydı.)

IR katmanı çözülmüştü. Sırada asıl soru vardı: fabrika dizisini bu kanaldan
gönderebilir miydik? → doküman 04 (cevap: hayır — kanıtlı).
