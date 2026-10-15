# wiretest changelog

The shared Wiretest Harness of the BACnet profile example series. Vendored into each
example; `WIRETEST_VERSION` in `__init__.py` names the version.

## [0.2.0] - 2026-10-14

Added for B-ACDC's Wire Tests (a client that commands an object and reads it back);
nothing in it is door-specific.

### Added

- `codec`: `write_property_request` (cl. 15.9, optional priority and array index),
  an optional `array_index` on `read_property_request`, `application_null`,
  `application_boolean`, `decoded_values` (NULL / BOOLEAN / Unsigned / Enumerated to
  Python values), `error_class_and_code`, and the property / error numbers
  Out_Of_Service, Priority_Array, Relinquish_Default, Status_Flags, Property_List,
  Current_Command_Priority, VALUE_OUT_OF_RANGE.
- `endpoint`: `Client` - an `Endpoint` that numbers confirmed requests to one device
  and returns each answer (`request`, `read`, `read_values`, `read_value`, `write`).
  An unanswered request is re-sent once with the same invoke ID after 2 s, as any
  BACnet client retries (cl. 5.4.4 TimeoutUnsegmented), and prints a `[RETRY]` line when it is.
- `process`: `Program.press(keys)` - type menu keys on an example's stdin (POSIX only:
  common/'s `PollKey()` reads a pipe there, not on Windows).

### Fixed

- `process.Program` starts the example by its absolute path: on Windows a relative
  `--exe build/Release/X.exe` (forward slashes) was not found by `CreateProcess`.

## [0.1.0] - 2026-10-14

First cut, written for B-RTR's wire tests and kept free of anything router-specific.

### Added

- `codec`: BVLC (Original-Unicast/Broadcast, Forwarded-NPDU decode), NPDU encode/decode
  with DNET/DADR, SNET/SADR, hop count and network layer messages, APDU builders
  (ReadProperty request/ComplexACK, Error, Who-Is, I-Am, AddListElement /
  RemoveListElement, ReadAccessSpecification), tag reader and value helpers.
- `endpoint`: `Endpoint` (send, collect, wait_for) and `broadcast_listener` (POSIX).
- `process`: `Program` / `start` for an example binary, `broadcast_address` from
  common/'s TX console line, `default_exe`.
- `peer`: `SimulatedDevice`, a Python BACnet/IP device that answers ReadProperty and
  Who-Is and addresses answers back through a router (DNET/DADR from SNET/SADR).
- `results`: `record`, `known_gap`, `summary`.
