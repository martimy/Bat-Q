# Integration tests

These tests run Bat-Q's code against a **real Batfish server**, using Batfish's
own example network (`networks/`, see `NOTICE.md`). The unit tests in `tests/`
use fakes and never need a server.

## Running them

```bash
# 1. start Batfish (the same image Bat-Q's README uses; any running Batfish works)
docker run --name batfish -d -p 9996:9996 -p 9997:9997 batfish/allinone

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

## If a test seems to hang

pybatfish waits a long time before giving up on an unresponsive Batfish: each
request may wait 30 s and is retried with growing pauses, roughly five minutes
or more in total. A slow or stuck server therefore looks like a frozen test.

1. Run with names and a stack dump: `python -m pytest tests/integration -v -x`
   (`pytest.ini` already prints every thread's stack after 180 s).
2. Look at the server: `docker stats --no-stream batfish` and
   `docker logs --tail 80 batfish`. A container near its memory limit, or one
   that has restarted, explains stalls after the heavier flow and filter checks.
3. Re-run the stuck test alone. If it passes at once, the server had become slow
   during the earlier tests rather than the test being wrong.
