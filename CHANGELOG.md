# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-15

### Changed

- **Stack pinned to `6.x` @ `abd4cee1` (6.0.21.0), STATIC link.** Replaces the
  `6.x-TestTool` @ `756371c1` pin. `common/` bumped to **v2.1.0** (verbatim copy
  from B-SS-CPP), byte-identical to the other migrated examples. (v2.1.0 adds
  `KeyCommand::DemoAdvance` for B-AAC's Wave 1 SCHED-I-B demo; purely additive,
  no change needed here.)
  - Every `GetProperty{Bool,CharacterString,Enumerated,OctetString,Real,UnsignedInteger}`
    callback gains a trailing `uint32_t* errorCode` out-parameter; each declines
    with `(void)errorCode` except `GetPropertyCharString`, which now names
    `ERROR_CODE_INVALID_ARRAY_INDEX` for an out-of-range `State_Text` read. See
    "THE errorCode OUT-PARAMETER" comment block in `main.cpp`.
  - `BACnetStack_AddNetworkPortObjectWithNetworkNumber` removed; replaced with
    the single `BACnetStack_AddNetworkPortObject`, which now always takes the
    network number and its quality.
  - `main.cpp` calls `CASExampleHelper::SetNetworkPortInstance(NETWORK_PORT_INSTANCE)`
    before `RegisterCommonCallbacks()`, so the shared transport callbacks know
    which Network Port object owns the socket.
  - This example now **builds and ships STATIC-only**
    (`CAS_BACNET_STACK_LINK=STATIC`, built from
    `tools/build-stack-static.sh`). `CMakeLists.txt` and the README no longer
    mention DLL/SOURCE as the way this example is built.
  - Release CI (`release.yml`) replaced with the Wave 0 template: builds the
    static library first, asserts `CAS_BACNET_STACK_LINK=STATIC` in
    `CMakeCache.txt`, smoke-tests the binary, and uploads `metrics-<os>.json`.

## [Unreleased]

### Changed

- **Documentation restructured to match the series' README + TUTORIAL + PICS
  shape** (see `BACnetProfileExample-B-SS-CPP`). `README.md` is now scoped to
  this example only; the extending/reviewing material moved to the new
  `TUTORIAL.md`, and the conformance statement moved to the new
  `docs/PICS.md` (partly generated from `docs/objects.json`, which now also
  lists the Device object). `AGENTS.md` updated to match the new file layout.
  - Corrected `docs/objects.json`: Binary Input 1 ("Emerald") is documented as
    starting **active**, matching what `GetPropertyEnumerated` actually
    returns — the previous note ("starts inactive"), carried over from the
    B-SS example, did not match this example's `main.cpp`.
  - The `CHANGE ALL OF THIS BEFORE YOU SHIP` block in `main.cpp` now carries a
    per-field comment (including the `DEVICE_NAME` uniqueness warning) that
    used to live only in the README's "Before you ship" table.
- **Build switched back to the adapter's default SOURCE mode** — plain
  `cmake -B build -S .` / `cmake --build build --config Release`, no
  `-DCAS_BACNET_STACK_LINK=STATIC` flag and no `tools/build-stack-static.sh`
  pre-step. `CMakeLists.txt`'s header comment and `release.yml` (link-mode
  assertion, metrics `"link_mode"`, dropped static-library cache/build steps
  and matrix `lib:` entries, packaged `TUTORIAL.md` + `docs/PICS.md`) updated
  to match. The v1.1.0 footprint table was measured from a STATIC build; the
  next release refreshes it from this SOURCE build.

## [1.0.0] - unreleased

> Not tagged yet: this repository has no tags at all. `release.yml` publishes binaries on a `v*.*.*`
> tag, so until that tag exists this section describes what is on the
> branch, not what shipped.

First release: a complete B-ACDC (Access Control Door Controller) tutorial.

### Added

- `main.cpp` implementing the **B-ACDC** profile and nothing more:
  - **DS-RP-B** — ReadProperty, with a `GetProperty*` callback per datatype.
  - **DS-WP-B** — WriteProperty, with `SetPropertyEnumerated` + `SetPropertyNull`.
  - **DS-ACAD-B** — `Access Door 1` ("Cobalt"), **commandable**: its
    `Present_Value` is resolved by the stack from a 16-slot `Priority_Array` plus
    a `Relinquish_Default` of `lock`, so an uncommanded door rests locked.
  - **DM-DDB-B / DM-DOB-B** — Who-Is/I-Am and Who-Has/I-Have (handled by the
    stack), plus an unsolicited I-Am broadcast on start-up.
- The four series base objects (Device "Rainbow" 389011, Analog Input 1 "Bronze",
  Binary Input 1 "Emerald", Multi-State Input 1 "Hot Pink") and the required
  Network Port 1 "Vermilion".
- All three of the Access Door's **required** timing properties — `Door_Pulse_Time`
  (3.0 s), `Door_Extended_Pulse_Time` (10.0 s), `Door_Open_Too_Long_Time` (30.0 s),
  in tenths of a second — plus its required `Reliability`.
- The Access Door's **optional** status properties `Door_Status`, `Lock_Status`,
  and `Secured_Status`, derived from the commanded value so a reader can see what
  the door *is* next to what it was *commanded* to be.
- Value validation: a `Present_Value` write outside the BACnetDoorValue range
  (0..3) is rejected with `value-out-of-range`.
- `README.md` (human tutorial), `AGENTS.md` (agent guidance), `LICENSE` (CC0-1.0),
  the vendored `common/` helper (v1.3.0), and a CMake build that compiles the CAS
  BACnet Stack from source.

### Notes

- Deliberately **not** implemented, because B-ACDC does not require them:
  ReadPropertyMultiple, SubscribeCOV, alarms/events, scheduling, trending, and
  DeviceCommunicationControl. A door controller that also reports access *events*
  is a B-ACC / B-AACC — a different profile with its own example.
- Verified against **CAS BACnet Stack 6.0.0.0** at **Protocol_Revision 24** (the
  stack default). Built and run on Windows (MSVC 2022, C++17): the device starts,
  registers all six objects, and broadcasts its I-Am.

[1.0.0]: https://github.com/chipkin/BACnetProfileExample-B-ACDC-CPP/commits/llm-auto-2026-july
