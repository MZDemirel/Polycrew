---
name: session-end
description: Close a work session in an orderly way. Use when the user says "close the session", "that's it for today", "update the notes", "write NEXT_SESSION" (Turkish: "oturumu kapat", "bugünlük bu kadar", "notları güncelle"), or when the session's goal is done. Ticks checkboxes, completes decision notes, writes the notes file and a new start prompt, commits.
---

# Session end

Notes file: `NEXT_SESSION.md`. If the project has `SONRAKI_OTURUM.md` instead, use that one and do not rename it unless asked. Write in the language the project's `CLAUDE.md` sets; keep the section names the file already has.

## Steps

1. **State:** list this session's commits with `git status` and `git log`. If work is unfinished, tell the user; do not commit half-done code.
2. **Definition of done:** check the definition of done in `CLAUDE.md` one last time (tests, lint, type check; if there is visual output, was it looked at).
3. **PLAN.md:** tick the checkboxes of finished items and add the decision number to each. Write newly found work as items under the right phase.
4. **Decisions:** `/decision` for decisions made in this session but not yet written.
5. **Notes file** (keep its sections):
   - The "Last updated" date in the header and a one-line summary of the session.
   - **Where we left off:** what was done in this session (in order, with decision numbers and measurements); test count and duration; an up-to-date "Still open" list (delete what closed, add what is new); any new dependency.
   - **Next:** in priority order, each with "Job" and "Done when".
   - **Questions for the user** and **What you need to do** (images for the user to look at, servers to restart).
   - **Start prompt:** the text that opens the next session, with a `<feedback>` placeholder.
6. **Team report:** if subagents or external workers ran in this session, do the "Session report" step of the `watch` skill: produce the HTML with `watch.py report`, publish it as an Artifact, write the link into the notes file.
7. **Next session's roster:** if a score ledger exists (whether or not scores were written this session), run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/team/roster.py" summary --days 7` and write its table into the notes file under "Next session's roster", header row included, exactly as printed (replacing the old one). Below the table add the `prefer ...` and `Avoid: ...` lines of `roster.py structure`, if it prints any (they are suggestions for the user, not decisions). Do not edit the table by hand; if you disagree with a row, add one sentence below it (for example quota, or a known pitfall of that worker).
8. **Memory:** if something lasting and not specific to this repository was learned (a user preference, a machine limit), save it to memory; do not save what the repository already records.
9. **Commit:** in the project's commit format (`CLAUDE.md`) and under the fixed git rules (`${CLAUDE_PLUGIN_ROOT}/rules/git.md`). Do not push.

In the last message: the commits, what the user needs to do, and the start prompt.
