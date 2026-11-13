# Changelog

Decision notes (in Turkish) are in [`docs/decisions/`](docs/decisions/); the number in brackets points to one.

## 0.13.0 (2026-11-13)

[0019]

- **Claude quota by itself in the desktop app.** The app keeps plan usage samples (5-hour and week, every 15 minutes); the session start hook, the agent hooks, the watch page and `external-agent.sh quota` copy the newest one to the log when it changed. A reset time recorded earlier is carried over; a sample older than a known reset is dropped. It is an undocumented file of the app: when it is missing or unreadable nothing is written and the status line or the PM still works. `/doctor` shows where the Claude reading came from. Per-model weekly limits still come from the PM (`--model-week`).
- When several sources write the same quota bucket, the newest measurement wins (the page used to take the last event in the log).
- **External workers:** the exact prompt is saved as `istem.md`. A failed run that stopped on a quota or rate limit exits 5, one stopped by agy's permission rules exits 6 (the tool's own code stays in the event as `arac_cikis`; a timeout stays 124). Only the tool's error signal is checked, never the worker's answer. Denied agy actions are listed even after a successful run. A read-only run that changed files gets a warning. agy in read mode is told not to wait for approval. `{"response": null}` from agy no longer crashes.
- agy worker names keep the effort in the model name (`agy/gemini-4-argon-high`); `agy/X/high` is read as `agy/X-high`, so one worker is one row and one timeline lane.
- `events.py score` refuses a score outside 1–5 and non-finite or negative `--quota`, `--duration`, `--fixes`. A resumed Claude agent's duration runs from its first start to its last stop.
- `Try` no longer suggests a worker that scored below 3 in that role and field.
- Fixed during review: the watch page crashed when a job event followed a quota event (introduced in this release, never on `main`).

## 0.12.1 (2026-11-13)

Quota readings are now right and on time. [0018]

- **Stale readings show as stale everywhere.** The watch page, `roster.py` and `/doctor` share one rule (`hooks/quota.py`): a reading is stale when its reset has passed, or when it is older than 5 hours (5-hour window) or a day (week). The page shows why. Before this, a four-day-old Claude reading (week 5%, really 32%) looked fresh on the page.
- **Claude quota on time:** the new optional status line `skills/watch/claude-statusline.py` records the plan's 5-hour and 7-day usage from Claude Code's status line input when it changes. Without it, `/session-start` and `/team` have the PM read the desktop usage tool (or `/usage`) and record it before assigning work, and `roster.py` notes a missing or stale Claude reading. `claude-quota.py --model-week Fable 23 <reset>` records a per-model weekly limit, which only affects workers of that model. Reset times in the past or beyond the window are refused.
- **Right bucket:** Argon workers are measured on agy's own Argon group (Gemini when agy reports none); a run's quota difference used to be measured on Gemini (0). Codex windows come from `window_minutes`; a bucket without a reset time is skipped instead of crashing. When Codex writes no new reading during a run, the difference stays empty instead of 0.
- **Times and unknowns:** agy reset times are shown in local time (they were UTC); a bucket that could not be read shows `?`, not 0%. A stale reading already under the limit still counts as `low quota` until its window resets.
- **Smaller event log:** an unchanged quota reading is not written again (at most every 30 minutes), and the page refreshes Codex and agy every 5 minutes instead of every minute. Quota events had been 73% of the log. Appending and trimming the log share a lock.
- The session start hook no longer risks exit 141 on a long first section.

## 0.12.0 (2026-11-12)

