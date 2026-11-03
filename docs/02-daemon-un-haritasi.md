# 02 — tclfactoryos Daemon'unun İç Haritası

> Faz: gün 2–4. Root daemon'unun elle tersine mühendisliği (stripped ARM32, radare2):
> socket protokolü, FCMD komut işlemcisi, root shell noktaları ve üç giriş kanalı.
> Binary: firmware paketinden çıkarıldı; `vaddr = dosya-offset + 0x1000` kayması önemli.

## 1. Thread tablosu (fatory_os_thread_init)

Daemon açılışında 5 thread yaratır (canlı `/proc/<pid>/task` doğrulamasıyla):

| Thread | İş |
|---|---|
| remote_thread_cb | IR olaylarını `/dev/input/*`'tan okur (venus_IR_input) |
| debug_interface → myuart | UART'ı HAL binder üzerinden okur (aygıtı kendisi açmaz) |
| socket_start | TCP 127.0.0.1:27856 fabrika socket'i |
| preset_keys | `/impdata/preset_keys.bin` izler (ölü — doküman 05) |
| user_timer | ARM penceresi zamanlayıcısı (tembel yaratılır) |

**Kritik:** `app_factory_p2p_interface` (p2p istemcisi) bu tabloda YOK. Kim yarattığı
doküman 04'te kanıtlandı: yalnız IR commit dizisi.

## 2. Fabrika socket'i (127.0.0.1:27856)

Adb forward ile erişilir. Protokol: **sabit 144 baytlık** frame:

```
offset  boyut  alan
0       4      id (i32)
4       4      fun (i32)
8       4      intAttr (i32)
12      64     strKey   (NUL-dolgulu)
76      4      intValue (i32)
80      64     strValue (NUL-dolgulu)
```

`fun` değerleri: **0** SET_PROP · **1** GET_PROP · **2** GET_ATTR · **3** SET_ATTR ·
**4** DO_FUNCTION · **6** GET_INFO · **7** EVENT (bildirim-only, giriş değil).

- fun=0/1 roundtrip canlı kanıtlı; DB'ye `memory.factory.*` **ve** `sys.System.*`
  yazılabiliyor (whitelist yok).
- fun=4 yalnız intAttr 0x84/0x86/0x8b destekler. 0x8b'de `system("<tool> > <impdata>/...")`
  biçiminde enjeksiyon noktası VAR ama yol config katmanından okunduğu için etkisiz +
  çağrılan Amazon binary'leri bu firmware'de yok (exit 32512) → ölü.
- Parser sağlam: `recvfrom` sabit 144B, `fun<=7` denetimi, SQLite parameterized.

Araç: `tools/factorysock.py` (`adb forward tcp:19999 tcp:27856` sonrası
`factorysock.py get|set|aget|aset|func|info ...`).

## 3. FCMD (app_factory_app_cmd) — root komut işlemcisi

Daemon'un iç komut işlemcisi. **Girişi tam 3 kanal** (xref haritası birebir çıkarıldı):

1. `app_factory_remote_thread_cb` (IR thread — type-0x19 fabrika olayları; doküman 04)
2. `app_factory_myuart` → `transfer_data` (UART thread — fiziksel hat)
3. `app_factory_p2p_interface` → `transfer_data` (p2p TCP — reverse connect)

İçindeki en değerli işlem: **GET_SYSTEM_PROP** — çağıranlar tam 2 yer: FCMD case'i ve
**ts_fun_read_write (p2p)**. Kod:

```c
system("getprop %s > /tmp/factory_prop_ret.txt");   // %s = 64 baytlık key!
```

**Root kanıtı payload'u** (kanal açılır açılmaz ilk atış):

```
key = "x;id>/sdcard/Download/R1.txt;id>/data/local/tmp/R2.txt;#"   // 56 bayt < 64
```

Ayrıca FCMD içinde `write_long_file` ve `0x8e328/0x8e77c/0x8e822` adreslerinde üç
`system()` noktası daha haritalandı. (Not: daemon'a `/tmp/x.sh` yazmak gerekmiyor —
key'e gömülü komut yeterli; TV'de /tmp tmpfs'e shell yazamıyor çünkü SELinux.)

## 4. p2p kanalı — reverse connect protokolü

`app_factory_p2p_interface` akışı (tamamı disasm'den):

1. `ts_init_queue` (özel malloc kuyruğu — POSIX mqueue DEĞİL, /dev/mqueue bağımsız)
2. 500 ms döngü: kendi `wlan0` IP'si `0.0.0.0` ise bekle
3. DB'den `memory.factory.RCU.IPAddr` + `p2p.sinPort` oku
4. **Dışarıya connect()** — TV istemci, karşısı sunucu
5. ts protokolü: sunucu `84 83 7B 7C` handshake yollar; veri frame'i
   `84 83 <cmd> <data> <crc16-ccitt-false>` → `ts_handle_data` → `ts_cmd` →
   `ts_fun_read_write` / `transfer_data` → FCMD

DB'ye IP/port yazmak canlı doğrulandı (socket fun=0) — ama thread doğmadan hiçbir etkisi
olmadı (canlı thread listesi kanıtı). Thread'in doğum koşulu: **yalnız IR RCU commit**
(doküman 04).

## 5. IR commit dizisi (daemon beklentisi — disasm'den bayt bayt)

`check_p2p_debug_ir_cmd(cmd, arg)`:

- **ARM:** `cmd==5` ve `arg ∈ [0x50..0x5A]` → 3000 ms `user_timer` penceresi açılır,
  tampon sıfırlanır. (0x50/0x58/0x59/0x5A farklı parse varyantları — v1..v4; 0x51–0x57
  tampon sıfırlayıcı.)
- **DIGIT:** `cmd==0xD` ve `arg` = hane değeri → 13 baytlık kaydırma yazmacına itilir.
  Her itilişten sonra `buf[0]==0x01 && buf[1]==0x0C` kontrol edilir; sağlanırsa
  `CRC16-CCITT-FALSE(buf[1..12]) == 0` şartı aranır.
- **COMMIT sağlanırsa:** baytlar `IP(4) + port(2) + random(2) + serbest(1) + crc(2)`
  olarak parse edilir (p2p_debug_ir_parse_v1), DB'ye yazılır **ve p2p thread doğar**
  (`os_thread_create`, handle==-1 koruması — bir kez doğar, ikinci kez doğmaz).
- ~15 sn **full-value dedupe** var: aynı 32-bit olay değeri 15 sn içinde tekrar
  işlenmez. Aşma yöntemi: cmd/arg dışındaki serbest bitleri frame'de değiştirmek.

CRC çözümü: verilen 11 baytlık öne `tail = coz_kuyruk(bytes 1..10)` araması —
`CRC16-CCITT-FALSE(önek+tail)==0` sağlayan 2 bayt. (rcu_hesap.py'de hazır.)

## 6. Bu fazın özeti

Root'a giden komut işlemcisi ve payload birebir hazır; geriye **tek soru**: üç kanaldan
birini açmak. UART fiziksel, p2p IR-commit'e bağımlı, IR ise kernel'e bağlı → doküman 03–04.
