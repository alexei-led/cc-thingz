# Doc Set

Use this reference to decide which doc owns which fact, and what each doc
contains. The result is a doc set where each file has one reader, one job, and
no copy of another file's facts.

## Roles

- **README (front page)**: for a person who decides whether to try the project.
  Answers, in this order: what it is, why use it, how it works, how to install
  it. Link to everything else.
- **User guide**: for a user after the install. Tasks in the order of use:
  check the setup, daily use, read the outputs, override defaults, update,
  stop or uninstall, troubleshoot.
- **Configuration or API reference**: for a user who changes behavior. Each
  key, parameter, or endpoint with its default and meaning. Values come from
  the source, not from memory.
- **Architecture**: for a contributor. How the system works inside: context,
  flows, decision logic, state, modules, failure handling, security, known
  limits. No history.
- **Evaluation or benchmarks**: for a skeptical reader. The method, the data
  window, the tables behind each chart, and the limits.
- **Contributing or develop**: build, test, and release commands. If the repo
  has no CONTRIBUTING file, a short section at the end of the architecture doc
  is enough.
- **Changelog and release notes**: history, including replaced designs and
  version-specific upgrade steps.

## Ownership map

Write this map before an overhaul. It prevents duplicate facts and broken links.

1. List the facts that the current docs state, for example install steps,
   default values, tier or mode lists, output formats, and update steps.
2. For each fact, pick the owner doc by its reader.
3. In every other doc, replace the copy with a link or a one-line pointer.
4. After the edits, run `<skill-dir>/scripts/check-links.py` on the full doc
   set.

Example map:

```text
fact                          owner                  others
install steps                 README#install         user guide links to it
update steps                  user-guide#update      README: none
tier list with purpose        README#tiers           architecture links to it
tier to model mapping         configuration#routes   architecture links to it
defaults of each key          configuration          nowhere else
status line format            user-guide             architecture: endpoint only
log retention                 configuration#data     architecture links to it
```

## README front page

Answer the reader's two questions first: what is it, and what is in it for me.

```markdown
# <project>

<badges>

**<one sentence: what it does, for whom>**

<two or three sentences: the problem, and how the project removes it>

> **Status:** <experimental | beta | stable>. <one sentence on maturity>

## Why use it

- **<measured benefit>.** <fact with a number and its baseline>
- **<second benefit>.** <fact>
- **<what the user no longer does>.** <fact>

<one chart or one diagram that proves the main claim; link to the method>

## How it works

<one diagram of the main flow; three to five sentences>

## Install

<requirements in one line; numbered steps; how to confirm that it works>

## Documentation

- [User guide](docs/user-guide.md): <tasks it covers>
- [Configuration](docs/configuration.md): <what it references>
- [Architecture](docs/architecture.md): <what it explains>
```

Leave these out of the front page: update steps, develop commands, full
configuration, troubleshooting, and history.

## User guide outline

- Check the setup: three steps that prove the install works.
- A short example of normal use, with a diagram if the behavior changes over
  time.
- How to read each output that the user sees, with an annotated sample.
- How to override or pin a default.
- Update, and stop or uninstall.
- Troubleshooting as a table: symptom, cause, fix.

## Architecture outline

- System context diagram and three to five bullets on what crosses each
  boundary.
- Main flow as a sequence diagram.
- Decision logic as a flowchart with one box for each outcome.
- State and lifecycle as state diagrams.
- Modules: a dependency diagram and one line for each module.
- Failure handling as a table: failure, behavior.
- Security and privacy, known limits.

## Faults to remove

- Stories and decision dates in design docs.
- The same table or list in more than one doc.
- Update, develop, or full configuration content on the front page.
- Troubleshooting entries for versions that nobody runs.
- Promotional adjectives in place of measured facts.
- Headings that do not match their content.
