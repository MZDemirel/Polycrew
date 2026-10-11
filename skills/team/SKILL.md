---
name: team
description: Do a phase with an agent team — the main session becomes the project manager (PM), splits the phase into independent streams, starts a lead per stream, the leads run developer, artist and reviewer workers, and the PM merges. Use when the user says "do it with the team", "agent team", "let's work in parallel", "split it into streams" (Turkish: "takımla yap", "ajan takımı", "paralel çalışalım", "akışlara böl").
---

# Team

You are the **PM** (the main session). The team structure and its background: the plugin's `docs/decisions/0001-takim-denemesi.md`.

```
user ── PM (main session: splits, merges, asks the user)
         ├── lead A ── developer (worktree) · artist · reviewer
         └── lead B ── developer (worktree) · artist · reviewer
```

## 0. Roster (by difficulty)
- Give every item a difficulty: **E** easy, **M** medium, **H** hard. Before building the roster run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/team/roster.py" suggest --role <role> --field <field> --difficulty <E|M|H>`. Scores fade with age (half-life 30 days, `--half-life`), so the ranking follows recent runs; `Eff. n` is how much data is still counted. `roster.md` (next to this file) stays as the prior table; when data is thin ("little data"), `roster.md` wins. Show item → difficulty → worker to the user in the plan.
- **Claude quota is kept for the PM, the artist, design and H-level code;** the rest goes to external workers first (the `external-agent` skill: Codex, agy).
- **Default is a small team:** PM → one developer (+ one helper). A lead only for truly parallel, large streams. At most 2 Claude agents; at most 2–3 developers running tests (machine).
- **The PM hands out decision numbers;** workers do not change them.
- **Quota:** before building the roster run `external-agent.sh quota` (5-hour and weekly quota of Codex and agy). If the Codex window is past 60%, medium jobs go to Gemini; for Claude quota the user checks `/usage`.

Visibility: when work starts, open the live page with `/watch` and give the user its address. After every job the PM writes `events.py score <id> <1-5> --worker ... --role ... --field ... --difficulty ... "<reason>"` (see the `watch` skill).

## 1. Split (in plan mode)
- Split the phase's items into streams **by file set**: two streams must not change the same file. If you cannot separate them, put them in sequence or make one stream.
- For each stream: items (in order, one commit each), "Done when" criteria, files it will touch, dependencies between streams (for example "B2 uses A3's light direction; do it with the default first").
- Get the user's approval for the plan.

## 2. Start
- External worker: the `external-agent` skill (you prepare the worktree: untracked assets, dependencies). Write the file boundary into the task: "Do not touch PLAN, the notes file or decision notes; the PM writes those."
- One **lead** per stream: `Agent(subagent_type: "polycrew:lead", run_in_background: true)`. If the role is not loaded, use `general-purpose` and put the content of `agents/lead.md` into the prompt.
- Into the lead's prompt: the stream and its items, decision notes, project root, the symlink command for untracked assets, machine limits, **the other leads' agentIds** (send them with `SendMessage` after starting), and "report to the PM with `SendMessage(to: "main")`".
- For short jobs independent of the streams (a report, say) you may start a worker directly.
- **Limit:** at most 2–3 developers at once (depends on the machine; check the project's notes). The full test suite runs only in the PM, one at a time, in the background.

## 3. Run
- Read the leads' messages. For a question: if you can decide, decide and tell the lead; if it is the user's call, collect such questions and ask them together with `AskUserQuestion`. Do not keep leads waiting.
- Tell the user briefly at every merge: what was merged, the measurement, the image.

## 4. Merge (PM only)
When an item is ready (lead's report, reviewer says "no blocker", artist's approval). Every commit, merge commits included, follows the fixed git rules: `${CLAUDE_PLUGIN_ROOT}/rules/git.md`.
1. Look at the image yourself too; verify the measurement.
2. `git -C <worktree> rebase main` (on conflict, hand it back to the lead), then in the main checkout `git merge --ff-only <branch>`.
3. Run the full tests, lint and type check in the background. If red, do not revert `main`; give the fix to the lead.
4. When the branch's work is done, `git worktree remove <path>`. **The branch stays;** merged branches are not deleted (only if the user asks separately and explicitly).

## 5. Close
- Write open worktrees and branches (`git worktree list`) into the notes file (`NEXT_SESSION.md`, or `SONRAKI_OTURUM.md` where the project uses that) with where the unfinished work stands; if a limit or an error cuts the session short, do this first.
- Summarize the leads' final reports; check that decision notes were written.
- If something about how the team worked is worth keeping (problems, permission prompts, durations), write it into the project's notes file or a decision note.
- `/session-end`.
