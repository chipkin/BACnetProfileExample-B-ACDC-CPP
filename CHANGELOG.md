# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  the vendored `common/` helper (v1.1.0), and a CMake build that compiles the CAS
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
