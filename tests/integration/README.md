# Integration tests

These tests run Bat-Q's code against a **real Batfish server**, using Batfish's
own example network (`networks/`, see `NOTICE.md`). The unit tests in `tests/`
use fakes and never need a server.

## Running them

```bash
# 1. start Batfish (only port 9996 is needed with a current pybatfish)
docker run --name batfish -d -p 9996:9996 batfish/batfish

# 2. run the integration tests
python -m pytest tests/integration -m integration

# stop the server when done
docker rm -f batfish
```

- `BATFISH_SERVER=<host>` points the tests at another host (default `localhost`).
- Without a server the tests are **skipped**. Set `BATFISH_INTEGRATION=1` to make
  that an error instead (the CI job does).
- Run only the unit tests: `python -m pytest -m "not integration"`.
- Each run creates a network named `batq_it_<random>` and deletes it afterwards.
- Keep Batfish and pybatfish at matching versions (upgrade them together).

## How the checks work

Most checks do not hard-code Batfish's answers. They ask Batfish directly (the
"oracle") and require Bat-Q's verdict to agree, e.g. `assert_no_forwarding_loops`
must pass exactly when `detectLoops` returns no rows. This keeps the tests valid
when Batfish's modelling of the example network changes. Where a verdict is
certain by construction (`num` + 1 rows, a TEST-NET route, a missing node), the
tests assert it directly.
