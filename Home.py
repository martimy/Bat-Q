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


logging.getLogger("pybatfish").setLevel(logging.WARNING)

st.set_page_config(layout="wide")
st.title("Bat-Q")
st.markdown(INTRO)
