# 01 — Recon and Access Doors

> Phase: days 1–2. Device identity, acquiring the firmware, the attack-surface map, and
> the discovery of the **uid-1000 code-execution door**.

## 1. Device identity and ground rules

- TCL 65T61C — Android TV 12, Realtek RTD2875P/rtd6748, kernel 5.4.284+,
  security patch 2025-12-05 (i.e.: known public LPEs are closed).
- The RC833A remote is **dual-mode**: it connects as a HID device over Bluetooth when
  available and falls back to IR when Bluetooth is off. This distinction mattered in the
  IR phase: **Bluetooth was turned off before every IR test** (otherwise the tests are
  meaningless — and note: the TV came back from every reboot with Bluetooth in a random
  state).
- Ground rules set up front: own device, own network; persistent flags/reboots only with
  the owner's approval; no MID/SN/key writes ever; every step reversible.

## 2. Acquiring the firmware

The exact full OTA package for the device (**V8-R75PT01-LF1V618.zip**, ~2 GB) was
downloaded from TCL's update servers. Its contents became the backbone of the whole
project:

- `boot.img` → the kernel Image (48.7 MB, ARM64) — used on day 8 to solve the IR driver
- `factory_ro.img` → **ir_table.bin** (the kernel's IR key table!) + ir_table_rtk_bt.bin
- `vendor.img` → the tclfactoryos daemon, HAL services, TCL framework jars
- `bootloader.img`, `dtbo.img`, `Auxcode.bin` — archived

**Lesson:** no deep analysis happened before the firmware package was in hand — all
static RE ran through this vein. Solving things on paper before touching the live
device kept reboot risk at zero.

## 3. Attack-surface map (summary)

| Layer | Who | What |
|---|---|---|
| Adb (network) | shell uid 2000 | The entry point |
| `com.tcl.ttvs` app | system_app uid 1000 | TCL's system app — contains a door (below) |
| `tclfactoryos` | **root** | The factory daemon — the target (doc 02) |
| `vendor.tcl.factory@1.0-service` | root | The HAL middle layer |
| ITclDevManager / ITclUbootEnv | root | Additional HIDL surfaces (both dead — doc 05) |

## 4. The uid-1000 code-execution door (discovery #1)

A "diagnostic command runner" door was found in TCL's service infrastructure and proven
working live:

```
settings put global tcl_diagnostic_status 1
dumpsys activity service com.tcl.ttvs/com.tcl.guard.onlinesupport.service.OnlineSupportService \
  --i 3 "CLASSPATH=/system/framework/tcl-service.jar:/data/data/com.tcl.ttvs/files/M4.jar \
         app_process / M <mode> [args] > /data/data/com.tcl.ttvs/files/m4out.txt 2>&1"
```

- The `--i 3` argument puts the service into "run external command" mode; the command
  runs as **system_app (uid 1000)** — not root, but far more privileged than shell.
- Long jobs need the `&` background pattern with output read afterwards
  (the service closes its ~4-second foreground window).

### The M-jar harness family

Small Java harnesses were written to be called through this door, invoking tcl-service.jar's
HIDL interfaces **via reflection** (build: `javac --release 8` + `d8 --min-api 30`; the
HIDL jar is DEX, so it cannot be fed to javac — reflection is mandatory):

| Harness | Capabilities |
|---|---|
| M / M2 | pg (status reads), uartw (UART write attempts) |
| M3 | pmon/pmoff (P-mode on/off), pg, pmrd |
| M4 | + cfgw (doSet_property), cfgcreate/cfgdel, cmdcopy, **rootloop** (root-channel attempt) |
| M5–M9 | HAL probe matrices: doCmdCopyFile combinations, doconfig_create, Demura paths... |

Key wins:
- **pmon**: starts the daemon live **without rebooting the TV** (the init trigger
  `pmode=1 && hardready=1` → `start tclfactoryos`; the service is `disabled oneshot`).
  This kept a root daemon available for the entire project without a single reboot.
- **pmoff**: clears the boot flag but does not kill the daemon (proven live) — so a
  pmode toggle never revives a running daemon; this detail became part of the day-8
  "reboot is useless" proof.

**Important lesson (jar naming):** even if the jar file is `M3.jar`, the **class name is
`M`** — writing `app_process / M3 pmon` dies silently with ClassNotFoundException.
When output is empty, check the class name first.

## 5. Property layers and the first disappointment

A live test revealed that factory configuration has two separate layers:

- **DB layer:** `/userdata/factory_property.db` (SQLite). Writable **without whitelist**
  from the 27856 socket (doc 02) — `memory.factory.*` and even `sys.System.*`
  (write + readback proven).
- **Config layer:** many values the daemon reads come through `doconfig_get_str` →
  `/tclconfig/json_sys.ini` (a read-only mount). **Writing the DB does not reflect into
  config** (proven with the impdata-path test).

So the "I can write anything in the DB" impression was misleading: nothing read from the
config layer can be changed this way. This distinction killed several promising paths
before they wasted time (doc 05).

## 6. Outputs of this phase

- Arbitrary code running at uid-1000 (the reflection harness family)
- The daemon can be brought up at will, without rebooting (pmon)
- Free writes into the property DB (limited effect, but proven)
- The firmware vein fully open: kernel, vendor, factory_ro in hand

Next question: **what does the root daemon look like inside?** → doc 02.
