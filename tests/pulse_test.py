#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""B-ACDC Wire Test: a pulse unlock re-locks the door by itself (DS-ACAD-B, cl. 12.26).

    python3 tests/pulse_test.py [--exe build/BACnetExampleBACDC] [--port 47830]

ANSI/ASHRAE 135-2024 12.26.16: Door_Pulse_Time is "the maximum duration of time, in
tenths of seconds, for which the door will be unlocked when the Present_Value has a
value of PULSE_UNLOCK, after which time the Present_Value shall be automatically
relinquished at the priority that established the PULSE_UNLOCK command." 12.26.17
says the same of EXTENDED_PULSE_UNLOCK and Door_Extended_Pulse_Time.

A Python client (the Peer) writes the pulse at priority 8, reads the door at once
(unlocked, the command in Priority_Array[8], Current_Command_Priority 8, the lock
relay open) and again after the pulse time (Priority_Array[8] NULL, Present_Value
LOCK, the relay locked, the door secured).
"""
import sys
import time

import acdc_setup as setup
from acdc_setup import (EXTENDED_PULSE_UNLOCK, LOCK, LOCKED, PULSE_UNLOCK, SECURED, SLACK, UNLOCKED,
                        UNSECURED, acked, application_enumerated, describe, door_value, wait_until, write_door)
import wiretest
from wiretest import PROPERTY_CURRENT_COMMAND_PRIORITY, PROPERTY_PRESENT_VALUE, PROPERTY_PRIORITY_ARRAY, record


def door_state(door):
    """(Present_Value, Priority_Array[8], Current_Command_Priority, Lock_Status, Secured_Status)."""
    return (door_value(door, PROPERTY_PRESENT_VALUE), door_value(door, PROPERTY_PRIORITY_ARRAY, 8),
            door_value(door, PROPERTY_CURRENT_COMMAND_PRIORITY), door_value(door, setup.PROPERTY_LOCK_STATUS),
            door_value(door, setup.PROPERTY_SECURED_STATUS))


def pulse(door, value, pulse_seconds, label):
    """Write `value` at priority 8, check the door while the pulse runs and after it."""
    answer = write_door(door, PROPERTY_PRESENT_VALUE, application_enumerated(value), priority=8)
    written_at = time.monotonic()
    record(f"{label}: WriteProperty(Present_Value = {value}, priority 8) is accepted", acked(answer), describe(answer))

    state = door_state(door)
    record(f"{label}: at once - Present_Value {value}, Priority_Array[8] {value}, Current_Command_Priority 8",
           state[:3] == (value, value, 8), f"read {state[:3]}")
    record(f"{label}: at once - Lock_Status UNLOCKED, Secured_Status UNSECURED (the relay followed the command)",
           state[3:] == (UNLOCKED, UNSECURED), f"read {state[3:]}")

    # Still unlocked part-way through: the pulse is not cut short by something else.
    wait_until(written_at, pulse_seconds * 0.6)
    state = door_state(door)
    record(f"{label}: at {pulse_seconds * 0.6:.1f} s of {pulse_seconds:.1f} s - still {value} and UNLOCKED",
           (state[0], state[3]) == (value, UNLOCKED), f"read Present_Value {state[0]}, Lock_Status {state[3]}")

    wait_until(written_at, pulse_seconds + SLACK)
    state = door_state(door)
    record(f"{label}: after {pulse_seconds:.1f} s - Priority_Array[8] NULL (relinquished at its own priority)",
           state[1] is None, f"read {state[1]}")
    record(f"{label}: after {pulse_seconds:.1f} s - Present_Value LOCK, Current_Command_Priority NULL",
           (state[0], state[2]) == (LOCK, None), f"read {state[0]}, {state[2]}")
    record(f"{label}: after {pulse_seconds:.1f} s - Lock_Status LOCKED, Secured_Status SECURED (re-locked)",
           state[3:] == (LOCKED, SECURED), f"read {state[3:]}")


def main():
    args = setup.parser(__doc__).parse_args()
    example = setup.start_door(args)
    door = setup.client(args)
    try:
        record("Control: the door answers, LOCKED and SECURED, nothing commanding it",
               door_state(door) == (LOCK, None, None, LOCKED, SECURED), f"read {door_state(door)}")
        listed = setup.door_values(door, wiretest.PROPERTY_PROPERTY_LIST)
        served = {PROPERTY_PRESENT_VALUE, PROPERTY_PRIORITY_ARRAY, PROPERTY_CURRENT_COMMAND_PRIORITY,
                  setup.PROPERTY_DOOR_STATUS, setup.PROPERTY_LOCK_STATUS, setup.PROPERTY_SECURED_STATUS,
                  setup.PROPERTY_DOOR_ALARM_STATE, setup.PROPERTY_DOOR_PULSE_TIME,
                  setup.PROPERTY_DOOR_EXTENDED_PULSE_TIME, setup.PROPERTY_DOOR_OPEN_TOO_LONG_TIME}
        record("Property_List lists the door's command, status, alarm and timing properties",
               served <= set(listed), f"missing {sorted(served - set(listed))}")
        record("Door_Pulse_Time / Door_Extended_Pulse_Time / Door_Open_Too_Long_Time are writable",
               setup.shorten_timings(door))
        record("Door_Pulse_Time reads back what was written",
               door_value(door, setup.PROPERTY_DOOR_PULSE_TIME) == setup.TEST_PULSE_TIME,
               f"read {door_value(door, setup.PROPERTY_DOOR_PULSE_TIME)}")

        pulse(door, PULSE_UNLOCK, setup.TEST_PULSE_TIME / 10, "pulseUnlock")
        pulse(door, EXTENDED_PULSE_UNLOCK, setup.TEST_EXTENDED_PULSE_TIME / 10, "extendedPulseUnlock")
        # The extended pulse runs on its OWN time: read it once Door_Pulse_Time plus the
        # full slack has passed (1.6 s), which a controller that used Door_Pulse_Time for
        # both values would already have relinquished.
        answer = write_door(door, PROPERTY_PRESENT_VALUE, application_enumerated(EXTENDED_PULSE_UNLOCK), priority=8)
        written_at = time.monotonic()
        wait_until(written_at, setup.TEST_PULSE_TIME / 10 + SLACK)
        value = door_value(door, PROPERTY_PRESENT_VALUE)
        record("extendedPulseUnlock outlasts Door_Pulse_Time (it runs on Door_Extended_Pulse_Time)",
               acked(answer) and value == EXTENDED_PULSE_UNLOCK, f"read {value} at {setup.TEST_PULSE_TIME / 10 + SLACK:.1f} s")
        wait_until(written_at, setup.TEST_EXTENDED_PULSE_TIME / 10 + SLACK)
        record("... and is relinquished after Door_Extended_Pulse_Time",
               door_value(door, PROPERTY_PRIORITY_ARRAY, 8) is None and door_value(door, PROPERTY_PRESENT_VALUE) == LOCK)
    finally:
        door.close()
        example.stop()
        if not all(wiretest.results.RESULTS):
            example.keep_log()
    return wiretest.summary()


if __name__ == "__main__":
    sys.exit(main())
