#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""B-ACDC Wire Test - Failure Modes: a door forced open, and a door held open too long.

    python3 tests/door_alarm_test.py [--exe build/BACnetExampleBACDC] [--port 47830]

Nobody stands at the door during a test, so the Peer (a Python client) moves it the
way the standard provides for: it takes the Access Door Out_Of_Service and writes
Door_Status. ANSI/ASHRAE 135-2024 12.26.9: when Out_Of_Service is TRUE, "(c) ... the
Door_Status, Lock_Status and Door_Alarm_State properties shall be writable to allow
simulating specific conditions or for testing purposes; (d) other functions that
depend on the state of ... the Door_Status ... shall respond to changes made to these
properties, as if those changes had occurred to the physical door."

  - Forced open: Door_Status OPENED while Present_Value is LOCK -> Door_Alarm_State
    FORCED_OPEN and Secured_Status UNSECURED; shut it -> NORMAL.
  - Open too long (12.26.19 (a)): pulseUnlock, the door opens (NORMAL - access was
    granted), the pulse expires and the door re-locks with the door still open.
    Part-way through Door_Open_Too_Long_Time: still NORMAL. After it:
    DOOR_OPEN_TOO_LONG. Shut it -> NORMAL.
  - Out_Of_Service FALSE again: Door_Status is back on the (simulated) contact,
    CLOSED, and writing it is refused again.
"""
import sys
import time

import acdc_setup as setup
from acdc_setup import (ALARM_DOOR_OPEN_TOO_LONG, ALARM_FORCED_OPEN, ALARM_NORMAL, DOOR_CLOSED, DOOR_OPENED, LOCK,
                        PULSE_UNLOCK, SECURED, SLACK, UNSECURED, acked, application_enumerated, describe, door_value,
                        wait_until, write_door)
import wiretest
from wiretest import (PROPERTY_OUT_OF_SERVICE, PROPERTY_PRESENT_VALUE, PROPERTY_STATUS_FLAGS, application_boolean,
                      record)

def alarm(door):
    return door_value(door, setup.PROPERTY_DOOR_ALARM_STATE)


def set_door_status(door, door_status):
    return acked(write_door(door, setup.PROPERTY_DOOR_STATUS, application_enumerated(door_status)))


def main():
    args = setup.parser(__doc__).parse_args()
    example = setup.start_door(args)
    door = setup.client(args)
    try:
        record("Setup: short door timings accepted", setup.shorten_timings(door))
        record("Control: Door_Alarm_State NORMAL, Door_Status CLOSED at start",
               (alarm(door), door_value(door, setup.PROPERTY_DOOR_STATUS)) == (ALARM_NORMAL, DOOR_CLOSED))

        answer = write_door(door, PROPERTY_OUT_OF_SERVICE, application_boolean(True))
        record("Out_Of_Service TRUE is accepted", acked(answer), describe(answer))
        flags = door_value(door, PROPERTY_STATUS_FLAGS)   # BACnetStatusFlags: 4 bits, bit 0 first
        record("Status_Flags shows OUT_OF_SERVICE",
               isinstance(flags, list) and len(flags) == 4 and flags[wiretest.STATUS_FLAG_OUT_OF_SERVICE],
               f"read {flags}")

        # --- Failure Mode 1: forced open -------------------------------------------------
        record("Door_Status OPENED is writable while out of service", set_door_status(door, DOOR_OPENED))
        time.sleep(0.2)
        state = (door_value(door, PROPERTY_PRESENT_VALUE), alarm(door), door_value(door, setup.PROPERTY_SECURED_STATUS))
        record("Opened while LOCK: Door_Alarm_State FORCED_OPEN, Secured_Status UNSECURED",
               state == (LOCK, ALARM_FORCED_OPEN, UNSECURED), f"read (Present_Value, alarm, secured) {state}")
        record("The door shuts", set_door_status(door, DOOR_CLOSED))
        time.sleep(0.2)
        state = (alarm(door), door_value(door, setup.PROPERTY_SECURED_STATUS))
        record("Shut again: Door_Alarm_State NORMAL, Secured_Status SECURED", state == (ALARM_NORMAL, SECURED),
               f"read {state}")

        # --- Failure Mode 2: held open too long after a pulse ---------------------------
        answer = write_door(door, PROPERTY_PRESENT_VALUE, application_enumerated(PULSE_UNLOCK), priority=8)
        pulsed_at = time.monotonic()
        record("pulseUnlock at priority 8 is accepted", acked(answer), describe(answer))
        record("Someone walks through: Door_Status OPENED", set_door_status(door, DOOR_OPENED))
        time.sleep(0.2)
        record("Opened during the pulse: Door_Alarm_State stays NORMAL (access was granted)",
               alarm(door) == ALARM_NORMAL, f"read {alarm(door)}")

        relock_time = setup.TEST_PULSE_TIME / 10
        open_too_long = setup.TEST_OPEN_TOO_LONG_TIME / 10
        wait_until(pulsed_at, relock_time + SLACK)
        record("The pulse expired: Present_Value LOCK with the door still open",
               door_value(door, PROPERTY_PRESENT_VALUE) == LOCK)
        wait_until(pulsed_at, relock_time + open_too_long * 0.5)
        record(f"{open_too_long * 0.5:.2f} s after re-lock (of {open_too_long:.1f} s): still NORMAL",
               alarm(door) == ALARM_NORMAL, f"read {alarm(door)}")
        wait_until(pulsed_at, relock_time + open_too_long + SLACK)
        record(f"{open_too_long:.1f} s after re-lock: Door_Alarm_State DOOR_OPEN_TOO_LONG",
               alarm(door) == ALARM_DOOR_OPEN_TOO_LONG, f"read {alarm(door)}")
        record("The door shuts", set_door_status(door, DOOR_CLOSED))
        time.sleep(0.2)
        record("Shut again: Door_Alarm_State NORMAL", alarm(door) == ALARM_NORMAL, f"read {alarm(door)}")

        # --- Back in service ---------------------------------------------------------------
        record("Out_Of_Service FALSE is accepted", acked(write_door(door, PROPERTY_OUT_OF_SERVICE, application_boolean(False))))
        answer = write_door(door, setup.PROPERTY_DOOR_STATUS, application_enumerated(DOOR_OPENED))
        record("In service again: writing Door_Status is refused", answer.error is not None,
               describe(answer))
        record("Door_Status reads the contact again: CLOSED",
               door_value(door, setup.PROPERTY_DOOR_STATUS) == DOOR_CLOSED)
    finally:
        door.close()
        example.stop()
        if not all(wiretest.results.RESULTS):
            example.keep_log()
    return wiretest.summary()


if __name__ == "__main__":
    sys.exit(main())
