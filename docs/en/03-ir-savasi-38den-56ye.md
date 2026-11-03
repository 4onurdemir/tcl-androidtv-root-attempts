# 03 — The IR War: From 38 kHz Deaths to the 56 kHz Breakthrough

> Phase: days 3–7. The project's longest front. The story of a channel declared dead
> several times over — and its most valuable lesson: **the failures were caused by the
> wrong carrier frequency, not the protocol.**

## 1. Why IR?

Of the three channels into the root processor (doc 02), IR was the only one that
required no physical intervention. If the factory remote sequence (ARM + 13 digits)
could be transmitted over IR, the p2p thread would be born and the TV would **itself**
connect to the analysis machine.

## 2. The book of deaths (in order, all documented)

1. **Phone IR (Redmi blaster):** transmit proven at the HAL level via ConsumerIrManager;
   not a single decode on the TV. (The reason was learned later: we were sending 38 kHz.)
2. **Arduino v1–v12 (custom Timer2 CTC carrier):** the VOL+ code sent 7+ times with
   SENT-OK — not one line in the TV logs. BC557 PNP driver, inverted logic, idle-high…
   everything checked out; the result never changed.
3. **The LED question:** a phone camera saw the purple glow → the hardware **was**
   emitting light; the problem was in the signal.
4. **Photodiode capture (v9/v9B):** 106 recordings — all of them turned out to be
   50 Hz mains flicker. Photovoltaic-LED measurement drowns in ambient light; dead end.
5. **Flipper-IRDB TCL records:** confirmed our timing (header 4000+4000 µs, 500 µs bit,
   1000/2000 µs spaces) but listed a 38 kHz carrier — keeping us on the wrong frequency.
6. **The kernel source (TCLOpenSource rt2875p):** gave the RCA protocol, the factory
   address set, the bit transforms — and the same 38 kHz assumption.

## 3. The breakthrough: measuring with a KY-022 receiver

A cheap off-the-shelf receiver module (KY-022) was wired to the Arduino and **the
remote's own transmissions were measured** — not guessed, measured:

- **Carrier: 56 kHz.** (Outside the KY-022's 38 kHz passband — it only read at close
  range, while the TV decoded perfectly. This was the killer behind every 38 kHz
  attempt: the protocol was right, the frequency was wrong.)
- Header: **4000 µs mark + 4000 µs space**
- 24 bits, **MSB-first**: `ADDR(4) | CMD(8) | ~ADDR(4) | ~CMD(8)` — the TV validates
  against the inverted 12 bits
- Bit: **500 µs mark** + a space of **2000 µs = '1'** / **1000 µs = '0'**; a closing
  500 µs mark at the end
- The remote sends every frame **twice** per keypress
- This remote uses **ADDR = 0xF** for every key

## 4. The full 40-key table

Power, volume, channels, navigation, colors, YouTube/Netflix/Disney+/Prime and more —
all 40 keys recorded, with their ADDR+CMD+inversion+check columns verified (the source
table lives in `data/TCL-kumanda-kodlari.md`). Three of them were then driven into the
TV from our own circuit: **VOL+, VOL−, Mute — worked.** From that point on we had
hardware that could control the TV without its remote.

## 5. The transmitter hardware and the errata

- Circuit: Arduino Uno pin 3 → 2N2222A driver → 940 nm IR LED.
- **Errata:** the 2N2222A used here has its pins, flat face toward you, in **C–B–E**
  order. The setup PDFs in use said **E–B–C** — the circuit only worked with the
  transistor rotated 180°. For any other 2N2222A, verify with a multimeter's hFE socket.
- Software: `fabrika.ino` — a universal blaster driving any frame at 56 kHz via serial
  commands: `H/G <24-bit hex>` (RCA frame 2×/1×), `N/M/O` (NEC variants), `B/C` (bursts),
  `P` (ping). Firing script: `fabrika_atess.py`.

## 6. Two standing reminders from this phase

1. **Don't believe without measuring:** neither the Flipper database, nor kernel sources,
   nor another device's recordings replace this TV receiver's reality. The only source
   of truth was the remote's own signal.
2. A channel was never declared "solved" on the basis of "light came out" — the bar was
   always **an observed effect on the TV + a getevent/log record**. (That is why an
   earlier 0x92 false positive was retracted: its source turned out to be keypresses
   from our own remote.)

The IR layer was solved. The real question came next: could the factory sequence be
sent through this channel? → doc 04 (answer: no — proven).
