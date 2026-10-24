# Example network

`live/` and `candidate/` are the example campus network (AS1, AS2, AS3 plus two
hosts) from the Batfish repository, `networks/example`, release v2026.08.27:
https://github.com/batfish/batfish/tree/master/networks/example

- `live` is the configuration deployed in the network.
- `candidate` is a candidate change: it adds ACLs, and one access-group is
  applied in the wrong direction.

The files are unchanged and used only as test data. Batfish is licensed under
the Apache License 2.0 (copy in `LICENSE`).
