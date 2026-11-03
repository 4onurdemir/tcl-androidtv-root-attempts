# 04 — Kök Fazı: Kernel Kanıtları ve İmkansızlık İspatı

> Faz: gün 8 (tek oturum). IR kanalı canlı, daemon beklentisi biliniyor, payload hazır.
> Bu doküman, zincirin neden **yazılımsal olarak** kapanmış olduğunu kanıtlarla anlatır.
> Yöntem: boot.img'den kernel Image çıkarıldı (48,7 MB ARM64), venus_ir sürücüsü elle
> disassemble edildi; tüm bulgular canlı cihazda getevent/logcat/thread-listesi ile
> çapraz doğrulandı.

## 1. Smoke test

`tools/arduino/fabrika/fabrika.ino` ile VOL+ frame'i 3 kez → TV ses seviyesi 13→16. IR kanalı ve yeni atıcı
sketch kanıtlı çalışıyor. Aynı pencerede `getevent -t /dev/input/event0` izlendi.

## 2. Kernel'in ilk gerçek yüzü: tablo-dışı kod = sessiz çöp

Denenmiş frame'ler ve sonuçları (getevent + daemon logu birlikte izlendi):

| Frame | Beklenti (eski hesap) | Gerçek |
|---|---|---|
| ARM adayı 0xA0A5F5 | check_p2p penceresi açılır | **Hiç olay yok** |
| ARM adayı 0x50AAF5 | " | **Hiç olay yok** |
| 0xF550AA (tabloda olmayan CMD) | bir şey olur | **Hiç olay yok** |
| NEC ailesi 8 bit/bayt-sırası varyantı | decode olur | **Hiç olay yok** (protokol deaktif) |
| VOL+ 0xF2F0D0 | EV_KEY 0x73 | ✓ EV_KEY 115 (KEY_VOLUMEUP), MSC_SCAN YOK |

Sonuç: sürücü, tuş tablosunda **birebir eşleşmeyen** her frame'i hiçbir input olayı
üretmeden atıyor.

## 3. w19 dönüşümü (sürücünün iç dili)

Sürücü IR akışını **LSB-ilk** biriktirir; her iletilen bayt bitrev8 ile ters çevrilip
32-bit `w19` kelimesine yerleşir:

```
w19 = bitrev8(W2)<<24 | bitrev8(W1)<<16 | bitrev8(W0)<<8
(W0 = ilk giden bayt = ADDR|CMD-yüksek-nibble)
```

Doğrulama: VOL+ frame'i 0xF2F0D0 → w19 = **0x0b0f4f00** → `ir_table.bin`'deki girdiyle
**birebir** eşleşiyor. Tuş tablosu girdileri w19 değerleridir.

## 4. ir_table.bin formatı (factory_ro bölmesinden)

- Başlık: `{u32 count=335, u32 magic}`; ardından 8 baytlık girdiler:
  `{u16 tip, u16 keycode, u32 w19}`
- Tipler = protokol aileleri: **1** = NEC müşteri 0x6699 · **0x12** = NEC 0x16b9 ·
  **8** = bu TV'nin 56 kHz RCA ailesi (158 girdi)
- Parse aracı: `tools/arduino/ir_tablo_parse.py`

## 5. Fabrika olayı: tip-0x19

Tabloda eşleşen bir kod için sürücü (özel koşullar altında) şunu yollar:

```
input_event(dev, type=0x19, code=KEYCODE, value=(code16<<16)|status)
```

- daemon `cmd = (value>>16)&0xF = code16&0xF`, **`arg = event.code&0xFF = tablodaki KEYCODE`**,
  `status = value&0xF` (1=basılı) okur — yani **hane değeri tablodan gelir, frame'den değil!**
- RCA ailesinde `code16 = bitrev4(CMD&0xF)`
- Emisyon iki kilit arkasında:
  1. **report-mode bayrağı** (kernel globali) — canlı cihazda kapalı; setleyen
     `/sys/venus_ir/*` düğümleri SELinux'suz etiketli ve **root-only**
  2. code16 özel maske kümesinde olmalı ({5,7..0xB,0xD..0xF,0xf2..})

