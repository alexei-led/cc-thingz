# Planning rules (Step 3)

## Vertical-slice rules

Tasks should be tracer bullets, not horizontal layers.

- Each task delivers a narrow but complete path through the system.
- A completed task is demoable or independently verifiable.
- Prefer many thin slices over one thick slice.
- Avoid "schema task" → "API task" → "UI task" unless one layer is the whole product.
- Include tests in the same slice as the behavior.

If a slice needs a human decision, external access, or manual validation before completion, capture it as a blocker or open question. Don't create a separate task taxonomy for it.

## Task sizing

- **S** — 1–2 files, 1–3 acceptance criteria → combine with a related task
- **M** — 3–5 files, 3–5 criteria → **target size**
- **L** — 5+ files, 5+ criteria → split into M tasks

M is ideal: meaningful progress, fits one session.

## Dependency rules

- Tasks that must complete before others → `blocked-by`
- Minimize file overlap for parallel work
- Sequential S tasks → combine into M

## Plan mental model

Before writing, answer:

1. What vertical slices are needed?
2. What order (dependencies)?
3. What size is each task?
4. Which can run in parallel?
5. Which unresolved questions block implementation?
