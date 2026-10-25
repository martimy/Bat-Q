# Testing

Bat-Q has two kinds of tests. The **unit tests** need nothing but Python: they
use a fake Batfish session. The **integration tests** run the same code against
a real Batfish server.

## Setup

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

`requirements-dev.txt` only adds test tools (pytest, pytest-cov and openpyxl, which
reads the Excel reports back). Run everything from the repository root.

## Running the tests

```bash
python -m pytest                       # everything; integration tests skip without a server
python -m pytest -m "not integration"  # unit tests only
python -m pytest tests/test_utils.py   # one file
python -m pytest -k assertions         # tests whose name contains "assertions"
python -m pytest --cov=common --cov=views --cov-report=term-missing   # coverage
```

The unit tests take under a minute. Most of that time is spent starting the
pages, because each page test runs the real page script.

## What is tested

| Tests | What they cover |
|---|---|
| `test_utils.py`, `test_presenter.py`, `test_queries.py`, `test_plotting.py` | The helper functions in `common/`: naming, session defaults, cleaning of answers, trace flattening, `run_query`, topology graphs. |
| `test_htmlreport.py`, `test_spreadsheet.py` | The analysis report (HTML) and spreadsheet builders. |
| `test_bfqs.py` | The question schema (unique names, valid inputs, a hint for every input type) and its links to the assertion registry. |
| `test_assertions.py` | The assertion registry, the YAML format and validation, and the runner's pass, fail and error results. The registry is also checked against the installed pyBatfish. |
| `test_assertion_report.py` | The assertion report in HTML and Excel, and its page. |
| `test_docs.py` | That the examples in `docs/assertions.md` load and that the guide mentions every assertion. |
| `test_assertions_page.py`, `test_pages_analysis.py`, `test_page_questions.py`, `test_page_net_setup.py` | The pages (Assertions, Analysis, Differential, Failure Tests, Reporting, Questions, Snapshots & Setup), run headlessly. |
| `integration/` | The helpers, assertions, reports and pages against a real Batfish server. See below. |

## How the page tests work

Pages are run with Streamlit's `AppTest`, which executes a page script without a
browser. The tests put a **fake Batfish session** in the session state and then
click buttons and read the resulting elements and state.

- `tests/fakes.py` holds the doubles. `FakeBatfish` keeps networks and
  snapshots, returns canned answers, and records every call in `.calls`.
  `FakeAnswer` imitates an answer (`frame()`, `rows`, item access). The fake
  session checks names with pyBatfish's own validator, as the real one does.
- `tests/conftest.py` provides `bf_session_state`, a plain stand-in for
  `st.session_state`, for testing helpers outside a page.
- Some things `AppTest` cannot do, so the tests replace them: editing a table
  (`st.data_editor`), and fragment-only reruns. Look at `test_page_net_setup.py`
  and `test_page_questions.py` for how.

**Check that a new test can fail.** After writing a test, break the code it
covers on purpose and confirm the test fails. A test that passes either way
checks nothing.

## Integration tests

These need a running Batfish server and use Batfish's own example network (kept
in `tests/integration/networks/`). Most checks ask Batfish the same question
directly and require Bat-Q's answer to agree, instead of hard-coding results.

```bash
docker run --name batfish -d -p 9996:9996 -p 9997:9997 batfish/allinone
python -m pytest tests/integration -m integration
```

Set `BATFISH_SERVER` if Batfish is not on `localhost`. Without a server the
tests are skipped; `BATFISH_INTEGRATION=1` turns that into an error. Each run
uses a throw-away network that is deleted afterwards. See
`tests/integration/README.md` for details and for what to do if a test seems to
hang.

## Continuous integration

Two GitHub Actions workflows live in `.github/workflows/`:

- `tests.yml` runs the unit tests with Python 3.11 and 3.12 on every push to
  `main` and on pull requests.
- `integration.yml` starts a Batfish container and runs the integration tests on
  pushes, pull requests, by hand, and every Monday (to notice changes in
  Batfish or pyBatfish).