- **Watch page redesigned for a half-width pane.** [0015] The timeline has one lane per worker (the role for a Claude agent, the model for an external worker) instead of one row per job; jobs that overlap stack inside the lane. Axis labels are laid out for the measured width: none is cut at the edge and none touches its neighbour, and daily ticks fall on local midnight. The axis ends at the last job when nothing is running. With 177 jobs the timeline went from 4240 px to 398 px at 560 px wide.
- The five counter boxes are one status line; the job table is a list that never scrolls sideways (newest 40, a button for the rest); the agent map is an indented tree at every width, folded until a lead gives it depth; "Running now" shows only while something runs. Breakpoints follow the page's own width (container queries).
- Office: a worker at a desk carries a short label from its model (`sol`, `flash`; numbered when several share one); a read-only worker wears glasses, a writer holds a pencil. [0015]
- Fixed: the static report showed the time-window buttons it was meant to hide; the page read agy's reset time as local time (it is UTC).
- **New skill `/doctor`:** a read-only setup check (tools on PATH, project files, event log, quota readings, agy permissions, shell syntax of the plugin's scripts). It prints `ok` / `warn` / `fail` lines, exits 1 on a failure, and changes nothing. [0017]
- **Quota-aware roster:** `roster.py suggest` and `summary` read the newest quota reading. A worker with under 20% left in the 5-hour window or under 10% left in the week drops to the end of its row and is marked `low quota`; it is not offered in `Try` either. A missing or stale reading changes nothing. `--no-quota`, `--quota-low-5h`, `--quota-low-week`. Quota events carry the exact reset time (`yenilenir_epoch`). [0017]
- **Pitfall candidates:** a score below 3 is also kept next to the event log, and `roster.py summary` lists the recent ones of the workers in the table. Hints only: they never change a ranking. [0017]
- `events.py score` prints a confirmation line; `roster.py --help` exits 0; `roster.py structure` says "Claude: little data" and lists the quota left per provider; `external-agent.sh quota` marks an old Codex reading `stale`. [0014]
- Draft decision on a shared memory for all workers (general and per project); no code yet. [0016]

## 0.11.0 (2026-10-19)

From the first real team run (Pixlender). [0014]

- **Privacy:** the watch page and the session report are filtered by project. The page takes `?project=<name>` and has a project selector; `watch.py report` keeps only the current folder's project (`--project`, `--all-projects`). Before this, a published report could carry another project's jobs and reports. The report's title names the project and the date, and its `lang` follows `--lang`.
- `external-agent.sh quota` no longer crashes on an exhausted agy bucket (missing `reset_time`). For agy the run is measured on the fullest window of the model's group, and `kota.json` names the group.
- A failed or timed-out run ends its `rapor.md` with the exit code and the last lines of the tool's error output.
- Parallel runs of the same tool: `kota.json` keeps the combined change (`ortak_fark`) and the overlapping runs; the score gets `kota_ortak`, which is not used as cost.
- `roster.py summary` ranks each row on all scores (faded by age); the window only sets the basis. One new score no longer pushes a well-measured worker off the table.
- Watch page: an old job that never finished no longer stretches the 12-hour timeline over days; axis labels show the day on spans over a day. agy jobs use the external worker color, Claude models on agy included.
- `/session-start` checks how far a worktree is behind its base branch; the "Try" worker may get the lightest M job when there is no E job. `/team`: the PM cannot edit a worker's worktree; run the tests a reviewer's suggestion touches before applying it.

## 0.10.0 (2026-10-19)

- **Privacy:** the event log only records projects that use the workflow (a `NEXT_SESSION.md` or `SONRAKI_OTURUM.md` in the project folder or above it). Before this, every subagent in every project was logged. `POLYCREW_WATCH_ALL=1` logs everything as before. [0013]
- The event log is trimmed to its newest half past 10 MB (`POLYCREW_EVENTS_MAX_MB`, `0` turns it off). [0013]
- `/session-start` opens the watch page once the plan includes team or external work; in the Claude desktop app it opens in the built-in browser pane. [0013]
- macOS: `external-agent.sh` works without GNU `timeout` (falls back to `gtimeout`, then Python), without `date +%N`, and with bash 3.2. Python 3.9 is the minimum. CI runs on macOS and on Python 3.9. [0013]

## 0.9.0 (2026-10-11)

- Watch page: a pixel office at the top (PM, Claude room, external workers' room, break room). [0012]
- `roster.py structure`: per role, Claude or an external worker, workers to avoid, whether a lead is used. Suggestions only. [0011]

## 0.8.0 (2026-10-11)

- `external-agent.sh` reads the tool's quota before and after each run; the difference (`kota.json`) and the duration go into the score by themselves. [0010]

## 0.7.0 (2026-10-11)

- A second score for the same job replaces the first. Near-equal workers (within 0.10) are ordered by cost or speed. Workers of a tool that is not installed are not suggested; `external-agent.sh` exits with 4 when the tool is missing. CI on GitHub Actions. [0009]

## 0.6.0 (2026-10-11)

- Scores fade with a 30-day half-life (`--half-life`). Claude workers are stored with their model version (`claude/developer/sonnet-5-5`). The summary table names a worker to try. [0008]

## 0.5.0 (2026-10-11)

- English names for commands, roles, scripts and options (`/session-start`, `/team`, `developer`, `external-agent.sh`…). New projects get `NEXT_SESSION.md`; `SONRAKI_OTURUM.md` keeps working. Old score data is mapped when read. [0007]

## 0.4.1 (2026-10-11)

- Fixed git rules in one file (`rules/git.md`): no tool signature in commits, merged branches are kept, workers never push. [0006]

## 0.4.0 (2026-10-03)

- Dynamic roster: a score ledger and `roster.py suggest` rank workers by role, field and difficulty. [0004]

## 0.3.0 (2026-10-02)

- First public version: session workflow, a measured multi-model team, external Codex and agy workers, live watch page in English and Turkish. [0002, 0003, 0005]
