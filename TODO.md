# TODO

Defects this example cannot fix itself. Each one is reported as a `[KNOWN GAP]`
line by the Wire Tests ([`tests/`](tests/README.md)): reported on every run, not
counted as a failure. When one prints `[GAP CLOSED]` instead, the defect is fixed
upstream - turn its check into a counted one and delete the entry here.

## 1. An out-of-range Present_Value gets a Reject, not Error VALUE_OUT_OF_RANGE

- **Where:** the CAS BACnet Stack -
  [chipkin/cas-bacnet-stack#3642](https://github.com/chipkin/cas-bacnet-stack/issues/3642)
  (owner question #3799).
- **What:** WriteProperty of Access Door `Present_Value` = 4 (or any value that is
  not a BACnetDoorValue) is answered with a **Reject, reason OTHER**, produced
  while the stack decodes the request. ANSI/ASHRAE 135-2024 clause 15.9.1.3.1
  lists "The value provided is outside the range of values that the property can
  take on" as Error PROPERTY / VALUE_OUT_OF_RANGE.
- **Effect here:** the write is still refused and nothing is stored, so the door
  is safe; only the error a client sees is wrong. `SetPropertyEnumerated` in
  `main.cpp` already answers VALUE_OUT_OF_RANGE for such a value - it is not
  reached at this Stack Pin.
- **Wire Test:** `arbitration_test.py`, "... with Error PROPERTY / VALUE_OUT_OF_RANGE".
