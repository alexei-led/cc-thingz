# Visuals

Use this reference for Mermaid diagrams, charts, and small annotated visuals in
human docs. A visual earns its place when it answers a question faster than
prose. Every visual needs a render check, because a diagram that parses can
still be hard to read.

## Pick the form by the question

- What talks to what: `flowchart LR` with the main component in the middle.
  Mark remote or external nodes by class and label, for example
  "(remote)". Example: `assets/examples/system-context.mmd`.
- What happens in order, across components: `sequenceDiagram`. Show internal
  steps as `Note over`, not as self-messages. Example:
  `assets/examples/request-flow.mmd`.
- How a decision is made: `flowchart TD` with one box for each outcome, labeled
  with the name that users see in logs or status. Example:
  `assets/examples/decision-outcomes.mmd`.
- How a thing changes state: `stateDiagram-v2`. Example:
  `assets/examples/lifecycle.mmd`.
- A pipeline of steps: `flowchart LR` with one class. Example:
  `assets/examples/pipeline.mmd`.
- A small UI element, such as a status line: an annotated `text` block.
- Reference data: a table. Troubleshooting: a symptom, cause, fix table.
- A measured comparison: a chart, as a static SVG.

## Mermaid faults

Check the rendered image for each fault. After the first render, add any new
fault that you see to this list for the rest of the task.

- An edge that crosses a box, or labels that overlap. Fix: merge a request and
  its response into one two-way edge (`A <-->|label| B`), or change the
  direction of the whole diagram.
- An arrow that seems to connect the wrong nodes, because it passes behind
  another node. Fix: remove the subgraph around the target nodes, so each
  edge gets its own row.
- A layout that depends on a subgraph `direction`. Mermaid ignores that
  direction when a node in the subgraph links outside it. Group by class and
  label instead, or keep all links of the subgraph inside it.
- A shared end node, such as one "Stay" box, that pulls long edges across
  the diagram. Fix: one small box for each outcome.
- The default yellow subgraph fill. Fix:
  `style <id> fill:#f8fafc,stroke:#94a3b8,color:#0f172a`.
- Color as the only signal. Fix: put the meaning in the node text, and add one
  legend sentence under the diagram.
- A color that means different things in different diagrams of the same doc
  set. Fix: one class palette for the doc set.
- A label longer than about five words on one line. Fix: `<br/>` breaks.
- HTML entities such as `&lt;` in labels. They can render as literal text.
- More than about 15 nodes. Fix: split the diagram, or move detail to a table.

## Class palette

One palette keeps meaning consistent across diagrams. The fills are light, and
the text color is explicit, so the nodes read on light and dark pages.

```text
classDef core  fill:#ecfdf5,stroke:#059669,color:#064e3b   main component
classDef ext   fill:#eef2ff,stroke:#6366f1,color:#1e1b4b   remote service
classDef store fill:#fff7ed,stroke:#ea580c,color:#431407   storage, I/O
classDef stay  fill:#f1f5f9,stroke:#64748b,color:#0f172a   no change
classDef up    fill:#fef3c7,stroke:#d97706,color:#451a03   increase, escalation
classDef down  fill:#e0f2fe,stroke:#0284c7,color:#082f49   decrease
```

## Render and look

1. Run `bash <skill-dir>/scripts/render-mermaid.sh <doc.md>`. It writes one PNG for each
   Mermaid block and reports each block that fails to parse.
2. Open each PNG and check the fault list.
3. Fix, render again, and look again.

If `mmdc` is not installed, the script says so. Then report that the diagrams
are not render-checked. Keep them small, with one direction and few crossings.

## Charts

- One message for each chart. Use one axis for each panel. Never use a dual
  axis.
- Put the claim in the title. Put the sample size and the data window in the
  subtitle.
- Direct labels on the bars. Text uses ink colors, not series colors.
- The product in one accent color, baselines in grey.
- A footnote with the key assumption, for example "lower bound", and a link to
  the method.
- Add `<title>` and `<desc>` for screen readers.
- Support dark mode with `@media (prefers-color-scheme: dark)` inside the SVG
  `<style>`, with its own background and ink colors.
- Check contrast: 3:1 for marks, 4.5:1 for text.
- Render with `rsvg-convert` and look at both themes. To preview dark mode,
  copy the SVG with the dark rules moved out of the media query.
- Put a table of the chart data in the evaluation doc.
- If a data-visualization skill is available, use it for palettes and checks.

## Small visuals

Annotate a one-line output with a `text` block:

```text
app ▸ model-name · high · upgrade
      │            │      └─ reason for the decision
      │            └─ effort
      └─ model of the last turn
```

Group a long table of codes by outcome, for example "changed" and "stayed",
with one table for each group.
