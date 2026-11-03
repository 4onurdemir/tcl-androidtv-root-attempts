# 07 — Araçlar ve Kullanım Tarifleri

> Projede yazılan/kullanılan her araç, ne yaptığı ve nasıl çalıştırılacağı.
> Yollar bu dokümandaki klasör yapısına göredir (repo'ya taşınırken tools/ altına).

## 1. fabrika.ino — evrensel IR atıcı (Arduino Uno)

**Yer:** `tools/arduino/fabrika/fabrika.ino` (+ atış scripti `fabrika_atess.py`)

56 kHz taşıyıcıyla TCL IR frame'leri yollar. Devre: Uno pin 3 → 2N2222A (C–B–E!) →
940 nm IR LED. Derleme/yükleme:

```
arduino-cli compile --fqbn arduino:avr:uno <klasör>
arduino-cli upload  --fqbn arduino:avr:uno -p /dev/cu.usbmodemXXXX <klasör>
```

Seri komutlar (115200 baud):

| Komut | İş |
|---|---|
| `H XXXXXX` | 24-bit RCA frame, 2 kez (kumanda davranışı) |
| `G XXXXXX` | 24-bit RCA frame, 1 kez (hızlı) |
| `N XXYYZZ` / `M XXXXXXXX` / `O XXXXXXXX` | NEC frame varyantları (c1,c2,data; ~data otomatik) |
| `B W1,W2,...` / `C F1,F2,...` | toplu seri (RCA / NEC) |
| `P` | ping (PONG) |

Bilinen tuş kodları: `data/TCL-kumanda-kodlari.md` (40 tuş; ör. VOL+ = F2F0D0).

## 2. factorysock.py — 27856 fabrika socket istemcisi

**Yer:** `tools/factorysock.py`

```
adb forward tcp:19999 tcp:27856
python3 factorysock.py get  <anahtar>          # fun=1
python3 factorysock.py set  <anahtar> <değer>  # fun=0
python3 factorysock.py aget/aset ...           # attr (fun=2/3)
python3 factorysock.py func <attrHex> [k] [v]  # fun=4
python3 factorysock.py info                    # fun=6
```

Frame: 144 bayt `{id,fun,attr,strKey[64],intval,strValue[64]}`. Yanıt ~73 bayt.
Daemon çalışırken (P-mode) geçerlidir.

## 3. ir_tablo_parse.py — kernel IR tuş tablosu çözücü

**Yer:** `tools/arduino/ir_tablo_parse.py`

`factory_ro.img` içinden çıkan `ir_table.bin`'i parse eder: girdi = `{u16 tip,
u16 keycode, u32 w19}`. w19 = sürücünün LSB-ilk bitrev8 biriktirmesi. Başka TCL
modelinde **önce bu tabloyu aç**: 0xD ailesinde (hane girebilen) 0x01/0x0C keycode
varsa IR-RCU dizisi o modelde çalışabilir.

## 4. rcu_hesap.py — RCU 13-hane dizisi üreteci (ESKİ hesap!)

**Yer:** `tools/arduino/rcu_hesap.py` (+ ateşleyici `rcu_atess.py`)

CRC16-CCITT-FALSE tail çözümü ve dizi üretimi doğru çalışır; **ama içindeki 32-bit
NEC-tarzı kelime kurulumu bu TV'nin gerçek formatına göre ESKİDİR** (doküman 04'teki
w19 dönüşümü geçerlidir). Yeni modelde kullanılacaksa `kelime()` fonksiyonu
güncellenmelidir. Kalıcı değer: `coz_kuyruk()` (CRC==0 sağlayan 2 baytlık tail araması)
ve `haneler_uret()` şablonu: `buf = [0x01, 0x0C] + IP(4) + port(2) + random(2) +
serbest(1) + tail(2)`.

## 5. Kernel image çıkarımı ve sürücü bulma

```
# boot.img (Android boot v3): kernel @ 4096'dan itibaren, boyut header'da
python3 - <<'EOF'
import struct
h = open('boot.img','rb').read(64)
ksize = struct.unpack_from('<I', h, 8)[0]
k = open('boot.img','rb').read()[4096:4096+ksize]
open('kernel.bin','wb').write(k)
EOF

# IR sürücüsü: kernel.bin içinde file-offset ~0x0c0f000–0x0c13xxx (venus_ir)
r2 -q -n -c "s 0xc0ff54; pd 80" kernel.bin   # report_key işlevi
```

ADRP+ADD literal referans taramasıyla string xref'i bulmak için çalışan tarayıcı
(ADR/ADRP kodlayıcı dikkatle): İR stringleri ~0x19xxxxx'te (rodata).

## 6. Yardımcı parçalar

| Parça | İş |
|---|---|
| `tools/p2pclient.py` | ts protokol istemci taslağı (handshake `84 83 7B 7C` + CRC16-CCITT-FALSE frame) |
| `/tmp/p2plisten.py` deseni | Port 40000 dinleyici: bağlantıyı kabul → TV 2 sn sessiz kalırsa handshake yolla → tüm trafiği logla |
| `tools/uart_fire.py`, `tools/sparse2img.py` | UART frame ateşleyici / sparse image dönüştürücü (devam edene hazır) |
| `analysis/bin/` | tclfactoryos, vendor.tcl.factory@1.0-service.elf, kernel.bin, ir_table.bin — tüm RE malzemesi |
| `DOKUMAN/baska-ai-ye-soru.md` | Bağımsız ikinci görüş için proje özeti (yapıştır-hazır) |

## 7. Yeniden kurulum tarifi (M-jar kapısı)

Kapı komutu (diagnostic flag açıkken):

```
settings put global tcl_diagnostic_status 1
dumpsys activity service com.tcl.ttvs/com.tcl.guard.onlinesupport.service.OnlineSupportService \
  --i 3 "CLASSPATH=/system/framework/tcl-service.jar:/data/data/com.tcl.ttvs/files/M3.jar \
         app_process / M pmon > /data/data/com.tcl.ttvs/files/m3out.txt 2>&1"
```

- **Sınıf adı `M`** (jar adı değil!) — `M3 pmon` yazmak sessiz ClassNotFoundException.
- Uzun işler `&` ile arka plana; çıktı sonra `--i 3 'cat ...'` ile okunur.
- Jar derleme: `javac --release 8` (reflection-only; HIDL jar'ı DEX, javac'a verilmez)
  + `d8 --min-api 30` + jar'la.
- pmon: daemon'u reboot'suz başlatır · pmoff: boot flag'ini kapatır (daemon'u öldürmez).
