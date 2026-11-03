# 02 — The Internal Map of the tclfactoryos Daemon

> Phase: days 2–4. Hand-reversing the root daemon (stripped ARM32, radare2):
> the socket protocol, the FCMD command processor, the root shell points, and the
> three entry channels. The binary came from the firmware package; note the
> `vaddr = file-offset + 0x1000` displacement.

## 1. Thread table (fatory_os_thread_init)

The daemon spawns 5 threads at startup (verified against the live `/proc/<pid>/task` list):

| Thread | Job |
|---|---|
| remote_thread_cb | Reads IR events from `/dev/input/*` (venus_IR_input) |
| debug_interface → myuart | Reads the UART through a HAL binder call (never opens the device itself) |
| socket_start | The TCP 127.0.0.1:27856 factory socket |
| preset_keys | Watches `/impdata/preset_keys.bin` (dead — doc 05) |
| user_timer | The ARM-window timer (created lazily) |

**Critical:** `app_factory_p2p_interface` (the p2p client) is **not** in this table.
Who creates it — and when — was proven in doc 04: only the IR commit sequence.

## 2. The factory socket (127.0.0.1:27856)

Reachable via adb forward. Protocol: a **fixed 144-byte** frame:

```
offset  size   field
0       4      id (i32)
4       4      fun (i32)
8       4      intAttr (i32)
12      64     strKey   (NUL-padded)
76      4      intValue (i32)
80      64     strValue (NUL-padded)
```

`fun` values: **0** SET_PROP · **1** GET_PROP · **2** GET_ATTR · **3** SET_ATTR ·
**4** DO_FUNCTION · **6** GET_INFO · **7** EVENT (outbound notify only, not an entry).

- fun=0/1 round-trips proven live; the DB accepts `memory.factory.*` **and**
  `sys.System.*` writes (no whitelist).
- fun=4 supports only intAttr 0x84/0x86/0x8b. The 0x8b path contains a `system("<tool> > <impdata>/...")`
  injection point — but its path is read from the config layer (ineffective) and the
  Amazon binaries it calls don't exist in this firmware (exit 32512) → dead.
- The parser is hardened: `recvfrom` fixed 144B, `fun<=7` check, SQLite parameterized.

Tool: `tools/factorysock.py` (after `adb forward tcp:19999 tcp:27856`, run
`factorysock.py get|set|aget|aset|func|info ...`).

## 3. FCMD (app_factory_app_cmd) — the root command processor

The daemon's internal command processor. **Entry from exactly 3 channels**
(the xref map was extracted link by link):

1. `app_factory_remote_thread_cb` (the IR thread — type-0x19 factory events; doc 04)
2. `app_factory_myuart` → `transfer_data` (the UART thread — the physical line)
3. `app_factory_p2p_interface` → `transfer_data` (p2p TCP — reverse connect)

Its most valuable operation: **GET_SYSTEM_PROP** — called from exactly 2 places: an FCMD
case and **ts_fun_read_write (p2p)**. The code:

```c
system("getprop %s > /tmp/factory_prop_ret.txt");   // %s = a 64-byte key!
```

**The root-proof payload** (the first shot, the moment a channel opens):

```
key = "x;id>/sdcard/Download/R1.txt;id>/data/local/tmp/R2.txt;#"   // 56 bytes < 64
```

FCMD also contains `write_long_file` and three more `system()` points at
`0x8e328/0x8e77c/0x8e822`, fully mapped. (Note: no /tmp/x.sh is needed — the command
embedded in the key is enough; TV /tmp is tmpfs and unwritable by shell due to SELinux.)

## 4. The p2p channel — the reverse-connect protocol

The `app_factory_p2p_interface` flow (entirely from disassembly):

1. `ts_init_queue` (a custom malloc queue — not POSIX mqueue; independent of /dev/mqueue)
2. 500 ms loop: wait while the device's own `wlan0` IP is `0.0.0.0`
3. Read `memory.factory.RCU.IPAddr` + `p2p.sinPort` from the DB
4. **connect() outward** — the TV is the client, your machine is the server
5. ts protocol: the server sends the `84 83 7B 7C` handshake; data frames are
   `84 83 <cmd> <data> <crc16-ccitt-false>` → `ts_handle_data` → `ts_cmd` →
   `ts_fun_read_write` / `transfer_data` → FCMD

Writing IP/port into the DB was verified live (socket fun=0) — but had no effect as long
as the thread wasn't born (live thread-list proof). The birth condition: **only a valid
IR RCU commit** (doc 04).

## 5. The IR commit sequence (the daemon's expectations — from disassembly, byte by byte)

`check_p2p_debug_ir_cmd(cmd, arg)`:

- **ARM:** `cmd==5` and `arg ∈ [0x50..0x5A]` → a 3000 ms `user_timer` window opens and
  the buffer resets. (0x50/0x58/0x59/0x5A select different parse variants — v1..v4;
  0x51–0x57 are buffer resets.)
- **DIGIT:** `cmd==0xD` and `arg` = the digit value → pushed into a 13-byte shift
  register. After each push, `buf[0]==0x01 && buf[1]==0x0C` is checked; when satisfied,
  the condition `CRC16-CCITT-FALSE(buf[1..12]) == 0` is evaluated.
- **On COMMIT:** the bytes parse as `IP(4) + port(2) + random(2) + free(1) + crc(2)`
  (p2p_debug_ir_parse_v1), get written to the DB **and the p2p thread is born**
  (`os_thread_create`, guarded by handle==-1 — born once, never twice).
- A ~15 s **full-value dedupe** exists: the same 32-bit event value is not processed
  again within 15 seconds. Bypass: vary the free bits outside cmd/arg from frame to frame.

CRC solution: for a given 11-byte prefix, search `tail` such that
`CRC16-CCITT-FALSE(prefix+tail)==0` — 2 bytes. (Ready in rcu_hesap.py.)

## 6. Phase summary

The root command processor and the payload are ready to the byte; the **single remaining
question** is opening one of the three channels. UART is physical, p2p depends on the IR
commit, and IR depends on the kernel → docs 03–04.
