# 06 — Lessons

> Proven, portable lessons from the project — for other devices and other sessions.
> Order: technical → method → discipline.

## Technical lessons

### 1. Measure the carrier before blaming the protocol
Days were spent at 38 kHz; the timing, the bit layout, the driver, the polarity — all
correct, nothing working. The cause was the **56 kHz carrier**. The frequency written in
sources (Flipper IRDB, kernel code, other devices' captures) was not valid for this TV's
receiver. **Lesson: a receiver's truth is only measured from its own transmitter's
signal.** A cheap receiver module (KY-022) + Arduino comes before any expensive analyzer.

### 2. The pinout lives in the part, not the datasheet
The 2N2222A used here had its pins (flat face toward you) in C–B–E order; two setup PDFs
said E–B–C. The circuit only worked with the transistor rotated 180°. **Lesson: verify a
transistor with a multimeter's hFE socket; don't trust the PDF.**

### 3. In the kernel, "no event" ≠ "event not processed"
Not seeing a trace in the daemon's logs does not mean the event wasn't produced — the
logcat buffer doesn't carry old events (a daemon boot from 75 hours earlier was gone
from every buffer). Definitive evidence: the `/proc/<pid>/task/*/comm` thread listing,
live `getevent -t`. **Before declaring "no log", prove your observation covers the event.**

### 4. Address columns in PIE binaries
r2's symbol list has two columns (paddr/vaddr); in this binary `vaddr = file-offset +
0x1000`. Raw python scans (BL decoding, literal pools) silently return nothing when run
against the wrong column — there is no error message. **Lesson: validate an empty scan
result against one known call first** (e.g. decode a known `bl` to test the decoder).
Thumb BL second halfword: `(w2 & 0xd000) == 0xd000`.

### 5. The property-layer split (TCL architecture)
Factory values live in two layers: the DB (SQLite, freely written from the socket) and
the config (json_sys.ini, a read-only mount the daemon reads). **Writing the DB changes
almost nothing.** Without understanding this split, "no whitelist" sounds like "I can
change everything."

### 6. Prove dependency chains; don't assume them
"The p2p thread will come up after a reboot" was a reasonable assumption — and wrong.
Only the IR commit ever spawns that thread; a reboot would have changed nothing.
**Lesson: every link in a chain that justifies a risky action (a reboot) must be tied
together with disassembly + live observation.** The same lesson in reverse: the fear
that "pulling the plug with pmode on boots the factory screen" was also examined — on
this device, a cold boot cleared the flag.

### 7. Impossibility is a result too
There is a difference between "we didn't get root" and "software root cannot be
constructed on this firmware (proof: the marker bytes are absent from the key-table
space)". The latter points the next person straight at what to check: **open the key
table first; look for 0x01/0x0C in the 0xD family.**

## Method lessons

### 8. Static RE before dynamic attempts
No risky dynamic experiment happened before the firmware package was pulled. The whole
daemon — kernel driver included — was solved on paper; the live device was only used
for verification. This made an 8-day campaign possible without a single reboot of a
family TV.

### 9. The evidence standard
The bar for every "worked/dead" claim was defined up front: for IR, not "light came out"
but **an observed effect on the TV + a getevent/log record**. This standard caught a
false positive (the 0x92 affair) and forced its retraction — the source turned out to be
keypresses from our own remote.

### 10. Dividing the work: measurement separate from analysis
The IR hardware measurements ran in a separate session (with another tool); root-layer
analysis and the firing runs stayed here. Each side kept its context; handoff prompts
carried the boundary without leaking the other side's knowledge.

### 11. Kill dead ends by documenting them
Every closed path went into the inventory (doc 05). Any urge to re-try a dead path was
refused by pointing at that inventory. A project without memory lifts the same stone
twice.

## Discipline lessons

### 12. The reboot rule was born in an accident
A reboot fired with P-mode on locked the TV into the factory pixel-test screen (remote
dead, Wi-Fi dead; ~40 minutes to rescue). From then on the rule was immutable:
**persistent flags / reboots only with the owner's approval.** Rules born from accidents
are not anecdotes — they are the project's constitution.

### 13. Cleanup is part of the project
At closing: DB values emptied, harness jars deleted, the diagnostics door shut,
Bluetooth (the family remote uses it) restored, every listener on the analysis machine
killed. **The device was left cleaner than it was found — because "reversible" was a
principle from day one, not a last-minute scramble.**

### 14. On long projects, the handoff file is survival
STATE.md was updated every session; a new session read it and continued exactly where
the last one stopped. The trio of a 60 KB archive + a current summary + persistent
memory reduced context loss to zero.
