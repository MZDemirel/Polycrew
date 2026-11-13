---
name: watch
description: Open the local page that shows the team's agents and external workers (Codex, Gemini) live; at the end of the session produce its shareable report. Use when the user says "show the agents", "who is doing what", "watch the team", "watch page", "session report" (Turkish: "agent'ları göster", "kim ne yapıyor", "takımı izle", "izleme sayfası", "oturum raporu"), or when work is handed out with /team.
---

# Watch

Events are collected in one log (`hooks/events.py`, decision `0003`): Claude subagents through hooks (`PreToolUse` Agent, `SubagentStart`, `SubagentStop`), external workers through `external-agent.sh` (started, finished, quota), scores from the PM.

## Live page

1. Is the server up: `curl -s -o /dev/null -w '%{http_code}' http://localhost:8770/api/durum`. If it is not 200, start it with the Bash tool's own background run (`run_in_background`), not with `nohup … &` inside a command: a process started that way dies when the command returns.
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/watch.py" --port 8770`
2. Open it for the user, filtered to this project: `http://localhost:8770/?project=<name>`, where `<name>` is the project folder's name (in a worktree under `.claude/worktrees/`, the main project's folder). One server serves every project; without `?project=` the page shows all of them, and the selector at the top switches.
   - in the Claude desktop app, open the address in the built-in browser pane (its preview/navigate tool with the URL), so the page sits next to the chat;
   - in VS Code: `Ctrl+Shift+P → Simple Browser: Show` with the address;
   - otherwise give the address for a browser.
   The plugin cannot open it by itself: hooks only print text, and a server started from a hook does not outlive it.
3. The page is in English and Turkish (by browser language; the EN/TR button or `?lang=tr`). It refreshes every 3 seconds: a status line, the office, who is running now, quota bars (external quota once a minute via `external-agent.sh quota`), the timeline (one lane per worker; Claude orange, Codex green, Gemini blue), jobs and scores, the agent map. Clicking a bar, a job or a map node shows its last report and task in the side panel. The layout follows the page's own width, so it reads in the half-width browser pane next to the chat.

## Office

The first section of the page is a small pixel office. The PM sits on the left; every running Claude agent sits at a desk in the Claude room and every running external worker (Codex, agy) in the external workers' room, typing, with the monitor in the provider's color. Finished jobs stand in the break room, dimmed: the last 8, the rest as "+N done". A failed job has a red "!" over its head, an unknown one a "?". Each role has a small accessory (developer headphones, reviewer magnifier, artist beret, designer ruler, researcher book, lead tie; an external worker wears glasses when read-only and holds a pencil when it writes). A worker at a desk has a short label from its model name (`sol`, `flash`), numbered when several share it (`sol1`, `sol2`). Hovering shows who it is and what it is doing; a click opens the same side panel as everywhere else. It is a picture of the same data: the timeline, the job list and the map below remain the accessible, complete view.

## Claude quota

Two ways to get it into the log:

- **Status line (automatic, CLI):** Claude Code gives the status line command the plan's `rate_limits` (5-hour and 7-day, Pro/Max/Ultra plans). `claude-statusline.py` writes them as a quota event when they change or every 10 minutes, only in projects that use this workflow, and prints a short line. The user adds it to `~/.claude/settings.json`: `"statusLine": {"type": "command", "command": "python3 <plugin>/skills/watch/claude-statusline.py"}`; an existing status line is kept with `--then "<its command>"`. The plugin never edits settings itself.
- **PM (desktop app, or no status line):** the PM reads the plan name, the 5-hour and weekly usage percentages, any per-model weekly limit and the ISO reset times from the desktop app's usage tool (or `/usage`), and adds its own context fill and token count if available:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/claude-quota.py" \
  --five-hour 35 --five-hour-resets 2026-10-07T16:00:00+03:00 \
  --week 65 --week-resets 2026-10-12T10:00:00+03:00 \
  --plan Max --context 42 --context-tokens 84000 \
  --model-week Fable 23 2026-10-12T10:00:00+03:00
