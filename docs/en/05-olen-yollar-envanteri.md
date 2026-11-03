# 05 — The Dead-End Inventory

> Every vector closed during the project, with its cause of death. If another researcher
> attacks the same device, this list will save them hours. Everything is proven; there
> are no "probably"s here.

## Attempts to open a channel into the daemon

| Path | Why it died |
|---|---|
| IR RCU sequence → commit → p2p | The central impossibility proof — doc 04 (missing table markers + report-mode lock) |
| Spawning p2p by DB writes | The thread is born only from an IR commit; DB writes were tested live, no thread was born |
| p2p via reboot / daemon restart | thread_init never creates p2p (disasm + live thread list) |
| Software UART (/dev/ttyS0 TIOCSTI, TIOCM_LOOP) | SELinux serial_device: open denied for system_app/shell (avc proof) |
| Fake IR events via /dev/input/* and /dev/uinput | root:input 660 — shell cannot write; uhid the same |
| Bluetooth remote emulation (HID factory sequence) | The daemon only processes the venus_IR_input device; BT HID lands in input-core as a different device; type-0x19 cannot be produced |
| NEC protocol frames (3 customer families × bit/byte-order variants) | Protocol inactive on this unit — 8 variants tried, zero events; the enabling sysfs is root-only |

## HAL / HIDL surface

| Path | Why it died |
|---|---|
| ITclUbootEnv (setUbootEnv = root env writes) | SELinux `find` allowed only for the system_server domain; NoSuchElementException + avc denied from system_app. No vector into system_server |
| ITclDevManager upgradeFirmware | No connected TCL device; early-return with a junk file (retval=1); the path is dead without a device |
| HAL debug(NativeHandle, options) | No override — IBase default dprintf |
| RKP/CSR command injection (fun=4 attr=0x8b, `system("%s > %s")`) | The called amzn_dha_tool/dhaprov-tool binaries don't exist in this firmware (exit 32512 — not the Amazon variant); the impdata path is also read from the config layer |
| wcl_generate single-quote injection (source: memory.factory.cpu.number) | Same flow: dak_provision runs first and dies — the injection never fires (payloads tested: `x';sh /tmp/x.sh;#` etc.) |
| preset_keys thread (calls `fpi_system_shell_cmd`!) | `/impdata` is root:root 755 — no file can be placed; a key-burn precedes the shell call (key writes were out of bounds ethically anyway) |
| monitord (root) | Only a watchdog reboot (persist.vendor.rtk.monitord_enabled=1 → reboots after 5 s) — no exec |
| doconfig_create (json_dom_list_save) | retval=1 but readback unchanged — no in-memory override / different layer |
| doCmdCopyFile (M5 matrix, 10 combinations) | access(src)+access(dst) both must exist; quoted `cp` — injection closed; 10/10 false |
| /tmp/ota staging | system:system 770; no consumer among the vendor binaries |

## Property/config layers

| Path | Why it died |
|---|---|
| Expecting DB writes to change config | DB layer ≠ config layer: reads come from /tclconfig/json_sys.ini (RO); DB writes don't reflect (live test) |
| Setting odm.tcl.factory.* properties from shell | SELinux property-context — the shell domain cannot write them (writes are HAL/root only) |

## Kernel / system level

| Path | Why it died |
|---|---|
| /sys/venus_ir/* (protocol switch, report mode) | Nodes are SELinux-unlabeled — inaccessible to shell/system_app |
| SICK-2020-012 (TCL's 2020 public root, the chmod 0777 vendor pattern) | Patched on this firmware |
| Kernel 5.4 generic LPEs, known Android 12 exploits | Security patch 2025-12-05 — closed |
| Boot-partition modification (Magisk/AVB) | Signature + brick risk + limited physical access — effectively closed, out of scope |
| Updating via USB | Signature wall (OTACERT) + forbidden by the project's own rules |
| FOTA package signature (the HUAN-Sign/MD5 vein) | Solved academically, but the package never passed acceptance — an interesting finding, not a path |

## Hardware-specific

| Path | Why it died |
|---|---|
| Phone IR blaster (Redmi) | Transmit proven at the HAL; zero decodes at the target (the era's carrier mistake) — by the time 56 kHz was found, the rig was already dismantled |
| LED photodiode capture/verification | Drowned in 50 Hz mains flicker (106 recordings, all mains) |
| Physical UART / internal pins | The TV belongs to the family — the case cannot be opened (a project boundary, not a technical one) |
| External service/RS232 jack | Back panel examined: HDMI×3, antenna, LAN, USB, one small jack (label unreadable) — **open question**; hotel-model TCLs have it, this class usually doesn't |

## The 27856 socket parser (special note)

`recvfrom` fixed 144B + `recv==144` check + `fun<=7` check + SQLite parameterized.
A 64-byte strKey/strValue NUL-overflow into the neighboring strlen field exists **on
paper**; no concrete impact was ever demonstrated. Blind fuzzing = every crash kills the
daemon = only a reboot brings it back (with the factory-screen accident as precedent) —
a bad trade, never attempted.
