#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""B-ACDC Wire Test: the door Simulation's own keys, observed over BACnet (Linux/macOS).

    python3 tests/door_keys_test.py [--exe build/BACnetExampleBACDC] [--port 47830]

door_alarm_test.py moves the door through Out_Of_Service. This one moves it the way
an operator at the console does - the keys that stand in for the hardware - and
reads the result over the wire, so the simulated contact and relay themselves (not
just the written-value path) are proven to drive Door_Status, Lock_Status and
Door_Alarm_State:

  p  a badge: pulseUnlock at priority 8 -> Priority_Array[8] pulseUnlock, the relay
     opens (Lock_Status UNLOCKED); after Door_Pulse_Time it is relinquished, LOCKED.
  o  the door opens during the pulse (NORMAL), stays open past the re-lock ->
     DOOR_OPEN_TOO_LONG after Door_Open_Too_Long_Time; o again shuts it -> NORMAL.
  f  the door is forced while locked -> FORCED_OPEN; o shuts it -> NORMAL.

The keys reach the example on its stdin, which common/'s PollKey() reads on POSIX
only (Windows' _kbhit() reads a console, not a pipe), so on Windows this prints
SKIP and passes.
"""
import os
import sys
import time

import acdc_setup as setup
from acdc_setup import (ALARM_DOOR_OPEN_TOO_LONG, ALARM_FORCED_OPEN, ALARM_NORMAL, DOOR_CLOSED, DOOR_OPENED, LOCK,
                        LOCKED, PULSE_UNLOCK, SLACK, UNLOCKED, door_value, wait_until)
import wiretest
from wiretest import PROPERTY_PRESENT_VALUE, PROPERTY_PRIORITY_ARRAY, record

KEY_SETTLE = 0.3   # seconds for a key to be read and the door to tick


def door_and_alarm(door):
    return door_value(door, setup.PROPERTY_DOOR_STATUS), door_value(door, setup.PROPERTY_DOOR_ALARM_STATE)


def main():
    args = setup.parser(__doc__).parse_args()
    if os.name == "nt":
        print("[SKIP] door_keys_test.py - menu keys reach the example through stdin on Linux/macOS only")
        return 0
    example = setup.start_door(args)
    door = setup.client(args)
    try:
        record("Setup: short door timings accepted", setup.shorten_timings(door))

        example.press("p")
        badged_at = time.monotonic()
        time.sleep(KEY_SETTLE)
        state = (door_value(door, PROPERTY_PRIORITY_ARRAY, 8), door_value(door, setup.PROPERTY_LOCK_STATUS))
        record("p (badge): Priority_Array[8] pulseUnlock, lock relay open (Lock_Status UNLOCKED)",
               state == (PULSE_UNLOCK, UNLOCKED), f"read {state}")
        example.press("o")
        time.sleep(KEY_SETTLE)
        record("o (walk through during the pulse): Door_Status OPENED, Door_Alarm_State NORMAL",
               door_and_alarm(door) == (DOOR_OPENED, ALARM_NORMAL), f"read {door_and_alarm(door)}")
        wait_until(badged_at, setup.TEST_PULSE_TIME / 10 + SLACK)
        state = (door_value(door, PROPERTY_PRIORITY_ARRAY, 8), door_value(door, PROPERTY_PRESENT_VALUE),
                 door_value(door, setup.PROPERTY_LOCK_STATUS))
        record("After Door_Pulse_Time: Priority_Array[8] NULL, Present_Value LOCK, relay locked",
               state == (None, LOCK, LOCKED), f"read {state}")
        wait_until(badged_at, setup.TEST_PULSE_TIME / 10 + setup.TEST_OPEN_TOO_LONG_TIME / 10 + SLACK)
        record("Door still open Door_Open_Too_Long_Time after the re-lock: DOOR_OPEN_TOO_LONG",
               door_and_alarm(door) == (DOOR_OPENED, ALARM_DOOR_OPEN_TOO_LONG), f"read {door_and_alarm(door)}")
        example.press("o")
        time.sleep(KEY_SETTLE)
        record("o (the door shuts): Door_Status CLOSED, Door_Alarm_State NORMAL",
               door_and_alarm(door) == (DOOR_CLOSED, ALARM_NORMAL), f"read {door_and_alarm(door)}")

        example.press("f")
        time.sleep(KEY_SETTLE)
        record("f (forced while locked): Door_Status OPENED, Door_Alarm_State FORCED_OPEN",
               door_and_alarm(door) == (DOOR_OPENED, ALARM_FORCED_OPEN), f"read {door_and_alarm(door)}")
        example.press("o")
        time.sleep(KEY_SETTLE)
        record("o (the door shuts): Door_Alarm_State NORMAL", door_and_alarm(door) == (DOOR_CLOSED, ALARM_NORMAL),
               f"read {door_and_alarm(door)}")
        console = example.output()
        record("The console printed the transitions (relay, Door_Status, Door_Alarm_State)",
               all(text in console for text in ("lock relay energised", "Door_Status opened",
                                                "Door_Alarm_State normal -> doorOpenTooLong",
                                                "Door_Alarm_State normal -> forcedOpen")))
    finally:
        door.close()
        example.stop()
        if not all(wiretest.results.RESULTS):
            example.keep_log()
    return wiretest.summary()


if __name__ == "__main__":
    sys.exit(main())
