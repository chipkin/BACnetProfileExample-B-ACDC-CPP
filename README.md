# BACnet B-ACDC (Access Control Door Controller) — C++ example

A complete, self-contained C++ tutorial that implements the **B-ACDC (Access
Control Door Controller)** device profile from ASHRAE 135 Annex L using the
[CAS BACnet Stack](https://store.chipkin.com/products/stacks/cas-bacnet-stack).

Part of the CAS BACnet Stack **BACnet profile example series** — one repository
per BACnet device profile. This example claims **only** B-ACDC.

A **B-ACDC is a door controller**: a small device that exposes one door to a
BACnet network so an access-control system can **lock and unlock it**. It is the
[B-SS example](https://github.com/chipkin/BACnetProfileExample-B-SS-CPP) plus a
single Access Door object — which makes it one of the smallest profiles in the
series, and a good place to start if you are new to BACnet objects that are
*commanded* rather than merely read.

## What this example supports

| Required BIBB | What it means | How this example does it |
|---|---|---|
| **DS-RP-B** | Execute ReadProperty | `SERVICE_READ_PROPERTY` enabled; `GetProperty*` callbacks |
| **DS-WP-B** | Execute WriteProperty | `SERVICE_WRITE_PROPERTY` enabled; `SetProperty*` callbacks |
| **DS-ACAD-B** | Present an Access Door whose value is readable + writable | `Access Door 1` ("Cobalt"), commandable |
| **DM-DDB-B** | Answer Who-Is with I-Am | Handled by the stack; plus an unsolicited I-Am on start-up |
| **DM-DOB-B** | Answer Who-Has with I-Have | Handled by the stack |

**Deliberately NOT included** — a B-ACDC does not require them, so a faithful
profile example leaves them out: ReadPropertyMultiple, SubscribeCOV, alarms and
events, scheduling, trending, and DeviceCommunicationControl. A door controller
that also reports access *events* is a **B-ACC** / **B-AACC** — a different
profile with its own example.

## Objects

| Object | Instance | Name | Notes |
|---|---|---|---|
| Device | 389011 | Rainbow | Configurable with `--deviceID` |
| Analog Input | 1 | Bronze | REAL, °C; read-only; starts at 21.5 |
| Binary Input | 1 | Emerald | active / inactive; read-only |
| Multi-State Input | 1 | Hot Pink | state 1..3; read-only |
| **Access Door** | **1** | **Cobalt** | **lock / unlock; WRITABLE, commandable** |
| Network Port | 1 | Vermilion | The BACnet/IP port (required) |

## The Access Door is commandable

This is the one idea the example exists to teach. An Access Door's
`Present_Value` is **not stored** — it is resolved by the stack from a 16-slot
**`Priority_Array`** plus a **`Relinquish_Default`**:

- `WriteProperty(Present_Value, value, priority)` sets slot `priority`.
- `WriteProperty(Present_Value, NULL, priority)` relinquishes slot `priority`.
- The stack reports the **highest-priority non-null slot** as `Present_Value`,
  or `Relinquish_Default` when every slot is null.

This example's door has `Relinquish_Default` = **lock**, so an uncommanded door
rests locked. That priority mechanism is exactly what a door wants in practice: a
fire-alarm system can command the door at a high priority and a badge reader at a
low one, and BACnet decides who wins — no application logic required.

The application stores the array and serves it; **it never answers
`Present_Value` itself**. The same pattern drives the outputs in the
[B-SA example](https://github.com/chipkin/BACnetProfileExample-B-SA-CPP).

`Present_Value` is a **BACnetDoorValue**: `0` = lock, `1` = unlock,
`2` = pulseUnlock, `3` = extendedPulseUnlock.

## An Access Door's required timing properties

Unlike the output objects in B-SA, an Access Door has three **required** timing
properties (clause 12.3), all in **tenths of a second**. This example serves all
three:

| Property | Value here | Meaning |
|---|---|---|
| `Door_Pulse_Time` | 30 (3.0 s) | How long a `pulseUnlock` holds the door unlocked *on a real controller* (this example serves the property but does not time-simulate the auto-revert - see the note in `SetPropertyEnumerated`) |
| `Door_Extended_Pulse_Time` | 100 (10.0 s) | The same, for `extendedPulseUnlock` (e.g. an accessibility door) |
| `Door_Open_Too_Long_Time` | 300 (30.0 s) | How long the door may stand open before it is a problem |

It also exposes the three **optional** status properties, because they are what
make the example legible — they report what the door *is*, next to what it was
*commanded* to be: `Door_Status`, `Lock_Status`, `Secured_Status`.

## Who serves what: application or stack?

For the **Access Door "Cobalt"** - the object that makes this a B-ACDC:

| Property | Served by | How |
|---|---|---|
| `Object_Identifier`, `Object_Type`, `Object_List`, `Property_List`, `Status_Flags` | **stack** | generated from the object you added |
| `Current_Command_Priority` | **stack** | computed from the Priority_Array (required at Protocol_Revision 24) |
| `Present_Value` | **you (write) / stack (read)** | `SetPropertyEnumerated` accepts a door-value write (lock/unlock/pulse); on read the **stack computes** it from the Priority_Array slots (highest non-null, or `Relinquish_Default` = **lock**) |
| `Priority_Array`, `Relinquish_Default` | **you** | `GetPropertyEnumerated` serves each slot's door value; `GetPropertyBool` reports whether a slot is null |
| `Reliability` | **you** | `GetPropertyEnumerated` - served as `no-fault-detected(0)`, which is also the datatype default, so it reads correctly either way |
| `Object_Name` | **you** | `GetPropertyCharString` |
| `Door_Pulse_Time`, `Door_Extended_Pulse_Time`, `Door_Open_Too_Long_Time` | **you** | `GetPropertyUnsignedInteger` - the timing properties no other object in this series has |
| `Event_State` | **stack**, sort of | no alarming here, so it reads `normal(0)` as a datatype default - correct by coincidence, not computation |

## Before you ship

This example is a tutorial, and it identifies itself as one. Everything in this
table is read by clients and shown to the operator in **every discovery tool on
the network**. Left as-is, your product appears on a real site announcing itself
as a Chipkin demo. None of it is cosmetic.

| Constant (`main.cpp`) | Ships as | Change it to |
|---|---|---|
| `VENDOR_IDENTIFIER` | `389` (Chipkin) | **Your** company's vendor ID. Assigned by ASHRAE, free: <https://bacnet.org/assigned-vendor-ids/> |
| `VENDOR_NAME` | `Chipkin Automation Systems` | Your company name - must match the vendor ID above. |
| `DEVICE_NAME` | `"Rainbow"` | Your door controller's `Object_Name`. **Must be unique across the BACnet internetwork** - see the note below. |
| `MODEL_NAME` | `CAS BACnet Stack Example - B-ACDC` | Your model designation - what a building operator reads to identify your door controller. |
| `DEVICE_DESCRIPTION` | a description of *this example* | What your door controller actually is. |
| `FIRMWARE_REVISION` / `APPLICATION_SOFTWARE_VERSION` | `1.0.0` | Your real versions - wire them to your build. |
| Device instance | `389011` (`--deviceID` overrides) | Must be unique on the internetwork. BACnet requires this to be configurable; keep it so. |

> **`Object_Name` uniqueness is the one that will bite you.** The device instance
> is runtime-configurable via `--deviceID`, but `DEVICE_NAME` is a compile-time
> constant. Ship two units and configure their instances correctly, and **both
> still announce `Object_Name "Rainbow"`** - a spec violation. In a real product,
> `Object_Name` must be per-unit configurable too (serial number, DIP switches,
> a config file, or a `--deviceName` argument).

`main.cpp` marks this block with a `CHANGE ALL OF THIS BEFORE YOU SHIP` banner.

## Build

```bash
git clone --recursive https://github.com/chipkin/BACnetProfileExample-B-ACDC-CPP.git
cd BACnetProfileExample-B-ACDC-CPP
cmake -B build -S .
cmake --build build --config Release
```

If you cloned without `--recursive`, run `git submodule update --init --recursive`
first. The first build compiles the whole CAS BACnet Stack (~600 source files) and
takes a few minutes; later incremental builds are fast.

## Run

```bash
./build/BACnetExampleBACDC                       # Linux/macOS
.\build\Release\BACnetExampleBACDC.exe           # Windows
```

Options: `--help`, `--version`, `--deviceID <n>` (default 389011), `--port <n>`
(default 47808). Interactive keys: `h` help, `q` quit, up/down nudge Analog
Input 1. The door is commanded over BACnet, not from the keyboard.

## Try it

With a BACnet client (e.g. the
[CAS BACnet Explorer](https://store.chipkin.com/products/tools/cas-bacnet-explorer)):

1. **Who-Is** → an I-Am from device **389011**, vendor **389**.
2. **ReadProperty** `Access Door 1` `Present_Value` → `lock` (nothing has
   commanded it, so it rests at `Relinquish_Default`).
3. **WriteProperty** `Access Door 1` `Present_Value` = `1` (unlock) at
   **priority 8** → read it back: `unlock`. `Lock_Status` now reads `unlocked`
   and `Secured_Status` reads `unsecured`.
4. **WriteProperty** `Present_Value` = `0` (lock) at **priority 1** → the door
   reads `lock`: priority 1 outranks the priority-8 unlock, even though the
   unlock came later. That is BACnet command arbitration doing its job.
5. **WriteProperty** `Present_Value` = `NULL` at priority 1 → the door returns to
   `unlock` (slot 8 is still commanded).
6. **WriteProperty** `Present_Value` = `NULL` at priority 8 → every slot is now
   null, so the door falls back to `Relinquish_Default` = `lock`.
7. **WriteProperty** `Present_Value` = `9` → rejected with `value-out-of-range`.

## Versions

| | |
|---|---|
| Example version | 1.0.0 |
| `common/` helper | 1.3.0 |
| CAS BACnet Stack | 6.0.0.0 (submodule pinned at the 6.x series commit) |
| Protocol_Revision | 24 (the stack default — the highest it supports) |
| Verified on | Windows (MSVC 2022, C++17) |

## License

The example source code is dedicated to the public domain under
[CC0-1.0](LICENSE) — copy it into your project freely. The **CAS BACnet Stack is
a separate, commercially licensed product** and is not covered by that
dedication; contact [Chipkin](https://store.chipkin.com/) for licensing.
