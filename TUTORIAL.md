# Tutorial - extending and reviewing the B-ACDC example

[README.md](README.md) says what this example *is*. This document is the *how*:
how to extend it into your own door controller, who serves which property, how
to review the result for conformance, and what goes wrong when you get it
subtly right.

Read this once before you start changing `main.cpp`. The most expensive mistake
in this example is silent, and the section it lives in is
[Add a second analog input](#add-a-second-analog-input).

- [Extending the example](#extending-the-example)
- [What each object type needs you to serve](#what-each-object-type-needs-you-to-serve)
- [Who serves what: the application or the stack?](#who-serves-what-the-application-or-the-stack)
- [Reviewing your device](#reviewing-your-device)
- [Troubleshooting](#troubleshooting)

## Extending the example

The example is intentionally small so it's easy to change.

**Change a sensor's value or name** - edit the constants / callbacks in
`main.cpp` (e.g. the initial value of `g_analogInput1Value`, or the `"Bronze"`
string in `GetPropertyCharString`).

**Change the device identity before you ship** - vendor ID, vendor name, model
name, description, firmware revision and device name are all in the
`CHANGE ALL OF THIS BEFORE YOU SHIP` block at the top of `main.cpp`, with a
per-field note on each saying what to change it to. That block is the
authoritative checklist; it is in the source rather than here so it cannot be
skipped by someone who only reads the code.

**Change the door's timing** - `Door_Pulse_Time`, `Door_Extended_Pulse_Time`,
and `Door_Open_Too_Long_Time` are compile-time constants (in tenths of a
second) next to the Access Door section of `main.cpp`. A real controller would
also *act* on `Door_Pulse_Time` / `Door_Extended_Pulse_Time` - re-locking the
door automatically after a `pulseUnlock` / `extendedPulseUnlock` expires. This
example deliberately does not time-simulate that auto-revert (see the note in
`SetPropertyEnumerated`): it serves the properties, but the door stays at
whatever value was last commanded until written again or relinquished. Wiring
the auto-revert to the tick loop is a natural next step if you build on this.

### Add a second analog input

Read this whole recipe before starting — the last step is the one that is easy
to miss and the one BTL will fail you for.

> **Why there are four edits, not three — and why skipping one is SILENT.**
> Most of the `GetProperty*` callbacks match on **both** object type *and*
> instance (`objectInstance == ANALOG_INPUT_INSTANCE`), so a new instance falls
> through every one of them. `GetPropertyBool` is the exception: it matches on
> type only, so `Out_Of_Service` works for a new instance for free.
>
> Here is the part that matters, and it is the opposite of what most people
> assume: falling through a callback does **not** reliably produce an
> error. The stack errors only for the few properties it refuses to invent —
> `Present_Value`, `Number_Of_States`, `Relinquish_Default`, `Local_Date`,
> `Local_Time`, and a Network Port's `APDU_Length`. For everything else it **silently substitutes a default**:
>
> | Property | If you forget to serve it | Loud? |
> |---|---|:--:|
> | `Present_Value` | Error (`read-access-denied`) | yes |
> | `Object_Name` | reads back as the string **`"undefined"`** | **no** |
> | `Units` | reads back as **`no-units` (95)** | **no** |
> | `Out_Of_Service` | served on type alone — works by accident | n/a |
>
> **Doesn't the `errorCode` out-parameter fix this?** Only if you use it, and
> only where it is right to. Each `GetProperty*` callback ends with a
> `uint32_t* errorCode` that the stack presets to `success` and reads only when
> you return `false`, so you *can* turn any decline into a chosen BACnet error.
> But ending every callback with `*errorCode = unknown-property` breaks the
> device: the stack's decline-and-fabricate path is what answers required
> properties an application is not expected to serve — the Device's
> `Max_APDU_Length_Accepted`, `APDU_Timeout` and `Number_Of_APDU_Retries` among
> them. Name an error on the catch-all and those start failing instead of
> answering. Set `errorCode` only where *this device* knows the read is wrong;
> `main.cpp` does it in exactly one place, `State_Text` with an out-of-range
> array index. The table above is still how the fall-through behaves, and the
> diff below is still what catches a missed step.
>
> It is worse than "wrong value": the object's `Property_List` **still advertises
> `Units` (117)**. So the object actively claims to have the property, and then
> answers with a default. Nothing on the wire says you forgot anything.
>
> So a half-added object does not look broken; it looks **healthy**. Add two of
> them and both report `Object_Name "undefined"` — duplicate object names inside
> one device, which is a spec violation and a hard BTL failure that every scan
> tool will render as a perfectly good object. **"It scanned OK" is exactly the
> failure mode, not evidence against it.**

```cpp
// 1) a new instance number (in section 1).
//    Naming: a second object of a type is "<Colour> 2" - so Analog Input 2 is
//    "Bronze 2", NOT a new colour. Each object TYPE owns one colour series-wide.
static const uint32_t ANALOG_INPUT_2_INSTANCE = 2;   // "Bronze 2"
static float g_analogInput2Value = 23.1f;            // its live value

// 2) add the object (in main, next to the other BACnetStack_AddObject calls).
//    Check the return, like every other stack call in this file.
if (!BACnetStack_AddObject(g_deviceInstance, OBJECT_TYPE_ANALOG_INPUT, ANALOG_INPUT_2_INSTANCE)) {
    printf("Error: Failed to add Analog Input 2 (Bronze 2).\n");
    return 1;
}

// 3) serve its Present_Value + Object_Name:
//    GetPropertyReal:        AI/2 + Present_Value -> *value = g_analogInput2Value;
//    GetPropertyCharString:  AI/2 + Object_Name   -> "Bronze 2"

// 4) DO NOT SKIP: serve its Units, in GetPropertyEnumerated.
//    Units is a REQUIRED property of an Analog Input. The existing check reads
//    `objectInstance == ANALOG_INPUT_INSTANCE`, which is instance 1 - so without
//    this, reading Analog Input 2's Units returns an ERROR and the object is
//    NON-CONFORMANT. It will still appear in the Object_List and its
//    Present_Value will read back perfectly, so the device looks healthy right
//    up until BTL certification.
//    GetPropertyEnumerated:  AI/2 + Units -> *value = ENGINEERING_UNITS_DEGREES_CELSIUS;
```

Then re-run the README's Verify steps **against Analog Input 2**, not just Analog
Input 1 — read every required property and **diff it against Analog Input 1**.
Any property that comes back `"undefined"`, `no-units`, or `0` where object 1
returns something real is a step you missed. Because the failure is silent (see
the table above), this diff is the only thing that catches it.

### Add a second commandable object

The same silent-failure pattern applies to a second Access Door, with one extra
trap: `GetCommandable()` maps `(objectType, objectInstance)` to exactly one
`Commandable` struct. Forget to add a case there for the new instance and every
`GetPropertyEnumerated` / `GetPropertyBool` / `SetPropertyEnumerated` /
`SetPropertyNull` lookup for it silently returns "not mine" - the new door
compiles, adds cleanly, and then **every WriteProperty to it is rejected** with
no hint why, because none of the setters recognise it as commandable.

## What each object type needs you to serve

The application must serve every REQUIRED property the stack does not generate.
It differs per type — this is the checklist, so you do not have to infer it:

| Object type | You must serve | Plus |
|---|---|---|
| Analog Input | `Present_Value` (Real), `Object_Name`, `Units` | — |
| Binary Input | `Present_Value` (Enumerated), `Object_Name` | `Polarity` |
| Multi-State Input | `Present_Value` (Unsigned), `Object_Name` | `Number_Of_States` |
| Access Door | `Object_Name`, `Reliability`, `Relinquish_Default`, `Door_Pulse_Time`, `Door_Extended_Pulse_Time`, `Door_Open_Too_Long_Time` | `Priority_Array` (via the commandable slot helpers) - `Present_Value` itself is **stack-computed**, never served by the app |

## Who serves what: the application or the stack?

The single most common question when reading this file is "who answers this
property?" For the **Access Door "Cobalt"** — the object that makes this a
B-ACDC — the whole picture:

| Property | Served by | How |
|---|---|---|
| `Object_Identifier`, `Object_Type`, `Object_List`, `Property_List`, `Status_Flags` | **stack** | generated from the object you added |
| `Current_Command_Priority` | **stack** | computed from the Priority_Array (required at Protocol_Revision 24) |
| `Present_Value` | **you (write) / stack (read)** | `SetPropertyEnumerated` accepts a door-value write (lock/unlock/pulse) at a priority; on read the **stack computes** it from the Priority_Array slots (highest non-null, or `Relinquish_Default` = lock) |
| `Priority_Array` | **you** | `GetPropertyEnumerated` serves each slot's door value; `GetPropertyBool` reports whether a slot is null |
| `Relinquish_Default` | **you** | `GetPropertyEnumerated` |
| `Reliability` | **you** | `GetPropertyEnumerated` - served as `no-fault-detected(0)`, which is also the datatype default, so it reads correctly either way |
| `Out_Of_Service` | **you** | `GetPropertyBool` — matched on object **type only** |
| `Door_Pulse_Time`, `Door_Extended_Pulse_Time`, `Door_Open_Too_Long_Time` | **you** | `GetPropertyUnsignedInteger` - the required timing properties no other object in this series has |
| `Door_Status`, `Lock_Status`, `Secured_Status` *(optional)* | **you** | `GetPropertyEnumerated` - derived from the resolved commanded value; a real controller would read them from door hardware instead |
| `Event_State` | **stack**, sort of | no intrinsic alarming here, so nothing serves it — it reads `normal` only because `normal` is the enumeration's zero value and the stack substitutes a datatype default. Correct by coincidence, not design. |

Every object, not just this one, is in [docs/PICS.md](docs/PICS.md).

Going beyond a single commandable door (multiple doors, access events, alarms)
means implementing a richer profile — see the series table in
[README.md](README.md).

## Reviewing your device

After you have changed anything, review it against the conformance statement
rather than against "it looked fine in the explorer":

1. Regenerate [docs/PICS.md](docs/PICS.md) after editing `docs/objects.json`
   (see [Keeping the PICS honest](#keeping-the-pics-honest) below). A ⚠ row is a
   required property nothing serves.
2. Read **every** property listed for **every** object with a BACnet client, and
   compare the value against the PICS. `"undefined"`, `no-units` and `0` are the
   three shapes a missed callback takes.
3. Diff a new object of a type against the existing one of that type. Anything
   that differs and shouldn't is a callback that matched on instance.
4. Confirm the services you do **not** implement are still rejected - for
   B-ACDC, ReadPropertyMultiple.
5. Exercise the Access Door's command arbitration specifically: write `unlock`
   at a low priority, then `lock` at a higher priority, and confirm the
   higher-priority write wins regardless of write order; relinquish it and
   confirm the door falls back to the next-highest slot, then to
   `Relinquish_Default` once every slot is null; write an out-of-range value
   (e.g. `9`) and confirm it is rejected with `value-out-of-range`.

### Keeping the PICS honest

`docs/PICS.md` is partly generated. `docs/objects.json` describes each object and
who serves which property; the series tool regenerates the object tables from it
plus the stack's own `docs/property-profile-reference.md` at the pinned commit:

```bash
python tools/gen-objects-properties.py BACnetProfileExample-B-ACDC-CPP            # rewrite
python tools/gen-objects-properties.py BACnetProfileExample-B-ACDC-CPP --check    # fail if stale
```

(That tool lives in the example-series repository, not in this one. If you only
have this repository, edit the generated block by hand and keep it matching the
callbacks in `main.cpp`.)

When you add an object or a property to `main.cpp`, update `docs/objects.json`
in the same change and regenerate. The `app` list is what the callbacks serve;
`accepted` is for a required property you deliberately leave to the stack's
default, and each one needs a justification. Anything required, not in `app` and
not in `accepted`, comes out as a ⚠ row - that is a defect, not a feature.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| On start-up the app prints a wall of red `Error:` lines but the device works | **Expected — this is not your bug.** Two benign sources, both from the stack's own debug logging: (1) the device receives its **own** broadcast I-Am and logs a decode cascade (*"Services is not supported service=[0]"* … *"Failed to process the incoming NPDU"*) — any BACnet/IP device that listens for broadcasts hears itself; (2) a one-time *"UUID has not been set. A UUID must be set for the BACnetSC device to start."* — the stack starts a BACnet/SC datalink these IP-only examples never configure. It appears once and does not spam. On a healthy start-up roughly half the output is these lines. |
| CMake error: *"CAS BACnet Stack adapter not found under: ..."* | Submodules not initialized. Run `git submodule update --init --recursive` (or pass `-D CAS_STACK_DIR=...`). |
| `CASBACnetStackDLL.h: No such file or directory` | Same - submodules not checked out. |
| Windows: *"No CMAKE_CXX_COMPILER could be found"* | Install Visual Studio with the "Desktop development with C++" workload, then re-run from a fresh terminal. |
| First build seems stuck for minutes | Normal - it's compiling ~600 stack files. Only the first build is slow. |
| App prints *"Failed to bind UDP port 47808"* | Another BACnet program is already using 47808. Stop it, or run with `--port <n>`. |
| Client sends Who-Is but sees no I-Am | Firewall is blocking UDP 47808, or the client and device are on different subnets (Who-Is is a broadcast). Allow the port; test on the same subnet first. |
| Replies show an unexpected device instance or vendor | Another BACnet device is already answering on this host/port. On Linux/macOS two processes can share the port and both reply; on Windows the example asks for `SO_EXCLUSIVEADDRUSE` (`common/SimpleUDP.cpp`) so this shows up as a bind failure instead. Stop the other device, or use `--port`. |
| WriteProperty to `Access Door 1` `Present_Value` succeeds but the value doesn't change | You wrote at a priority *lower* than an already-commanded slot. Higher priority (lower number) wins - relinquish the higher-priority slot first, or write at a higher priority (lower number) than it. |
| The door never re-locks after a `pulseUnlock` | Expected in this example - see "Change the door's timing" above. This example serves `Door_Pulse_Time` but does not time-simulate the auto-revert; a real controller wires that to its tick loop. |