```

Reset times must be ahead and within the window's length (5 hours, 7 days). `--plan`, `--context`, `--context-tokens` and `--model-week` are optional; if tokens are given the context percentage is required too. Percentages are 0–100, tokens a non-negative integer. Called without arguments it prints the latest Claude buckets with measurement times and ages, line by line, and writes nothing. If the week is ≥ 70% or the 5-hour window ≥ 80% it warns to shift Claude's jobs to external workers.

The Claude card comes first; context is a separate thin row. With no Claude measurement the page shows that none exists yet (the PM writes it). The latest event is kept per provider/group/window, so an external quota reading does not erase Claude's. Every row shows its own measurement time and its reset time in local time. A row is "stale" (label with the reason, faded bar) when its reset time has passed, or when the reading is older than its window allows: 5 hours for the 5-hour window, one day for the week; the same rule as `roster.py` and `/doctor` (`hooks/quota.py`). A bucket that could not be read shows `?`, not 0%. The page refreshes the Codex and agy reading at most every 5 minutes, and an unchanged reading is not written again. Old abbreviated dates are resolved with the measurement's year: `MM-DD HH:MM` in local time, agy's old `MM-DDTHH:MM` in UTC.

## Agent map

The jobs in the selected time window appear as an indented PM → lead → worker tree, folded until the tree has depth (a lead, or an agent that started agents). External workers (Codex, agy) sit directly under the PM. Nodes show role, model (if known), provider color, state, duration and score if any; a click or Enter/space opens the side panel. The same tree is embedded in the session report.

The parent link comes from the hook's `ham.parent_agent_id`, `ham.parent_session_id`, the launch payload's `ham.agent_id`, or a `ham.transcript_path` that belongs to the parent agent. `ham.session_id` counts as a parent only if it matches a known agent or agent session id; the shared PM session id alone is no proof of a link. If no link is found, the parent is outside the selected window, or there is a cycle, the node attaches to the PM (decision `0005`). The real log's current samples carry no explicit parent field; those jobs stay under the PM.

The PM node is a virtual summary of the selected jobs: state and duration are computed from the jobs; the PM's real model, score and own running time are not in the log, so they are unknown. If several sessions fall in the same window they share that virtual root.

## Score

When a worker's job is done and the PM has measured it (roster experiment, `roster.md`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/events.py" score <job id> <1-5> [reason] \
  [--worker <provider/model/effort>] [--role <role>] [--field <field>] [--difficulty <E|M|H>] \
  [--quota <percent>] [--duration <s>] [--fixes <count>] [--project <name>]
```

`--quota` and `--duration` are optional: for an external worker both come from the run's own measurement, for a Claude agent the duration comes from its start and end events (Claude quota cannot be read from the CLI, so it stays empty). A value you pass wins.

With `--worker` the record goes both to the event log and to the persistent score ledger (`${XDG_DATA_HOME:-~/.local/share}/polycrew/puanlar.jsonl`). For a Claude agent write `--worker claude/<role>/<sonnet|opus|haiku>`; the script reads the real model from the agent's transcript and stores the name with its version (`claude/developer/sonnet-5-5`), so a new model starts with its own scores. If it warns that the version was not found, write the version yourself. The flagless form works too. Job id: for an external worker the name of the log folder (the last line of `external-agent.sh`), for a Claude agent the id of its row on the page (the Agent tool's `tool_use_id` or the agent id).

## Session report

At `/session-end`, if a team or an external worker was used in the session:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/watch.py" report --hours <session length in hours> --lang <project language: tr|en> --out <scratchpad>/team-report.html
```

Run it from the project folder: the report holds only this project's jobs (`--project <name>` to choose another, `--all-projects` for every project). Its title names the project and the date.

Then publish the file as an Artifact (the title is already in the page, icon `chart`) and write the link into the notes file. The report embeds the reports and tasks; before publishing, check that it holds no secrets (keys, passwords).

## Notes

- Log: `${XDG_CACHE_HOME:-~/.cache}/polycrew/olaylar.jsonl` (change with `POLYCREW_EVENTS`). Safe to delete; the page starts empty.
- The PM reads Claude quota from the desktop tool and writes it with `claude-quota.py`; without arguments the script reads the last record.
- Hook field names may change with the Claude Code version; events also keep the truncated raw payload (`ham`).
