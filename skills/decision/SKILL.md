---
name: decision
description: Write an important decision as a short numbered note under docs/decisions/. Use when an architecture, format, contract or behavior choice is made, when the user says "write this down as a decision" (Turkish: "bunu karar olarak yaz"), or when one option is dropped in favor of another.
---

# Decision note

1. Next number: `ls docs/decisions/ | grep -E '^[0-9]{4}-' | sort | tail -1` plus 1, four digits.
2. File name: `NNNN-short-name.md` (ASCII, hyphens, in the project's language). Images go to `docs/decisions/img/NNNN-*.png`.
3. Template. Write the headings and the text in the project's language (`CLAUDE.md`); in a project that already has decision notes, follow their headings.

```markdown
# NNNN: Title

- **Date:** YYYY-MM-DD
- **Status:** Accepted | Under review | Superseded (→ NNNN). Which decision it completes or replaces.

## Context

Why it was needed: the user's words, a bug, a measurement.

## Decisions

Numbered; what and why for each. Values and units of constants.

### Tried and dropped

What was tried and why it did not work (with numbers).

## Measurements

Before/after table; images.

## Tests

Which tests guard what.

## Still open

Known gaps; link to the next phase.
```

4. Keep it short: someone re-reading the note should find the answer to "why is it like this". Do not copy code; give file and function names.
5. Add the number to the related `PLAN.md` item and to the notes file (`NEXT_SESSION.md`, or `SONRAKI_OTURUM.md` where the project uses that).
