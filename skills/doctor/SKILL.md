---
name: doctor
description: >-
  Check the polycrew setup without changing anything, after installation or when something does not work. Use for "check the setup", "why doesn't the watch page show anything", "is polycrew installed correctly" (Turkish: "kurulumu denetle", "polycrew çalışıyor mu").
---

# Doctor

Run from the user's project folder:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/doctor/doctor.py"
```

Use `--project <dir>` for another project, or `--json` for a JSON list of checks.

- `ok`: the check passed; no action is needed.
- `warn`: something is missing, stale or could not be checked; read the suggested action. Claude roles can work without external tools.
- `fail`: a required check failed, such as Python below 3.9 or broken shell syntax. The script exits 1; otherwise it exits 0.

The plain report ends with counts of all three statuses. JSON contains only the checks.
Checks cover Python, tools on PATH, project files, the event log, recorded quota,
agy permissions (when installed), and each plugin shell script's syntax.

This skill reports and suggests but changes nothing. It never writes files,
refreshes quota, starts a network call or runs an external model.
Explain warnings and failures, then offer fixes to the user one by one before applying them.
