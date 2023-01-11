"""Some useful functions."""

import contextlib
import socket


def internet_on():
    """Check whether there is a working internet connection

    Returns:
        bool: True if internet is up and running
    """
    with contextlib.suppress(Exception):
        # Check if we can resolve the host name
        host = socket.gethostbyname("www.google.com")
        # Connect to the host
        socket.create_connection((host, 80), 2)
        return True
    return False
