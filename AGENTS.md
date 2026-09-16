# AGENTS.md

Guidance for AI coding agents working in this repository. See
<https://agents.md/> for the format. Human contributors should read
[README.md](README.md) first, then [TUTORIAL.md](TUTORIAL.md).

## What this project is

A **tutorial** C++ example that implements the BACnet **B-ACDC (Access Control
Door Controller)** device profile using the CAS BACnet Stack. It is one of a
series - one git repo per BACnet profile. The top priority is that the code reads
like a tutorial a customer can learn from and copy-paste. Favour clarity over
cleverness.

## Layout

This repository is self-contained:

- `main.cpp` - the example device.
- `common/` - the shared helper (vendored).
- `README.md` - what this example is. Keep it short and about THIS example only.
- `TUTORIAL.md` - how to extend and review the example. Long-form material that
  would bloat the README belongs here.
- `docs/PICS.md` - the Protocol Implementation Conformance Statement. Its
  objects-and-properties section is GENERATED from `docs/objects.json`; do not
  hand-edit between the `OBJECTS-PROPERTIES` markers.
- `docs/objects.json` - the input to that generator. Update it in the same change
  as any `main.cpp` change that adds an object or a `GetProperty*` branch.
- `submodules/cas-bacnet-stack/` - the **CAS BACnet Stack** as a git submodule
  (private; compiled from source). After cloning, run
  `git submodule update --init --recursive`.

The `PROFILE-TABLE` block in README.md is also generated, from the example-series
repository's `docs/profile-table.md`. Edit it there, not here.

## Build

Plain CMake, identical on every platform, in the adapter's default SOURCE mode
(the stack's sources are compiled into the executable - no prebuilt library, no
DLL, no per-platform pre-step):

```bash
git submodule update --init --recursive   # once, if not cloned with --recursive
cmake -B build -S .
cmake --build build --config Release
```

The first build compiles the whole stack (~600 files) and takes a few minutes;
rebuilds after that are incremental and fast. Use `-D CAS_STACK_DIR=...` only if
your stack lives outside the bundled submodule. Do not reintroduce a link-mode
flag or a series-root build script into the documented build: a customer
downloads this repository on its own and must be able to build it with the two
commands above.

## Run

```bash
./build/BACnetExampleBACDC [--port 47808] [--deviceID 389011]   # Linux/macOS
.\build\Release\BACnetExampleBACDC.exe [--port 47808] [--deviceID 389011]   # Windows
```

Interactive keys while running: `h` help, `q` quit, up/down nudge Analog Input 1.
The door is commanded over BACnet (WriteProperty), not from the keyboard.

## Conventions

- Device is named "Rainbow"; objects use the series' colour names (the Access
  Door is "Cobalt"); vendor id 389.
- Implement **only** the services and objects the B-ACDC profile requires -
  DS-RP-B, DS-WP-B, DS-ACAD-B, DM-DDB-B, DM-DOB-B - but expose **every required
  property** of each object for Protocol_Revision 24. In particular an Access Door
  requires `Door_Pulse_Time`, `Door_Extended_Pulse_Time`, and
  `Door_Open_Too_Long_Time`; all three are served.
- Do **not** add alarms/events, COV, scheduling, trending, or
  DeviceCommunicationControl. A door controller that reports access *events* is a
  B-ACC / B-AACC - a different profile with its own example.
- The Access Door is **commandable**: never serve `Present_Value` yourself. Serve
  the `Priority_Array` slots (typed getter for the value, Bool getter for
  "is this slot null?") plus `Relinquish_Default`, and let the stack resolve it.
- Match the surrounding code style: `const`-correct parameters, check every stack
  return value, keep `main.cpp` linear and well-commented.
- **Never edit `common/` in this repo alone** - it is a vendored copy shared by
  every example in the series, with its own version (`COMMON_VERSION`) and
  changelog (`common/CHANGELOG.md`). To change it: edit, bump the version, add
  a changelog entry, then re-copy `common/` into every example repository.

## How to verify a change

There are no unit tests; verification is behavioural:

1. Build, then run one instance on a clear UDP port.
2. With a BACnet client (e.g. the CAS BACnet Explorer), send **Who-Is** and
   confirm **I-Am** from device 389011.
3. **ReadProperty** every required property of every object and confirm the
   values; confirm `Protocol_Revision` is 24 and `Object_List` lists all six
   objects.
4. **WriteProperty** `Access Door 1` `Present_Value` = 1 (unlock) at priority 8,
   then read it back: `Present_Value` = unlock, `Lock_Status` = unlocked,
   `Secured_Status` = unsecured. Write NULL at priority 8 to relinquish and
   confirm the door falls back to `Relinquish_Default` = lock.
5. Write an out-of-range value (e.g. 9) and confirm it is rejected with
   `value-out-of-range`.
6. Confirm services that are not enabled (e.g. ReadPropertyMultiple,
   DeviceCommunicationControl) are rejected.
7. If you changed the objects or their properties, regenerate `docs/PICS.md`
   (`python tools/gen-objects-properties.py BACnetProfileExample-B-ACDC-CPP` from
   the series root) and confirm no row comes out flagged with ⚠.

## Releasing

Bump `APP_VERSION` in `main.cpp` and add an entry to [CHANGELOG.md](CHANGELOG.md),
then tag `vX.Y.Z`. The GitHub Actions workflow builds and publishes the release.

## License

See [LICENSE](LICENSE). The CAS BACnet Stack is a separate, commercially
licensed product and is not covered by it.
