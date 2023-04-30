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
import time
import streamlit as st
import logging


INTRO = """
This is a Streamlit app that enables the user to run network analysis 
queries using [Batfish](https://www.batfish.org/). 

Batfish is an open-source tool used for network analysis and verification. 
It allows network engineers to model and analyze network configurations and 
identify configuration errors, security vulnerabilities, and other potential 
issues before they cause problems.
"""

x = """
Batfish is an open-source tool used for network analysis and verification. 
It allows network engineers to model and analyze network configurations and 
identify configuration errors, security vulnerabilities, and other potential 
issues before they cause problems.

In Batfish, a network is defined as a collection of network devices 
(routers, switches, firewalls, etc.) and their configurations. The network is 
specified using configuration files, which are parsed by Batfish to create an 
abstract representation of the network. This representation allows Batfish to 
perform various types of analysis on the network, such as verifying routing 
policies, identifying security risks, and predicting network behavior under 
different scenarios.

A snapshot in Batfish refers to a specific point in time of the network's 
configuration files. A snapshot captures the state of the network at a 
particular moment, including the devices, configurations, and network topology. 
Batfish allows users to take snapshots of the network periodically, enabling 
them to track changes in the network over time and identify configuration 
drift or changes that could potentially cause issues.

Batfish questions are the queries or analyses that users can perform on network 
configurations using Batfish. These questions allow users to specify complex 
queries and perform various types of analyses on the network configurations.
Find more information about Batfish questions
[here](https://batfish.readthedocs.io/en/latest/index.html).
"""

logging.getLogger("pybatfish").setLevel(logging.ERROR)


def test_connection(host, port=9996):
    """
    Test connection to Batfish server

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


st.set_page_config(layout="wide")
st.title('Bat-Q')
st.markdown(INTRO)


# Get Batfish host from user
if 'host' not in st.session_state:
    st.session_state.host = 'localhost'

if 'hostreacable' not in st.session_state:
    st.session_state.hostreacable = False
    
host = st.text_input(
    'Enter Batfish host:', st.session_state.get('host', 'localhost'))

if not st.session_state.hostreacable:
    connected, message = test_connection(host)
    placeholder = st.empty()
    if connected:
        placeholder.success(message)
        st.session_state.host = host
        st.session_state.hostreacable = True
    else:
        placeholder.error(message)
    time.sleep(1) # Wait for 3 seconds
    placeholder.empty()
