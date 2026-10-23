import logging

import pytest

# Streamlit logs "missing ScriptRunContext" and similar notices whenever code
# is exercised outside a running app. They are expected in tests.
logging.getLogger("streamlit").setLevel(logging.ERROR)


@pytest.fixture
def bf_session_state(monkeypatch):
    """
    Replaces st.session_state with a plain dict-like object so helpers that
    read or write session state can be tested without a running app.
    """
    import streamlit as st

    class State(dict):
        __getattr__ = dict.get

        def __setattr__(self, key, value):
            self[key] = value

    state = State()
    monkeypatch.setattr(st, "session_state", state)
    return state
