# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""UDP sockets that send BACnet/IP frames and collect what comes back."""
import socket
import time

from .codec import (PDU_COMPLEX_ACK, PDU_CONFIRMED_REQUEST, Frame, bvlc, decoded_values, npdu,
                    read_property_request, read_property_value, write_property_request)


class Endpoint:
    """A UDP socket (127.0.0.1, ephemeral port by default) that sends frames and keeps every reply."""

    def __init__(self, port=0, bind_ip="127.0.0.1", reuse=False):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if reuse:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((bind_ip, port))
        self.port = self.sock.getsockname()[1]
        self.frames = []

    def send(self, frame, port, ip="127.0.0.1"):
        self.sock.sendto(frame, (ip, port))

    def _receive(self, timeout):
        self.sock.settimeout(timeout)
        try:
            data, source = self.sock.recvfrom(2048)
        except socket.timeout:
            return False
        self.frames.append(Frame(data, source))
        return True

    def collect(self, seconds):
        """Keep every datagram arriving in the next `seconds`; returns all frames so far."""
        deadline = time.monotonic() + seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self._receive(remaining):
                return self.frames

    def wait_for(self, predicate, seconds):
        """The first decoded frame (already kept, or arriving within `seconds`) that matches, or None."""
        deadline = time.monotonic() + seconds
        seen = 0
        while True:
            for frame in self.frames[seen:]:
                if frame.ok and predicate(frame):
                    return frame
            seen = len(self.frames)
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self._receive(remaining):
                for frame in self.frames[seen:]:
                    if frame.ok and predicate(frame):
                        return frame
                return None

    def close(self):
        self.sock.close()


class Client(Endpoint):
    """A BACnet client of ONE device on one UDP port: numbers its confirmed requests and
    returns the answer to each (the Frame, or None after `timeout` seconds).

        door = Client(47820)
        answer = door.write(30, 1, PROPERTY_PRESENT_VALUE, application_enumerated(2), priority=8)
        answer.pdu_type == PDU_SIMPLE_ACK
        door.read_value(30, 1, PROPERTY_PRESENT_VALUE)          # -> 2
    """

    def __init__(self, device_port, device_ip="127.0.0.1", timeout=2, retries=1, **endpoint_options):
        super().__init__(**endpoint_options)
        self.device_port = device_port
        self.device_ip = device_ip
        self.timeout = timeout
        self.retries = retries
        self.next_invoke_id = 0

    def request(self, build):
        """Send the confirmed request `build(invoke_id)` returns; wait for its answer.

        Unanswered after `timeout` seconds, it is sent again with the SAME invoke ID, up
        to `retries` times - what every BACnet client does (APDU_Timeout /
        Number_Of_APDU_Retries; TimeoutUnsegmented in the client state machine,
        cl. 5.4.4). Each retry prints a [RETRY] line, so a device that needs them is
        visible in the test output rather than silently tolerated."""
        self.next_invoke_id = (self.next_invoke_id + 1) % 256
        invoke_id = self.next_invoke_id
        octets = bvlc(npdu(build(invoke_id), expecting_reply=True))
        for attempt in range(1 + self.retries):
            if attempt:
                print(f"[RETRY] invoke ID {invoke_id} unanswered after {self.timeout} s - sent again", flush=True)
            self.send(octets, self.device_port, self.device_ip)
            answer = self.wait_for(lambda frame: frame.network_message is None and frame.invoke_id == invoke_id and
                                   frame.pdu_type != PDU_CONFIRMED_REQUEST, self.timeout)
            if answer is not None:
                return answer
        return None

    def read(self, object_type, instance, property_identifier, array_index=None):
        return self.request(lambda invoke_id: read_property_request(
            invoke_id, object_type, instance, property_identifier, array_index))

    def read_values(self, object_type, instance, property_identifier, array_index=None):
        """The decoded values of a ReadProperty answer (see codec.decoded_values), or None
        when the answer is not a ComplexACK."""
        answer = self.read(object_type, instance, property_identifier, array_index)
        if answer is None or answer.pdu_type != PDU_COMPLEX_ACK:
            return None
        return decoded_values(read_property_value(answer.payload) or b"")

    def read_value(self, object_type, instance, property_identifier, array_index=None):
        """The single value a ReadProperty returns (NULL -> None), or the string 'no answer'
        / 'error' so a comparison with an expected value fails readably."""
        answer = self.read(object_type, instance, property_identifier, array_index)
        if answer is None:
            return "no answer"
        if answer.pdu_type != PDU_COMPLEX_ACK:
            return "error"
        values = decoded_values(read_property_value(answer.payload) or b"")
        return values[0] if len(values) == 1 else values

    def write(self, object_type, instance, property_identifier, value_octets, priority=None, array_index=None):
        return self.request(lambda invoke_id: write_property_request(
            invoke_id, object_type, instance, property_identifier, value_octets, priority, array_index))


def broadcast_listener(broadcast_ip, port):
    """Receives what an example BROADCASTS on one UDP port, and nothing it is sent unicast.

    Bound to the broadcast address itself (not 0.0.0.0), so unicast datagrams for the
    example's own socket on the same port still reach the example - only datagrams
    addressed to broadcast_ip:port are delivered here too. Both sockets set SO_REUSEADDR,
    which is what lets a second socket share the port; that sharing is POSIX behaviour,
    so broadcast checks run on Linux/macOS (Windows' SO_EXCLUSIVEADDRUSE, which common/
    sets deliberately, refuses it)."""
    return Endpoint(port, bind_ip=broadcast_ip, reuse=True)
