# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""What B-ACDC's wire tests share: this door controller's numbers, and starting it.

The setup, all on one host:

    test client (127.0.0.1, ephemeral UDP port) - the Peer: a Python BACnet client
        |  BACnet/IP, unicast
    BACnetExampleBACDC   UDP --port   Access Door 1 "Cobalt"

The Peer plays the part of whatever commands the door on a real site - an access
control panel (B-AACC), a fire-alarm interface, a commissioning tool. It writes and
reads the door over the wire exactly as those would; nothing reaches into the
example any other way.
"""
import argparse
import sys
import time
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

import wiretest  # noqa: E402  (the vendored harness at the repository root)
from wiretest import application_enumerated, application_unsigned  # noqa: E402,F401

# Match main.cpp.
DEVICE_INSTANCE = 389011
OBJECT_TYPE_ACCESS_DOOR = 30
DOOR = (OBJECT_TYPE_ACCESS_DOOR, 1)        # Access Door 1 "Cobalt"

# Access Door properties (cl. 12.26; numbers from cl. 21 BACnetPropertyIdentifier).
PROPERTY_DOOR_ALARM_STATE = 226
PROPERTY_DOOR_EXTENDED_PULSE_TIME = 227
PROPERTY_DOOR_OPEN_TOO_LONG_TIME = 229
PROPERTY_DOOR_PULSE_TIME = 230
PROPERTY_DOOR_STATUS = 231
PROPERTY_LOCK_STATUS = 233
PROPERTY_SECURED_STATUS = 235

# BACnetDoorValue, BACnetDoorStatus, BACnetLockStatus, BACnetDoorSecuredStatus,
# BACnetDoorAlarmState (cl. 21).
LOCK, UNLOCK, PULSE_UNLOCK, EXTENDED_PULSE_UNLOCK = 0, 1, 2, 3
DOOR_CLOSED, DOOR_OPENED = 0, 1
LOCKED, UNLOCKED = 0, 1
SECURED, UNSECURED = 0, 1
ALARM_NORMAL, ALARM_DOOR_OPEN_TOO_LONG, ALARM_FORCED_OPEN = 0, 2, 3

# Short timings the tests write first, in tenths of a second (main.cpp defaults are
# 3 s / 10 s / 30 s - far too slow for a test).
TEST_PULSE_TIME = 10            # 1.0 s
TEST_EXTENDED_PULSE_TIME = 25   # 2.5 s
TEST_OPEN_TOO_LONG_TIME = 15    # 1.5 s
SLACK = 0.6                     # seconds allowed for the controller's tick and the round trip


def parser(description):
    arguments = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    arguments.add_argument("--exe", default=str(wiretest.default_exe(REPOSITORY, "BACnetExampleBACDC")),
                           help="path to BACnetExampleBACDC (default: build/BACnetExampleBACDC)")
    arguments.add_argument("--port", type=int, default=47830,
                           help="the door controller's UDP port (default 47830)")
    return arguments


def start_door(args, label="door"):
    return wiretest.start(args.exe, ["--port", args.port], label)


def client(args):
    return wiretest.Client(args.port)


def door_value(door, property_identifier, array_index=None):
    return door.read_value(*DOOR, property_identifier, array_index)


def write_door(door, property_identifier, value_octets, priority=None):
    return door.write(*DOOR, property_identifier, value_octets, priority)


def acked(answer):
    return answer is not None and answer.pdu_type == wiretest.PDU_SIMPLE_ACK


def describe(answer):
    if answer is None:
        return "no answer"
    error = wiretest.error_class_and_code(answer.payload)
    if error:
        return f"Error class {error[0]} code {error[1]}"
    return f"APDU {answer.payload.hex()}"


def shorten_timings(door):
    """Write the short test timings; True when all three were accepted."""
    return all(acked(write_door(door, property_identifier, application_unsigned(value)))
               for property_identifier, value in ((PROPERTY_DOOR_PULSE_TIME, TEST_PULSE_TIME),
                                                  (PROPERTY_DOOR_EXTENDED_PULSE_TIME, TEST_EXTENDED_PULSE_TIME),
                                                  (PROPERTY_DOOR_OPEN_TOO_LONG_TIME, TEST_OPEN_TOO_LONG_TIME)))


def wait_until(start, seconds):
    """Sleep until `seconds` after the monotonic time `start`."""
    remaining = start + seconds - time.monotonic()
    if remaining > 0:
        time.sleep(remaining)
