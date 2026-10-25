# Assertions

An **assertion** is a statement about your network that must be true, for
example "there are no forwarding loops" or "web traffic from the border router
reaches the server". Bat-Q checks assertions against the active snapshot,
reports whether each one passed, failed or could not be evaluated, and can
produce a report of the results.

Assertions use Batfish's own checks (the `assert_*` functions of
[pyBatfish](https://pybatfish.readthedocs.io/)), plus a few that Bat-Q adds for
the number of rows a question returns. Use them to turn a network design or a
change plan into a repeatable list of yes/no checks.

## Quick start

1. On **Snapshots & Setup**, upload a snapshot and choose it as the **Main
   Snapshot**. Assertions are always checked against this snapshot.
2. Open **Assertions** (under *Analysis & Verification*) and use **Add
   assertion** to pick a check, fill in its parameters and click **Add**.
3. Click **Run all** (or the play button on one assertion).
4. Read the results. Click a failed or errored assertion's *details* to see why.
5. Save the list with **Save assertions to YAML** in the sidebar, so you can
   load it again later or share it.
6. Open **Assertion Reporting** (under *Reporting*) to download the HTML or
   Excel report.

## The Assertions page

**Add assertion / Edit assertion.** Choose the assertion from the list (grouped
by topic), optionally give it a *name* and *description*, and fill in its
parameters. Required parameters are marked as such; the others may be left
empty. Assertions that check the answer of a question also ask you to choose
the question and, if it has any, its parameters, exactly as on the Questions
page. Click **Add**, or **Update** when editing.

**The list.** Each assertion shows its status, name, description, what it
checks, and these buttons:

| Button | Does |
|---|---|
| play | runs this assertion only |
| pencil | loads it into the form for editing |
| up / down arrows | change its position (the order of the list and of the report) |
| trash can | deletes it |

**Run all** runs every assertion in order. **Remove all** empties the list.
Above the list, counters show how many assertions passed, failed, ended in an
error, or have not been run. *Results table* shows the same in a table.

### Results

| Status | Meaning |
|---|---|
| ✅ **Passed** | The assertion holds. |
| ❌ **Failed** | The assertion does not hold. The details show Batfish's message and, for assertions on a question's answer, the rows it looked at. |
| ⚠️ **Error** | The assertion could not be evaluated, so it is **neither passed nor failed**. For example, the question could not be run, a device or VRF was not found, or a parameter was invalid. The details show the reason. |
| ⏺️ **Not run** | Not run yet on this snapshot. |

An error is never counted as a pass. This matters most for "absent" checks:
Batfish itself reports success when the device you named does not exist (a
typo), while Bat-Q reports an error.

Results belong to a snapshot and are kept while you work: they are dropped when
you edit or delete the assertion, delete the snapshot, or switch network, and
they follow a snapshot that you rename. The assertion list and the results live
in your browser session, so **save the list to YAML** to keep it.

## Available assertions

An asterisk marks a required parameter. Where a parameter is a device, filter or
location, Bat-Q accepts the same specifiers as Batfish (names, comma-separated
names, or `/regular expressions/`); see the
[Batfish specifiers documentation](https://batfish.readthedocs.io/en/latest/specifiers.html).

### Snapshot checks

| Assertion | Type name | Checks that | Parameters |
|---|---|---|---|
| No undefined references | `assert_no_undefined_references` | No configuration refers to a structure (ACL, route-map, ...) that is not defined. | none |
| No forwarding loops | `assert_no_forwarding_loops` | No forwarding loops exist in the snapshot. | none |
| No unestablished BGP sessions | `assert_no_unestablished_bgp_sessions` | No BGP session is compatible but not established. | `nodes` (node specifier), `remote_nodes` (node specifier) |
| No incompatible BGP sessions | `assert_no_incompatible_bgp_sessions` | No BGP sessions have incompatible settings. | `nodes` (node specifier), `remote_nodes` (node specifier), `status` (text) |
| No incompatible OSPF sessions | `assert_no_incompatible_ospf_sessions` | No OSPF session is incompatible or unestablished. | `nodes` (node specifier), `remote_nodes` (node specifier) |
| No duplicate router IDs | `assert_no_duplicate_router_ids` | No two routers share a router ID for the checked protocols. | `nodes` (node specifier), `protocols` (list), `ignore_same_node` (true/false) |

### Filters

| Assertion | Type name | Checks that | Parameters |
|---|---|---|---|
| Filter has no unreachable lines | `assert_filter_has_no_unreachable_lines` | No line in the selected filters is shadowed by earlier lines. | `filters`* (filter specifier) |
| Filter permits flows | `assert_filter_permits` | The selected filters permit the described flows. | `filters`* (filter specifier), `headers`* (header fields), `startLocation` (start location) |
| Filter denies flows | `assert_filter_denies` | The selected filters deny the described flows. | `filters`* (filter specifier), `headers`* (header fields), `startLocation` (start location) |

### Reachability

| Assertion | Type name | Checks that | Parameters |
|---|---|---|---|
| Flows succeed | `assert_flows_succeed` | The described flows succeed. | `startLocation`* (start location), `headers`* (header fields) |
| Flows fail | `assert_flows_fail` | The described flows fail. | `startLocation`* (start location), `headers`* (header fields) |

### Question results

| Assertion | Type name | Checks that | Parameters |
|---|---|---|---|
| Question returns no rows | `assert_zero_results` | The selected question returns an empty answer. | a question (and its parameters) |
| Question returns exactly N rows | `assert_num_results` | The selected question returns exactly N rows. | a question (and its parameters); `num`* (whole number) |
| Question returns at least N rows | `batq_min_results` | The selected question returns at least N rows (N defaults to 1). | a question (and its parameters); `num` (whole number) |

### Routing

| Assertion | Type name | Checks that | Parameters |
|---|---|---|---|
| Route is present | `assert_has_route` | A route matching the description is in the node's RIB. | `expected_route`* (route columns), `node`* (text), `vrf` (text); Bat-Q runs the `routes` question for you |
| Route is absent | `assert_has_no_route` | No route matching the description is in the node's RIB. | `expected_route`* (route columns), `node`* (text), `vrf` (text); Bat-Q runs the `routes` question for you |

## Notes on parameters

**Flow and filter checks.** *Flows succeed* passes when none of the described
flows fails; *Flows fail* passes when none of them succeeds. If the description
covers a mix of flows that succeed and flows that fail, both assertions fail.
The same holds for *Filter permits flows* and *Filter denies flows*. Describe the
flows precisely enough (source, destination, application) to get a clear answer.

**Headers.** `headers` is a dictionary of header fields that describe the flows.
The accepted fields are `srcIps`, `dstIps`, `srcPorts`, `dstPorts`,
`ipProtocols`, `applications`, `icmpCodes`, `icmpTypes`, `ecns`, `dscps`,
`packetLengths`, `fragmentOffsets` and `tcpFlags`. A misspelled field is
rejected when you add the assertion or load a file. In the form, enter it as
`{'dstIps': '2.128.0.101', 'applications': ['HTTP']}`.

**Questions.** The three *Question returns ...* assertions run a Bat-Q question
(any question from the Questions page, with its parameters) on the snapshot and
count the rows of the answer. They are useful for "this list must be empty"
rules such as *Unused Structures*, or "exactly two BGP edges" checks. If the
question itself cannot be run, the result is an error.

**Routes.** *Route is present* and *Route is absent* look at the routes of one
`node` in one `vrf` (default: `default`). Bat-Q asks Batfish only for that
node's routes in that VRF. `expected_route` lists the columns of the *Routes*
answer that the route must match, for example
`{'Network': '10.0.0.0/24', 'Protocol': 'bgp'}`. Only the columns you list are
compared, and values must match exactly. An empty `expected_route` is rejected,
because it would match any route. If the node or VRF does not exist, the result
is an error and never a pass.

## Assertion files (YAML)

Assertions are saved to and loaded from a YAML file. This file is separate from
the questions file of the Questions page.

```yaml
version: 1
assertions:
  - type: assert_no_forwarding_loops
    name: Core is loop free
    description: A loop in the core would take down both sites.
  - type: assert_no_undefined_references
  - type: assert_zero_results
    name: No unused structures
    question:
      fun: unusedStructures
  - type: assert_num_results
    question:
      fun: bgpEdges
      options:
        nodes: as1border1,as1border2
    params:
      num: 2
  - type: assert_flows_succeed
    description: Web traffic from as1border1 reaches host1.
    params:
      startLocation: as1border1
      headers:
        dstIps: 2.128.0.101
        applications: [HTTP]
  - type: assert_has_route
    params:
      node: as1border1
      expected_route:   # placeholder values: copy them from your own Routes answer
        Network: 1.0.1.0/24
        Protocol: bgp
```

The file has a `version` (currently `1`) and a list of `assertions`. Each
assertion has these keys:

| Key | Required | Meaning |
|---|---|---|
| `type` | yes | The type name from the tables above, such as `assert_no_forwarding_loops`. |
| `name` | no | A label shown in the list and the reports. |
| `description` | no | A longer explanation, shown in the list and the reports. |
| `params` | when the assertion has required parameters | The parameters of the assertion, by name. Only the parameters listed for that type are accepted. |
| `question` | for the *Question returns ...* assertions, and only for them | `fun` is the Batfish question's function name (as used on the Questions page, for example `bgpEdges`). `options` holds that question's parameters. |
| `scope` | no | Reserved. Leave it out: every assertion is currently checked against the active snapshot. |

When you load a file with **Load assertions** in the sidebar:

- the current list and its results are **replaced** by the file's contents;
- the file is checked as a whole. If anything is wrong (an unknown type or
  question, a missing or misspelled parameter, a wrongly typed value, an
  unsupported `version`), **nothing is loaded** and every problem is listed with
  the number of the assertion it belongs to;
- the same file can be loaded again later.

**Save assertions to YAML** downloads the current list as `assertions.yaml`.
Internal ids and results are not saved.

## Assertion reports

**Assertion Reporting** (under *Reporting*) builds a report of the last results
for the active snapshot. It is separate from **Analysis Reporting**, which is a
collection of question answers. Run the assertions first. Assertions that have
not been run are listed as *Not run*.

The report starts with an overall verdict:

| Verdict | When |
|---|---|
| **FAILED** | at least one assertion failed |
| **INCONCLUSIVE** | nothing failed, but some assertions ended in an error or were not run |
| **PASSED** | every assertion was run and passed |

It then lists every assertion with its status, what it checks, its runtime and
when it ran, followed by a section for each failed or errored assertion with
Batfish's message and the rows it looked at.

Two downloads are offered in the sidebar:

- **HTML report**: a single page you can open, print or e-mail.
- **Spreadsheet (.xlsx)**: a *Summary* sheet (verdict, counts, one filterable
  row per assertion) and one sheet with the rows of each failed assertion.

## Limits to know about

- Assertions are always checked against the **active snapshot** (the Main
  Snapshot chosen on *Snapshots & Setup*), not the alternate one or a failure
  fork.
- Only hard checks are available: an assertion either holds or it does not
  (Batfish's "soft" warning-only mode is not used).
- Results are not stored in a file. They belong to the browser session.

## Troubleshooting

**A page seems to hang for several minutes after running a question or an
assertion.** If Batfish itself rejects a question (for example a node specifier
with an unbalanced `/(`), the pyBatfish client retries the request with longer
and longer pauses, for about seven minutes, before it reports an error. Correct
the parameter and run it again, or restart Bat-Q if you do not want to wait.

**An assertion ends in an error.** Open its *details*. Typical causes are a
device, VRF or filter name that does not exist in the snapshot, or a question
that could not be run.

**"File ... is not recognized" when loading a snapshot.** This concerns
snapshots, not assertions; see *Getting started*.
