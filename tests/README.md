# B-ACDC Wire Tests

Tests that drive the running door controller over BACnet/IP from outside it and
fail when its Profile Function - locking, unlocking and **re-locking** a door -
is removed. They put hand-built frames on the wire and check what comes back.
They are written against the series' shared harness in
[`../wiretest/`](../wiretest/README.md) (vendored, like `common/`); everything
specific to this door controller is here. Python 3 standard library only -
nothing to `pip install`.

## Running

Build the example (README "Build"), then from the repository root:

```bash
python3 tests/run_wire_tests.py --exe build/BACnetExampleBACDC
```

It runs the four scripts below one after another and ends with
`ALL WIRE TESTS PASSED` (exit 0) or the scripts that failed. Each script also
runs on its own with the same `--exe` / `--port` options (`--port`, default
47830, is the door controller's UDP port). The whole run takes about half a
minute: every test first writes short door timings (1.0 s pulse, 2.5 s extended
pulse, 1.5 s open-too-long) instead of the 3 s / 10 s / 30 s defaults.

CI (`.github/workflows/release.yml`) runs them on Linux after the smoke test.
On Windows all of them run except `door_keys_test.py`, which prints `SKIP`: it
types menu keys on the example's stdin, and Windows' `_kbhit()` reads only a
console.

A `[KNOWN GAP]` line is a requirement the door does not meet yet because of a
defect outside this example (the stack). It is reported on every run but does
not fail it; [`../TODO.md`](../TODO.md) says where it has to be fixed. If one
prints `[GAP CLOSED]`, that defect is fixed: make it a counted check.

## The setup

```
test client (127.0.0.1, ephemeral UDP port)  - the Peer
    |  BACnet/IP, unicast
BACnetExampleBACDC  UDP --port               - Access Door 1 "Cobalt"
```

The Peer is a Python BACnet client (`wiretest.Client`), never another example's
binary. It plays whatever commands the door on a site - an access panel, a
fire-alarm interface, a commissioning tool - and only ever talks to the door
over the wire. To make the door open and shut without anyone at the console, it
uses the standard's own mechanism: `Out_Of_Service` = TRUE makes `Door_Status`
writable and the door "respond to changes made to these properties, as if those
changes had occurred to the physical door" (ANSI/ASHRAE 135-2024 12.26.9 (d)).

## `pulse_test.py` - the door re-locks itself (DS-ACAD-B, 12.26.16 / 12.26.17)

- **Control:** the door answers, `lock`, `locked`, `secured`, nothing commanding
  it; `Property_List` lists the command, status, alarm and timing properties;
  the three timing properties are writable and read back.
- **pulseUnlock at priority 8:** at once `Present_Value`, `Priority_Array[8]` =
  pulseUnlock, `Current_Command_Priority` = 8, `Lock_Status` unlocked,
  `Secured_Status` unsecured; still unlocked at 60 % of `Door_Pulse_Time`;
  after it, `Priority_Array[8]` NULL, `Present_Value` lock,
  `Current_Command_Priority` NULL, `Lock_Status` locked, `Secured_Status`
  secured.
- **extendedPulseUnlock:** the same on `Door_Extended_Pulse_Time`, and still
  running once `Door_Pulse_Time` plus the slack has passed.

## `arbitration_test.py` - two masters, and writes to refuse (12.26.4, 19.2)

- UNLOCK at priority 5, then pulseUnlock at priority 8: acknowledged and
  relinquished at once (`Priority_Array[8]` NULL); the door stays unlock at
  priority 5. Relinquish 5: lock, `Current_Command_Priority` NULL.
- UNLOCK at priority 10, then pulseUnlock at priority 6: the pulse wins while it
  runs; after `Door_Pulse_Time` `Priority_Array[6]` is NULL and the door is back
  on the priority-10 UNLOCK (relay still open) - not on lock. Relinquish 10:
  lock, relay locked.
- `Present_Value` = 4 is refused and stores nothing. KNOWN GAP: the answer is a
  Reject (reason OTHER) from the stack's decoder, not Error PROPERTY /
  VALUE_OUT_OF_RANGE (cl. 15.9.1.3.1) - stack #3642, [`../TODO.md`](../TODO.md).
- `Door_Status` written while the door is in service: Error PROPERTY /
  WRITE_ACCESS_DENIED.

## `door_alarm_test.py` - Failure Modes: forced open, held open (12.26.19 / 12.26.20)

- `Out_Of_Service` = TRUE is accepted and `Status_Flags` shows OUT_OF_SERVICE.
- **Forced open:** `Door_Status` = opened while `Present_Value` is lock ->
  `Door_Alarm_State` forcedOpen, `Secured_Status` unsecured; shut -> normal,
  secured.
- **Held open too long:** pulseUnlock, the door opens during the pulse (normal),
  the pulse expires with the door open (`Present_Value` lock); half-way through
  `Door_Open_Too_Long_Time` still normal; after it, doorOpenTooLong; shut ->
  normal.
- `Out_Of_Service` = FALSE: writing `Door_Status` is refused again, and it reads
  the (shut) contact.

## `door_keys_test.py` - the Simulation's keys (Linux/macOS)

The same scenario driven by the console keys that stand in for the hardware,
observed over BACnet: `p` (badge) puts pulseUnlock in `Priority_Array[8]` and
opens the relay; `o` opens the door during the pulse (normal); the pulse
expires (`Priority_Array[8]` NULL, lock, relay locked) and the door is still
open past `Door_Open_Too_Long_Time` -> doorOpenTooLong; `o` shuts it -> normal;
`f` forces it while locked -> forcedOpen; `o` -> normal. The console printed
the relay, `Door_Status` and `Door_Alarm_State` transitions.

## Each check fails without its feature

Run 2026-10-14 against stack `6.x` @ `e6de4ffd` - Windows STATIC build for the
`main.cpp` rows, Linux for the key rows. Each row is `main.cpp` with one feature
removed, rebuilt, and the scripts that must catch it:

| Without | Script(s) | Result |
|---|---|---|
| **The whole change**: `main.cpp` of `main` (d089ae0) | `pulse_test.py` | 10/20 - `Door_Alarm_State` not in Property_List, timings not writable, neither pulse ever relinquished (Priority_Array[8] still 2 / 3, `Lock_Status` unlocked) |
| | `arbitration_test.py` | 10/17 - timings not writable, the lower-priority pulse stays in Priority_Array[8], the priority-6 pulse never expires |
| | `door_alarm_test.py` | 3/19 - Out_Of_Service and Door_Status not writable, no `Door_Alarm_State` |
| Pulse expiry (DoorTick step 1) | `pulse_test.py` | 13/20 - Priority_Array[8] still pulseUnlock / extendedPulseUnlock after their times, door unlocked |
| | `arbitration_test.py` | 14/17 - the priority-6 pulse never hands back to priority 10 |
| | `door_alarm_test.py` | 17/19 - the pulse never expires, so no doorOpenTooLong |
| extendedPulseUnlock timed on `Door_Pulse_Time` | `pulse_test.py` | 17/20 - relinquished at 1.0 s, not 2.5 s |
| Lower-priority pulse kept (12.26.4) | `arbitration_test.py` | 15/17 - Priority_Array[8] holds the pulse, which wins once priority 5 is relinquished |
| Lock relay not following Present_Value | `pulse_test.py` | 16/20 - `Lock_Status` locked during both pulses |
| | `arbitration_test.py` | 16/17 - relay locked under the priority-10 UNLOCK |
| Forced-open rule | `door_alarm_test.py` | 15/19 - opened while locked reads doorOpenTooLong, not forcedOpen |
| Open-too-long rule | `door_alarm_test.py` | 18/19 - still normal past `Door_Open_Too_Long_Time` |
| `Secured_Status` ignoring Door_Status / Lock_Status | `door_alarm_test.py` | 18/19 - secured with the door forced open |
| Out_Of_Service gate on Door_Status writes | `arbitration_test.py`, `door_alarm_test.py` | 16/17, 18/19 - Door_Status write ACKed while in service |
| Out_Of_Service not decoupling Door_Status | `door_alarm_test.py` | 17/19 - the written Door_Status is ignored: no forcedOpen, no doorOpenTooLong |
| `Door_Alarm_State` not enabled | `pulse_test.py`, `door_alarm_test.py` | the example refuses to start (it cannot make a disabled property writable) |
| Timing properties not writable | `pulse_test.py` | 11/20 - the 3 s / 10 s defaults stay, so neither pulse has expired when checked |
| `p` key does nothing (Linux) | `door_keys_test.py` | 5/9 |
| `o` key does nothing (Linux) | `door_keys_test.py` | 5/9 |
| `f` key does nothing (Linux) | `door_keys_test.py` | 7/9 - no forcedOpen |

The out-of-range check (`Present_Value` = 4 refused, nothing stored) is the
stack's at this pin - it never reaches `main.cpp` (stack #3642) - so it has no
`main.cpp` mutation; it is a refusal check, plus the KNOWN GAP for the error it
should be.

With nothing removed: Windows (STATIC build) 56/56 with `door_keys_test.py`
skipped; Linux (WSL Ubuntu 22.04, the documented SOURCE build, Python 3.10)
65/65, twice in a row, no `[RETRY]`.

Re-run 2026-10-15 against stack `6.x` @ `64b2cfac5` with `wiretest/` 0.5.0:
Windows (STATIC build) 56/56 with `door_keys_test.py` skipped; Linux (WSL
Ubuntu 22.04, SOURCE build, Python 3.10) 65/65 twice, no `[RETRY]`; the stack
#3642 line still prints `[KNOWN GAP]`. The pulse-expiry row above was re-run at
this pin on Windows and gave the same 13/20, 14/17, 17/19. The other rows were
not re-run.
