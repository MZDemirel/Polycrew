---
name: watch
description: Open the local page that shows the team's agents and external workers (Codex, Gemini) live; at the end of the session produce its shareable report. Use when the user says "show the agents", "who is doing what", "watch the team", "watch page", "session report" (Turkish: "agent'ları göster", "kim ne yapıyor", "takımı izle", "izleme sayfası", "oturum raporu"), or when work is handed out with /team.
---

# Watch

Events are collected in one log (`hooks/events.py`, decision `0003`): Claude subagents through hooks (`PreToolUse` Agent, `SubagentStart`, `SubagentStop`), external workers through `external-agent.sh` (started, finished, quota), scores from the PM.

## Live page

1. Is the server up: `curl -s -o /dev/null -w '%{http_code}' http://localhost:8770/api/durum`. If it is not 200, start it in the background (Bash `run_in_background`):
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/watch.py" --port 8770`
2. Give the user the address: in VS Code `Ctrl+Shift+P → Simple Browser: Show → http://localhost:8770` (or a browser).
3. The page is in English and Turkish (by browser language; the EN/TR button or `?lang=tr`). It refreshes every 3 seconds: who is running now, the timeline (Claude orange, Codex green, Gemini blue), the agent map, quota bars (external quota once a minute via `external-agent.sh quota`), jobs and scores. Clicking a job or a map node shows its last report and task in the side panel.

## Claude quota

The PM reads the plan name, the 5-hour and weekly usage percentages and the ISO reset times from the desktop app's usage tool, and adds its own context fill and token count if available. The script cannot read these from the CLI by itself; it writes the given measurement to the log:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/claude-quota.py" \
  --five-hour 35 --five-hour-resets 2026-10-07T16:00:00+03:00 \
  --week 65 --week-resets 2026-10-12T10:00:00+03:00 \
  --plan Max --context 42 --context-tokens 84000
```

`--plan`, `--context` and `--context-tokens` are optional; if tokens are given the context percentage is required too. Percentages are 0–100, tokens a non-negative integer. Called without arguments it prints the latest Claude buckets with measurement times and ages, line by line, and writes nothing. If the week is ≥ 70% or the 5-hour window ≥ 80% it warns to shift Claude's jobs to external workers.

The Claude card comes first; context is a separate thin row. With no Claude measurement the page shows that none exists yet (the PM writes it). The latest event is kept per provider/group/window, so an external quota reading does not erase Claude's. Every row shows its own measurement time. If the reset time has passed since the measurement, the row gets a "stale" label and a faded bar. Abbreviated dates (`MM-DD HH:MM`, `MM-DDTHH:MM`) are resolved in the local calendar with the measurement's year.

## Agent map

The jobs in the selected time window appear as a PM → lead → worker tree. External workers (Codex, agy) sit directly under the PM. Nodes show role, model (if known), provider color, state, duration and score if any; a click or Enter/space opens the side panel. The same tree is embedded in the session report.

The parent link comes from the hook's `ham.parent_agent_id`, `ham.parent_session_id`, the launch payload's `ham.agent_id`, or a `ham.transcript_path` that belongs to the parent agent. `ham.session_id` counts as a parent only if it matches a known agent or agent session id; the shared PM session id alone is no proof of a link. If no link is found, the parent is outside the selected window, or there is a cycle, the node attaches to the PM (decision `0005`). The real log's current samples carry no explicit parent field; those jobs stay under the PM.

The PM node is a virtual summary of the selected jobs: state and duration are computed from the jobs; the PM's real model, score and own running time are not in the log, so they are unknown. If several sessions fall in the same window they share that virtual root.

## Score

When a worker's job is done and the PM has measured it (roster experiment, `roster.md`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/events.py" score <job id> <1-5> [reason] \
  [--worker <provider/model/effort>] [--role <role>] [--field <field>] [--difficulty <E|M|H>] \
  [--quota <percent>] [--duration <s>] [--fixes <count>] [--project <name>]
```

With `--worker` the record goes both to the event log and to the persistent score ledger (`${XDG_DATA_HOME:-~/.local/share}/polycrew/puanlar.jsonl`). For a Claude agent write `--worker claude/<role>/<sonnet|opus|haiku>`; the script reads the real model from the agent's transcript and stores the name with its version (`claude/developer/sonnet-5-5`), so a new model starts with its own scores. If it warns that the version was not found, write the version yourself. The flagless form works too. Job id: for an external worker the name of the log folder (the last line of `external-agent.sh`), for a Claude agent the id of its row on the page (the Agent tool's `tool_use_id` or the agent id).

## Session report

At `/session-end`, if a team or an external worker was used in the session:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/watch.py" report --hours <session length in hours> --lang <project language: tr|en> --out <scratchpad>/team-report.html
```

Then publish the file as an Artifact (the title is already in the page, icon `chart`) and write the link into the notes file. The report embeds the reports and tasks; before publishing, check that it holds no secrets (keys, passwords).

## Notes

- Log: `${XDG_CACHE_HOME:-~/.cache}/polycrew/olaylar.jsonl` (change with `POLYCREW_EVENTS`). Safe to delete; the page starts empty.
- The PM reads Claude quota from the desktop tool and writes it with `claude-quota.py`; without arguments the script reads the last record.
- Hook field names may change with the Claude Code version; events also keep the truncated raw payload (`ham`).
