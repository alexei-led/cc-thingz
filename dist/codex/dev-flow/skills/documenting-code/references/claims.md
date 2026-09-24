# Claims

Use this reference to check each statement in a doc against its source. Docs
that look correct often contain small false claims. Each class below produced
real errors in reviewed docs.

## Check against the source

Open the source line for each of these claims:

- Commands, flags, and their effect.
- Default values, limits, and thresholds. Compare tables of defaults with the
  configuration source, line by line.
- Names that users see: labels, status text, error text, file names, paths.
- Conditions: "X happens when Y". Check the full condition. Example of a real
  error: a doc said "the log rotates at start". The code rotates it at start
  only above 20 MB.
- Direction of a dependency or a data flow. Read the imports and the call site.
- Privacy and safety claims, for example "does not send files". Check what is
  sent, including user text that can contain the same data.
- Counts, versions, and percentages. Parts must add up to the whole after
  rounding. Use one decimal when whole numbers do not add up.

## Generate samples from the code

- Produce sample output (status lines, reports, error messages) by running the
  real code path: a script, a CLI command, or a test helper. Do not type it.
- Make the numbers in a sample consistent with the rules that the doc
  explains. A sample that shows a threshold must use the formula that computes
  the threshold.
- Mark a shortened sample with an ellipsis line (`…`).

## Measured claims

A number that sells the project (savings, speed, accuracy) needs a baseline
that a skeptical reader accepts.

- Name the baseline in words, for example "a user who keeps the strongest
  model for the whole session".
- Give both sides the same inputs. Remove only the effect under test.
- Reject a baseline that pays for the product's own overhead. That inflates
  the result.
- Reject a baseline with perfect conditions that the real alternative never
  gets. That hides the result.
- Fix a data window with a cutoff time, and give the sample size.
- If an assumption leans one way, say "lower bound" or "upper bound". If one
  assumption dominates the result, give the result at two or three values of
  it.
- Include the data that goes against the claim, for example a second setup
  where the effect is zero.
- Keep the analysis reproducible: a script path or a query.
- Put the method, the tables, and the limits in an evaluation doc. The front
  page gets one line, the chart, and a link.

## Unconfirmed claims

- If a claim cannot be checked, do not state it as fact.
- Report it as `unconfirmed: <claim> — looked in <places>`.
- Remove the claim when it is not necessary for the reader.
