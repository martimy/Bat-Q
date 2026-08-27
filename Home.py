# -*- coding: utf-8 -*-
"""
Copyright 2023-2026 Maen Artimy

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
from common.utils import init_session_state

# Initialize session state globally
init_session_state()

# Global page configuration (must be called once before running navigation)
st.set_page_config(
    page_title="Bat-Q: Network Analysis with Batfish",
    page_icon="🦇",
    layout="wide",
)

# Modern multi-page routing via st.navigation
pages = {
    "Network Setup": [
        st.Page("views/net_setup.py", title="Snapshots & Setup", default=True),
        st.Page("views/questions.py", title="Questions"),
    ],
    "Analysis & Verification": [
        st.Page("views/analysis.py", title="Network Analysis"),
        st.Page("views/fail_tests.py", title="Failure Tests"),
        st.Page("views/differential.py", title="Differential Analysis"),
    ],
    "Reporting": [
        st.Page("views/reporting.py", title="Analysis Reporting"),
    ],
}

pg = st.navigation(pages)

# Common UI elements (This shows up on EVERY view page)
st.logo("docs/pics/logo.svg", size="large", link=None, icon_image=None)

pg.run()
