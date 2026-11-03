# 04 — Root Phase: Kernel Proofs and the Impossibility Proof

> Phase: day 8 (a single session). The IR channel is live, the daemon's expectations are
> known, the payload is ready. This document explains — with evidence — why the chain is
> **permanently closed in software**. Method: the kernel Image was extracted from
> boot.img (48.7 MB ARM64), the venus_ir driver hand-disassembled, and every finding
> cross-verified on the live TV with getevent/logcat/thread listings.

## 1. Smoke test

`fabrika.ino` sent the VOL+ frame 3 times → TV volume 13→16. The IR channel and the new
blaster sketch are proven working. `getevent -t /dev/input/event0` watched the same window.

## 2. The kernel's first truth: off-table code = silent garbage

Frames tested (getevent + daemon logs watched together):

| Frame | Expectation (old math) | Reality |
|---|---|---|
| ARM candidate 0xA0A5F5 | check_p2p window opens | **No event at all** |
| ARM candidate 0x50AAF5 | " | **No event at all** |
| 0xF550AA (a CMD not in the table) | something happens | **No event at all** |
| NEC family, 8 bit/byte-order variants | decodes | **No event at all** (protocol inactive) |
| VOL+ 0xF2F0D0 | EV_KEY 0x73 | ✓ EV_KEY 115 (KEY_VOLUMEUP), no MSC_SCAN |

Conclusion: the driver silently discards **every frame that does not match the key
table exactly**, producing no input event at all.

## 3. The w19 transform (the driver's internal language)

The driver accumulates the IR stream **LSB-first**; each transmitted byte lands in the
32-bit `w19` word bitrev8-transformed:

```
w19 = bitrev8(W2)<<24 | bitrev8(W1)<<16 | bitrev8(W0)<<8
(W0 = first byte sent = ADDR | CMD-high-nibble)
```

Verification: the VOL+ frame 0xF2F0D0 → w19 = **0x0b0f4f00** → matches an `ir_table.bin`
entry **exactly**. Key-table entries *are* w19 values.

## 4. ir_table.bin format (from the factory_ro partition)

- Header: `{u32 count=335, u32 magic}`; then 8-byte entries:
  `{u16 type, u16 keycode, u32 w19}`
- Types = protocol families: **1** = NEC customer 0x6699 · **0x12** = NEC 0x16b9 ·
  **8** = this TV's 56 kHz RCA family (158 entries)
- Parser: `tools/arduino/ir_tablo_parse.py`

## 5. The factory event: type-0x19

For a table-matched key, the driver (under special conditions) emits:

```
input_event(dev, type=0x19, code=KEYCODE, value=(code16<<16)|status)
```

- The daemon reads `cmd = (value>>16)&0xF = code16&0xF`, **`arg = event.code&0xFF =
  the table KEYCODE`**, `status = value&0xF` (1=down) — i.e. **the digit value comes
  from the table, not from the frame!**
- In the RCA family, `code16 = bitrev4(CMD&0xF)`
- Emission sits behind two locks:
  1. a **report-mode flag** (a kernel global) — off on the live device; the
     `/sys/venus_ir/*` nodes that set it are unlabeled for SELinux and **root-only**
  2. code16 must be in a special mask set ({5,7..0xB,0xD..0xF,0xf2..})

## 6. The impossibility proof (the project's central finding)

Combine the RCU sequence rules (doc 02) with the kernel facts:

1. A digit value must equal **a table keycode & 0xFF** (the kernel derives arg from the keycode)
2. The only family that can send digits is code16=0xD ⇒ that family's keycode low bytes
   are exactly: **{b2, a3, f7, ac, 81, 58, 92, ef}**
3. The first two bytes of the sequence are **fixed markers**: buf[0]=0x01, buf[1]=0x0C
4. 0x01 ∉ set, 0x0C ∉ set ⇒ **no valid 13-byte sequence can ever be constructed. Full stop.**

(On top of that, a second independent lock: the report-mode flag is off and root-only.
Either one alone would close the path.)

## 7. The birth secret of the p2p thread — solved

- The daemon's startup threads never create p2p (live /proc/840/task list: IR, UART,
  socket, preset, user_timer — no p2p).
- Disassembly: the only caller of `app_factory_p2p_interface` is the **commit branch of
  check_p2p** (`os_thread_create`, with a born-once handle==-1 guard).
- check_p2p's only caller is the IR thread.
- **Conclusion:** p2p is born only from a valid IR commit. IR is impossible ⇒ p2p is
  never born. **Neither a reboot nor a daemon restart changes this** (a restart itself
  requires a crash/reboot anyway, and thread_init has no such dependency). This finding
  saved us from a risky, pointless reboot — the DB already held the IP/port, and the
  "the thread will come up after a reboot" hope was disproven before it cost anything.
- Side finding: the old "ts_init_queue crashes at boot" theory was wrong —
  `os_mqueue_create` is a custom malloc queue with nothing to do with POSIX mqueue
  (that directory doesn't even exist on the TV, and it doesn't matter).

## 8. Live cross-evidence

- The 27856 socket (fun=0) wrote `RCU.IPAddr`/`sinPort`/`RandomCode` into the DB, read
  back with fun=1 — **the write channel is live**; ineffective only because the p2p
  thread was never born (thread-list proof).
- The logcat buffer was shown not to carry old boots (the daemon started 75 hours ago;
  its boot logs were long gone from every buffer) — **"no trace in the logs" ≠ "never
  happened"**; the definitive evidence was the /proc thread listing.

## 9. The scoreboard

| Root path | Status |
|---|---|
| IR → check_p2p → commit → p2p → FCMD → root | **Impossible** (markers absent from the table + report-mode lock) |
| UART (physical) → myuart → FCMD → root | Hardware sealed; software path closed by SELinux |
| Spawning p2p any other way | Its only birth path is the IR commit — proven |
| Reboot / daemon-restart for p2p | Useless — proven |
| Root through the 27856 socket | Parser hardened; theoretical NUL overflow unproven; every crash costs a reboot |

**Closing:** the software surface is exhausted. The one path that remains open in
principle is the physical UART — see the README's call-out for exactly what is prepared
and where to aim.
