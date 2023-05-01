# -*- coding: utf-8 -*-
"""
Copyright 2023 Maen Artimy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import socket


def test_connection(host, port=9996):
    """
    Test connection to host
    """
    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Set the timeout to 5 seconds
    sock.settimeout(5)

    success = False
    msg = ""
    # Attempt to connect to the host and port
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            success = True
            msg = f"{host} is reachable"
        else:
            msg = f"{host} is not reachable"

    except socket.gaierror:
        msg = "Hostname could not be resolved"
    except socket.timeout:
        msg = "Connection attempt timed out"
    finally:
        sock.close()

    return success, msg
