# 07 — Tools and Usage Recipes

> Every tool written or used in the project, what it does, and how to run it.
> Paths are relative to this repository layout.

## 1. fabrika.ino — the universal IR blaster (Arduino Uno)

**Location:** `tools/arduino/fabrika/fabrika.ino` (+ firing script `fabrika_atess.py`)

Sends TCL IR frames on a 56 kHz carrier. Circuit: Uno pin 3 → 2N2222A (C–B–E!) →
940 nm IR LED. Build/flash:

```
arduino-cli compile --fqbn arduino:avr:uno <folder>
arduino-cli upload  --fqbn arduino:avr:uno -p /dev/cu.usbmodemXXXX <folder>
```

Serial commands (115200 baud):

| Command | Action |
|---|---|
| `H XXXXXX` | 24-bit RCA frame, 2× (remote-like) |
| `G XXXXXX` | 24-bit RCA frame, 1× (fast) |
| `N XXYYZZ` / `M XXXXXXXX` / `O XXXXXXXX` | NEC frame variants (c1,c2,data; ~data automatic) |
| `B W1,W2,...` / `C F1,F2,...` | bursts (RCA / NEC) |
| `P` | ping (PONG) |

Known key codes: `data/TCL-kumanda-kodlari.md` (40 keys; e.g. VOL+ = F2F0D0).

## 2. factorysock.py — client for the 27856 factory socket

**Location:** `tools/factorysock.py`

```
adb forward tcp:19999 tcp:27856
python3 factorysock.py get  <key>          # fun=1
python3 factorysock.py set  <key> <value>  # fun=0
python3 factorysock.py aget/aset ...       # attrs (fun=2/3)
python3 factorysock.py func <attrHex> [k] [v]  # fun=4
python3 factorysock.py info                # fun=6
```

Frame: 144 bytes `{id,fun,attr,strKey[64],intval,strValue[64]}`. Response ~73 bytes.
Valid while the daemon is running (P-mode).

## 3. ir_tablo_parse.py — kernel IR key-table parser

**Location:** `tools/arduino/ir_tablo_parse.py`

Parses the `ir_table.bin` extracted from a `factory_ro` partition: entries are
`{u16 type, u16 keycode, u32 w19}`; w19 is the driver's LSB-first bitrev8 accumulation.
**On another TCL model, open this table first**: if the 0xD family (the only
digit-capable one) contains 0x01/0x0C keycodes, the IR-RCU sequence can work on that
model.

## 4. rcu_hesap.py — RCU 13-byte sequence generator (LEGACY word format!)

**Location:** `tools/arduino/rcu_hesap.py` (+ firer `rcu_atess.py`)

The CRC16-CCITT-FALSE tail solver and the payload template are correct; **but its
32-bit word construction follows the old assumption, not this TV's real kernel format**
(see the w19 transform in doc 04). If reused on a new model, update `kelime()`.
The lasting values: `coz_kuyruk()` (the search for a 2-byte tail making CRC==0) and the
payload layout `buf = [0x01, 0x0C] + IP(4) + port(2) + random(2) + free(1) + tail(2)`.

## 5. Kernel image extraction and finding the driver

```
# boot.img (Android boot v3): kernel starts at offset 4096, size in the header
python3 - <<'EOF'
import struct
h = open('boot.img','rb').read(64)
ksize = struct.unpack_from('<I', h, 8)[0]
k = open('boot.img','rb').read()[4096:4096+ksize]
open('kernel.bin','wb').write(k)
EOF

# IR driver: file-offsets ~0x0c0f000–0x0c13xxx inside kernel.bin (venus_ir)
r2 -q -n -c "s 0xc0ff54; pd 80" kernel.bin   # the report_key function
```

String xrefs can be found by scanning ADRP+ADD literal references (careful with the
decoder); IR strings live around ~0x19xxxxx (rodata).

## 6. Helper pieces

| Piece | Job |
|---|---|
| `tools/p2pclient.py` | ts-protocol client skeleton (handshake `84 83 7B 7C` + CRC16-CCITT-FALSE framing) |
| listener pattern (`p2plisten.py` in the journal) | port-4000 server: accept → if the TV stays silent 2 s, send the handshake → log everything |
| `tools/arduino/rcu_atess.py` | sequence firer over the serial port |
| `data/kanit-ornekleri.md` | raw log/disassembly excerpts for the main claims |

## 7. The M-jar door recipe

The door command (while the diagnostics flag is on):

```
settings put global tcl_diagnostic_status 1
dumpsys activity service com.tcl.ttvs/com.tcl.guard.onlinesupport.service.OnlineSupportService \
  --i 3 "CLASSPATH=/system/framework/tcl-service.jar:/data/data/com.tcl.ttvs/files/M3.jar \
         app_process / M pmon > /data/data/com.tcl.ttvs/files/m3out.txt 2>&1"
```

- **The class name is `M`** (not the jar's file name!) — `M3 pmon` fails silently with
  ClassNotFoundException.
- Long jobs go to the background with `&`; output is read back with `--i 3 'cat ...'`.
- Jar build: `javac --release 8` (reflection-only; the HIDL jar is DEX and must not go
  into javac) + `d8 --min-api 30` + jar.
- pmon: starts the daemon without a reboot · pmoff: clears the boot flag (does not kill
  the running daemon).
