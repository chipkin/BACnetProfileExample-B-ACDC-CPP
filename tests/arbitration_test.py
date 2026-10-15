#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""B-ACDC Wire Test: who wins when two sources command the door (cl. 12.26.4, cl. 19.2).

    python3 tests/arbitration_test.py [--exe build/BACnetExampleBACDC] [--port 47830]

ANSI/ASHRAE 135-2024 12.26.4: "If a value of PULSE_UNLOCK is written at a given
priority and the Present_Value is currently being commanded, at any value, at a
higher priority then the lower priority value will be relinquished immediately."

The Python client (the Peer) stands in for two masters - a fire-alarm interface at
priority 5 and an access panel at priority 8 - and for a careless client that
writes a value the door does not have.

  - UNLOCK at priority 5, then a pulse at priority 8: the pulse is acknowledged and
    gone at once (Priority_Array[8] NULL); the door stays UNLOCKed at priority 5.
  - Relinquish priority 5: the door falls back to Relinquish_Default, LOCK.
  - UNLOCK at priority 10, then a pulse at priority 6: the pulse wins while it runs,
    and when it is relinquished the door goes back to the priority-10 UNLOCK, not to
    LOCK - each pulse is relinquished at its own priority only.
  - Present_Value 4 (no such BACnetDoorValue) is refused and changes nothing. The
    spec's answer is Error PROPERTY / VALUE_OUT_OF_RANGE (cl. 15.9.1.3.1); the stack at
    this pin answers Reject (OTHER) while decoding - a KNOWN GAP, stack #3642.
  - Door_Status, which only an Out_Of_Service door accepts, is refused,
    write-access-denied, while the door is in service.
"""
import sys
import time

import acdc_setup as setup
from acdc_setup import (DOOR_OPENED, LOCK, LOCKED, PULSE_UNLOCK, SLACK, UNLOCK, UNLOCKED, acked,
                        application_enumerated, describe, door_value, wait_until, write_door)
import wiretest
from wiretest import (ERROR_CLASS_PROPERTY, ERROR_CODE_VALUE_OUT_OF_RANGE, ERROR_CODE_WRITE_ACCESS_DENIED,
                      PROPERTY_CURRENT_COMMAND_PRIORITY, PROPERTY_PRESENT_VALUE, PROPERTY_PRIORITY_ARRAY,
                      application_null, record)


def command(door, value, priority):
    octets = application_null() if value is None else application_enumerated(value)
    return write_door(door, PROPERTY_PRESENT_VALUE, octets, priority)


def main():
    args = setup.parser(__doc__).parse_args()
    example = setup.start_door(args)
    door = setup.client(args)
    try:
        record("Setup: short door timings accepted", setup.shorten_timings(door))

        # --- A lower-priority pulse under a higher-priority command -------------------
        record("UNLOCK at priority 5 is accepted", acked(command(door, UNLOCK, 5)))
        answer = command(door, PULSE_UNLOCK, 8)
        record("pulseUnlock at priority 8 (below the priority-5 command) is acknowledged", acked(answer), describe(answer))
        slot_8 = door_value(door, PROPERTY_PRIORITY_ARRAY, 8)
        record("... and relinquished immediately: Priority_Array[8] NULL", slot_8 is None, f"read {slot_8}")
        state = (door_value(door, PROPERTY_PRESENT_VALUE), door_value(door, PROPERTY_CURRENT_COMMAND_PRIORITY))
        record("The door stays UNLOCK, Current_Command_Priority 5", state == (UNLOCK, 5), f"read {state}")

        record("Relinquishing priority 5 is accepted", acked(command(door, None, 5)))
        state = (door_value(door, PROPERTY_PRESENT_VALUE), door_value(door, PROPERTY_CURRENT_COMMAND_PRIORITY))
        record("Nothing commands the door: Present_Value = Relinquish_Default LOCK, Current_Command_Priority NULL",
               state == (LOCK, None), f"read {state}")

        # --- A higher-priority pulse over a lower-priority command ---------------------
        record("UNLOCK at priority 10 is accepted", acked(command(door, UNLOCK, 10)))
        answer = command(door, PULSE_UNLOCK, 6)
        written_at = time.monotonic()
        record("pulseUnlock at priority 6 (above the priority-10 command) is accepted", acked(answer), describe(answer))
        state = (door_value(door, PROPERTY_PRESENT_VALUE), door_value(door, PROPERTY_CURRENT_COMMAND_PRIORITY))
        record("The pulse wins while it runs: Present_Value pulseUnlock, Current_Command_Priority 6",
               state == (PULSE_UNLOCK, 6), f"read {state}")
        wait_until(written_at, setup.TEST_PULSE_TIME / 10 + SLACK)
        slots = (door_value(door, PROPERTY_PRIORITY_ARRAY, 6), door_value(door, PROPERTY_PRIORITY_ARRAY, 10))
        record("After Door_Pulse_Time: Priority_Array[6] NULL, Priority_Array[10] still UNLOCK",
               slots == (None, UNLOCK), f"read {slots}")
        state = (door_value(door, PROPERTY_PRESENT_VALUE), door_value(door, PROPERTY_CURRENT_COMMAND_PRIORITY),
                 door_value(door, setup.PROPERTY_LOCK_STATUS))
        record("The door falls back to the priority-10 UNLOCK (not to LOCK), relay still open",
               state == (UNLOCK, 10, UNLOCKED), f"read {state}")
        record("Relinquishing priority 10 is accepted", acked(command(door, None, 10)))
        state = (door_value(door, PROPERTY_PRESENT_VALUE), door_value(door, setup.PROPERTY_LOCK_STATUS))
        record("... and the door locks: Present_Value LOCK, Lock_Status LOCKED", state == (LOCK, LOCKED), f"read {state}")

        # --- Writes the door must refuse ------------------------------------------------
        answer = command(door, 4, 8)
        record("Present_Value 4 (not a BACnetDoorValue) is refused (no SimpleACK)",
               setup.refused(answer), describe(answer))
        wiretest.known_gap("... with Error PROPERTY / VALUE_OUT_OF_RANGE (cl. 15.9.1.3.1)",
                           answer.error == (ERROR_CLASS_PROPERTY, ERROR_CODE_VALUE_OUT_OF_RANGE),
                           "the stack Rejects it (reason OTHER) while decoding, before main.cpp sees it: "
                           "chipkin/cas-bacnet-stack#3642")
        slot_8 = door_value(door, PROPERTY_PRIORITY_ARRAY, 8)
        record("... and stores nothing: Priority_Array[8] NULL", slot_8 is None, f"read {slot_8}")

        answer = write_door(door, setup.PROPERTY_DOOR_STATUS, application_enumerated(DOOR_OPENED))
        record("Door_Status written while in service is refused: Error PROPERTY / WRITE_ACCESS_DENIED",
               answer.error == (ERROR_CLASS_PROPERTY, ERROR_CODE_WRITE_ACCESS_DENIED), describe(answer))
    finally:
        door.close()
        example.stop()
        if not all(wiretest.results.RESULTS):
            example.keep_log()
    return wiretest.summary()


if __name__ == "__main__":
    sys.exit(main())
