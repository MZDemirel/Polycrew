# Changelog

Decision notes (in Turkish) are in [`docs/decisions/`](docs/decisions/); the number in brackets points to one.

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
