---
name: project-setup
description: Set up the working discipline in a project — CLAUDE.md, PLAN.md, NEXT_SESSION.md and a docs/decisions/ skeleton. Use when the user says "set up the workflow in this project", "I'm starting a new project, let's make a plan" (Turkish: "bu projeye düzeni kur", "yeni proje başlatıyorum, plan çıkaralım"). Never overwrites existing files.
---

# Project setup

First get to know the project (language, package manager, test and lint commands, git state). Then ask the user in one batch (`AskUserQuestion`):

- Conversation and document language; code language.
- Default mode: **builder** (Claude writes the code and adds tests) or **teacher** (the user writes, Claude guides). It can change per phase.
- Commit: who commits, prefix and format (for example a plain single line, or `feat(...): ...`), which branch; who pushes and who opens PRs.
- Whether a new dependency needs permission.

**The fixed git rules are not asked** and never appear as an option of any question (no signature, no tool line in PRs, merged branches are kept, workers do not push): `${CLAUDE_PLUGIN_ROOT}/rules/git.md`. Whatever format the user picks, they are written into the `Git` section.

## Files (leave existing ones alone; suggest the missing section)

Write every file in the language the user chose; the file names below stay as they are.

**CLAUDE.md**: short; one paragraph describing the project, then these sections:
`Language`, `Working mode` (teacher/builder, "start every phase in plan mode", "tick the PLAN.md checkboxes", "write important decisions to docs/decisions/"), `Git` (the user's answers, then the "Block for the project's CLAUDE.md" from the rules file), `Dependencies`, `Architecture rules` (the ones the project itself shows), `Environment`, `Commands` (install, test, lint, types, run), `Definition of done` (tests green, lint and types clean, plus project-specific visual or measurement checks).

**PLAN.md**: goal, principles, then phases:

```markdown
### Phase N: Name
**Goal:** one sentence.
**Mode:** builder | teacher
- [ ] item
**Done when:** an observable criterion.
**Learning note:** (teacher mode) the concepts to learn.
```

**NEXT_SESSION.md**: `# Next session`, a "Last updated" line, then in this order: `## Where we left off`, `## Next` (`### 1. ...`), `## Questions for the user`, `## First steps when the session opens (for Claude)`, `## What you need to do`, `## Start prompt` (in a code block), `## At the end of the session`. The order matters: the session hook shows the first section and the headings of the second. If the project already has `SONRAKI_OTURUM.md`, that is its notes file; do not create a second one.

**docs/decisions/0001-...md**: the first decision is usually "why this structure and these tools" (the `/decision` template).

If `CLAUDE.md` already exists and its `Git` section lacks one of the fixed rules, do not touch the file; show the missing lines and suggest adding them.

**User level (suggest once):** if `~/.claude/CLAUDE.md` does not exist or does not contain the fixed rules, suggest writing the same block there, showing the text (it affects every project). Never create or change that file without approval; if the user declines, do not ask again.

After setup, list what was created and make the first commit in the project's format and under the fixed rules (skip the commit if the user wants to commit themselves).
