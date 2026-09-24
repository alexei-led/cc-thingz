# Style

Use this reference for the language of human docs. It is a practical subset of
ASD-STE100 Simplified Technical English. It makes each sentence readable in one
pass, also for readers who are not native English speakers. If a
`simple-english` skill is available and the user asks for strict STE, use that
skill.

## Before writing

- Pick one verb for each recurring concept, for example "check", and one noun,
  for example "configuration". Do not rotate synonyms.
- Decide for each passage: procedure (tells the reader what to do) or
  description (explains what a thing is or does).

## Rules

- Procedures: imperative verbs, 20 words or fewer for each sentence, one
  action for each sentence. Put a condition first: "If the build fails, read
  the log."
- Descriptions: 25 words or fewer for each sentence, one new fact for each
  sentence, six sentences or fewer for each paragraph.
- Active voice. Simple present, past, or future.
- Use the modals "must", "can", and "will". Replace "should" with "must" for a
  requirement, or state a recommendation as a fact. Replace "may", "might",
  and "could" with "can".
- No contractions. Keep articles and the word "that".
- No semicolons. Write two sentences.
- No filler: leverage, utilize, seamlessly, robust, powerful, simply, just,
  easily, "in order to", "it is worth noting".
- No Latin abbreviations. Write "for example" and "that is", and name the
  items of a list in full.
- Persuade with facts: a number with its baseline, not an adjective.
- Leave code, commands, identifiers, file paths, and quoted output unchanged.

## Example

Before:

```text
You'll want to grab the API key from the dashboard before configuring the
client, which you can easily do under Settings, since otherwise requests may
fail.
```

After:

```text
Get the API key from the dashboard, under Settings. Then configure the client
with this key. Without the key, requests fail.
```

## Self-check

- Run `python3 <skill-dir>/scripts/prose-lint.py <files>`. It flags banned modals,
  contractions, semicolons, filler words, and long sentences.
- Read the three longest sentences again, and split them if possible.
- Make sure that each "if" and "when" starts its sentence in procedures.
