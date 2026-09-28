# Calibration Anchors

Read when a score is borderline, confidence is low, or two versions are being
compared. Match the file to the closest anchor, then adjust only when evidence
clearly supports it.

## Anchors

- 10 (overall 9.5-10, confidence high): result and a testable done line up
  front; description gives what, when, and NOT-for neighbors; each rule once;
  hard limits short and explicit; nothing model-known; well under 500 lines with
  read-when references; neutral base with section-patched overlays.
- 8 (overall 7.5-8): the same shape with one weaker area, such as a few
  model-known lines, one duplicated rule, or a reference without a read-when
  condition.
- 6 (overall 5.5-6): the task is doable, but a long step list prescribes the
  path, verification or scope repeats in several places, or preferences are
  written as prohibitions. Results vary by run.
- 4 (overall 3.5-4): the result is implied, rules conflict or repeat heavily,
  and routing overlaps a neighbor.
- 2 (overall 1-2): persona or motivational prose, or unsafe and contradictory
  instructions dominate. If the file is not agent-facing, do not score it.

A shorter file that states the outcome beats a longer one that adds output
templates, failure catalogs, or verification sections the task does not need.

## Pairwise rerank

When comparing two files or two versions:

- Apply caps to both first; a polished but unsafe file does not win.
- Compare each dimension as A better, B better, or tie.
- When totals are within 0.5 and evidence is similar, report a tie.
