# Kanıt Örnekleri — ana iddiaların ham çıktıları

> Buradaki kesitler çalışma sırasında alınmıştır; cihaz/kullanıcı bilgisi içermez.
> Karşılık geldikleri bölümler parantez içinde.

## 1. IR kanalının çalıştığı kanıt — VOL+ ×3 (docs/03, docs/04)

Kendi IR verici devremizden (Arduino + 2N2222A + 940nm LED, 56 kHz) VOL+ frame'i
(`0xF2F0D0`) 3 kez gönderildi; TV ses seviyesi 13 → 16:

```
=== ONCE ===   streamVolume: 13 ... (4. satır)
SENT-OK F2F0D0 ×3
=== SONRA ===  streamVolume: 16 ... (4. satır)
```

Kernel tarafı (getevent -t, aynı pencerede):

```
[19657.107395] 0001 0073 00000001    ← EV_KEY KEY_VOLUMEUP down
[19657.107395] 0000 0000 00000000    ← SYN
[19657.262679] 0001 0073 00000000    ← up
[19657.262679] 0000 0000 00000000
```

## 2. Kernelin tablo-dışı kodu attığının kanıtı (docs/04 §2)

ARM adayları ve tabloda olmayan kodlar aynı izleme altında yollandı — getevent VE
daemon loglarında tek satır bile olay yok:

```
ATIS: ARM-A A0A5F5 → (getevent: boş)   ATIS: ARM-B 50AAF5 → (boş)
ATIS: 0xF550AA      → (boş)            NEC 8 varyant    → (boş)
```

## 3. w19 dönüşümünün birebir doğrulanması (docs/04 §3)

VOL+ frame'i `0xF2F0D0` → sürücünün LSB-ilk bitrev8 biriktirmesi:
`bitrev8(F2)=4F, bitrev8(F0)=0F, bitrev8(D0)=0B` → **w19 = 0x0B0F4F00**.
`ir_table.bin` girdisi (parse çıktısı):

```
14 t=0008 kc=0073 raw=0b0f4f00 [004f0f0b] VOL+      ← keycode 0x73 = KEY_VOLUMEUP ✓
```

## 4. Daemon thread listesi — p2p yok (docs/04 §7)

Daemon (root) çalışırken `/proc/<pid>/task/*/comm`:

```
840: tclfactoryos        867: user_timer
868: tclfactoryos        869: tclfactoryos      ← IR + UART
870: socket thread       871: preset keys thr
(7. thread yok: p2p_interface — açılışta yaratılmıyor)
```

## 5. p2p thread'inin nerede doğduğunun disasm kanıtı (docs/04 §7)

`check_p2p` commit dalı — daemon binary'sinden (thumb):

```
0x93ee8  ldr  r4, [pc-rel]        ; &p2p_thread_handle
0x93eec  ldr  r0, [r4]
0x93eee  adds r0, #1
0x93ef0  bne  skip                ; handle != -1 → zaten doğmuş, geç
0x93ef2  ldr  r0, [pc-rel]        ; 0x846BD = app_factory_p2p_interface|thumb
0x93f02  bl   os_thread_create    ; ← p2p YALNIZ burada doğar
0x93f06  str  r0, [r4]
```

ve `check_p2p`'yi çağıran tek yer IR thread'i (`bl @ 0x95870`, remote_thread_cb içi).

## 6. İmkansızlık ispatının verisi (docs/04 §6)

Tablodaki cmd=0xD ailesi (hane gönderebilen tek aile) — keycode düşük baytları:

```
{ b2, a3, f7, ac, 81, 58, 92, ef }
```

Daemon dizisi ise sabit `buf[0]=0x01`, `buf[1]=0x0C` marker'ları ister
(disasm: `ldrb r0,[r6]; cmp r0,#1` + `ldrb r0,[r6,1]; cmp r0,#0xC`).
`0x01 ∉ küme`, `0x0C ∉ küme` ⇒ geçerli dizi kurulamaz.

## 7. Fabrika socket roundtrip (docs/02 §2)

fun=0 SET + fun=1 GET (değerler temizlik aşamasında boşaltıldı):

```
>> set memory.factory.RCU.IPAddr 192.168.1.x     → << ack
>> get memory.factory.RCU.IPAddr                 → << 'val': '192.168.1.x'   ✓
(temizlikte: set "" → get → ascii tamamen noktalar = boş)                    ✓
```

## 8. P-mode kapama + temizlik (docs/06 ders 13)

```
setPMode(false)=true / MODE-DONE:pmoff     ← HAL üzerinden, reboot yok
odm.tcl.factory.pmode → (boş)              ← init trigger property temiz
tcl_diagnostic_status → 0 ; bluetooth_on → 1
ttvs files/ → yalnız app'in kendi dizini   ← M*.jar + tüm çıktılar silindi
```