## 6. İmkansızlık ispatı (çalışmanın ana bulgusu)

RCU dizisinin kuralları (doküman 02) + kernel gerçekleri birleşince:

1. Hane değeri = **tablo keycode & 0xFF** olmalı (kernel arg'yı keycode'dan veriyor)
2. Hane gönderebilen tek aile: code16=0xD ⇒ tablodaki 0xD ailesi, keycode düşük
   baytları tam olarak: **{b2, a3, f7, ac, 81, 58, 92, ef}**
3. Dizinin ilk iki baytı **sabit marker**: buf[0]=0x01, buf[1]=0x0C
4. 0x01 ∉ küme, 0x0C ∉ küme ⇒ **hiçbir geçerli 13-baytlık dizi kurulamaz. Nokta.**

(Üstüne ikinci bağımsız kilit: report-mode bayrağı kapalı ve root-only. İkisinden
herhangi biri bile tek başına yolu kapatırdı.)

## 7. p2p thread'inin doğum gizemi çözüldü

- Daemon açılış thread'leri p2p'yi **yaratmıyor** (canlı /proc/840/task listesi: IR,
  UART, socket, preset, user_timer — p2p yok).
- Disasm: `app_factory_p2p_interface`'i çağıran TEK yer, `check_p2p`'nin **commit dalı**
  (`os_thread_create`, handle==-1 korumasıyla bir kezlik doğum).
- `check_p2p`'yi çağıran tek yer IR thread'i.
- **Sonuç:** p2p yalnız geçerli IR commit'inden doğar. IR imkansız ⇒ p2p asla doğmaz.
  **Reboot da daemon-restart da bunu değiştirmez** (restart zaten sadece crash/reboot ile
  mümkün ve thread_init bağımlılığı yok). Bu buluş, riskli bir yeniden başlatmayı
  denemekten kurtardı — DB'ye IP/port yazılmıştı ve "reboot'ta thread kalkar" umudu
  vardı; kanıt gösterdi ki umut boştu.
- Yan bulgu: eski "ts_init_queue boot'ta çöküyor" teorisi yanlıştı — `os_mqueue_create`
  özel malloc kuyruğudur, POSIX mqueue/`/dev/mqueue` ile ilgisi yok (o dizin TV'de
  hiç yok ve fark etmiyor).

## 8. Canlı çapraz kanıtlar

- 27856 socket fun=0 ile DB'ye `RCU.IPAddr`/`sinPort`/`RandomCode` yazıldı, fun=1 ile
  geri okundu — **yazma kanalı canlı**; p2p doğmadığı için etkisiz (thread listesi kanıtı).
- Logcat tamponunun eski boot'ları taşımadığı gösterildi (daemon 75 saat önce açılmış,
  açılış logları hiçbir tamponda yoktu) — **"logda iz yok" ≠ "hiç olmadı"**; kesin kanıt
  için /proc thread listesi kullanıldı.

## 9. Tablo

| Kök yol | Durum |
|---|---|
| IR → check_p2p → commit → p2p → FCMD → root | **İmkansız** (tabloda marker yok + report-mode kilidi) |
| UART (fiziksel) → myuart → FCMD → root | Donanım açılamıyor; yazılım yolu SELinux kapalı |
| p2p'yi başka türlü doğurmak | Tek doğum yolu IR commit — kanıtlandı |
| Reboot / daemon-restart ile p2p | İşe yaramaz — kanıtlandı |
| 27856 socket'ten root | Parser sağlam; teorik NUL-taşması kanıtsız; her crash=reboot maliyeti |

**Kapanış:** yazılımsal yüzey tükendi. Kalan tek yol fiziksel UART (harici servis jakı
aranmalı; kapak açmadan erişilebilir olursa Arduino Uno RESET→GND hilesi USB-TTL köprüsüdür).
