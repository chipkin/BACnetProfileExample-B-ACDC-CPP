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


class Door:
    """Access Door 1 as the Peer sees it: a wiretest.Client aimed at the door controller.
    One retry, as a BACnet client makes (it prints [RETRY] if it is ever needed)."""

    def __init__(self, args):
        self.client = wiretest.Client(retries=1)
        self.port = args.port

    def read(self, property_identifier, array_index=None):
        return self.client.read_property(self.port, *DOOR, property_identifier, array_index, timeout=2.0)

    def write(self, property_identifier, value_octets, priority=None):
        return self.client.write_property(self.port, *DOOR, property_identifier, value_octets, priority,
                                          timeout=2.0)

    def close(self):
        self.client.close()


def client(args):
    return Door(args)


def door_value(door, property_identifier, array_index=None):
    """The decoded value of a ReadProperty (NULL -> None), or 'no answer' / 'error' so a
    comparison with an expected value fails readably."""
    answer = door.read(property_identifier, array_index)
    if not answer.answered:
        return "no answer"
    if not answer.ok:
        return "error"
    return answer.value


def door_values(door, property_identifier):
    """Every value of a list- or array-valued property (Property_List), or []."""
    answer = door.read(property_identifier)
    return wiretest.decoded_values(answer.value_octets) if answer.ok else []


def write_door(door, property_identifier, value_octets, priority=None):
    return door.write(property_identifier, value_octets, priority)


def acked(answer):
    return answer.answered and answer.frame.pdu_type == wiretest.PDU_SIMPLE_ACK


def refused(answer):
    """An Error or a Reject - anything but an acknowledgement."""
    return answer.answered and answer.frame.pdu_type in (wiretest.PDU_ERROR, wiretest.PDU_REJECT)


def describe(answer):
    return answer.describe()


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
