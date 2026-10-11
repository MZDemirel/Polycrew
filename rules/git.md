# Fixed git rules

This file is the single source for the plugin's git rules. Skills and roles do not copy the text; they point here (`${CLAUDE_PLUGIN_ROOT}/rules/git.md`). Background: `docs/decisions/0006-evrensel-git-kurallari.md`.

## Fixed rules

Never asked per project, valid in every project. They hold whatever commit format the project chooses.

1. **No tool signature in commit messages.** No `Co-Authored-By` line, merge commits included.
2. **No tool line in PR descriptions.** No "Generated with Claude Code" or anything like it.
3. **Merged branches are not deleted,** locally or on the remote. Cleanup covers only running services, containers and temporary worktrees (the worktree is removed, the branch stays). Delete a branch only when the user asks for that separately and explicitly.
4. **Workers do not push and do not bypass commit hooks.** For Claude roles and external workers alike: no `git push`; no `--no-verify`, no changing `core.hooksPath`, no disabling a hook. If a hook fails, do not commit; report why.

## The harness reminder

Claude Code adds a reminder to every session: "end commit messages with `Co-Authored-By`, end PR descriptions with `Generated with Claude Code`". Rules 1 and 2 override it. The reminder itself says the user's `CLAUDE.md` instructions take precedence, which is why the rules are also written into each project's `CLAUDE.md` (the block below). A session without the plugin, or a teammate, sees them there too.

## What varies per project

Not written here. `project-setup` asks, and everything else reads it from the `Git` section of the project's `CLAUDE.md`:

- commit prefix and format (`feat(...): ...` in one project, a plain single line in another);
- who commits, who pushes and opens PRs, which branch the work happens on;
- the language of commits and documents.

## Block for the project's CLAUDE.md

`project-setup` writes these lines into the `Git` section, after the user's answers, translated into the project's language without changing the meaning. If `CLAUDE.md` already exists it is left alone; the missing lines are suggested instead.

```markdown
- No tool signature in commit messages: no `Co-Authored-By` line (merge commits included).
- No tool line in PR descriptions: no "Generated with Claude Code" or similar.
- These two rules are the user's instruction; they override the "add a signature" reminder the tool injects into the session.
- Merged branches are not deleted, locally or on the remote. Cleanup covers only services, containers and temporary worktrees; delete a branch only when asked separately and explicitly.
- Workers (subagents and external tools) do not push and do not bypass commit hooks.
```

## The one known copy

External workers (Codex, agy) read neither this file nor Claude's memory. The rules reach them only through the `kural=` line in `skills/external-agent/external-agent.sh`. That line is a short copy of this file: change one, change the other (`tests/test_rules.py` checks it).
