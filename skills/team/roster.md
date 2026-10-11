# Roster: worker by difficulty (built from measurements, the plugin's decision note 0002, 2026-10-02)

This table is the prior; the current ranking is `roster.py suggest`.

Difficulty **E** easy, **M** medium, **H** hard. Claude quota is kept for the PM, the artist, design and H-level code.
External workers run through the `external-agent` skill (Codex: `codex`; Gemini, and Claude via agy: `agy`).

| Role | E | M | H | Backup |
|---|---|---|---|---|
| researcher | Gemini 3.1 Pro (agy, read) | Gemini 3.1 Pro | Codex sol + Gemini Pro (compare) | Claude `researcher` (haiku) |
| reviewer | Codex sol (read) | Codex sol (read; evidence-based, no false alarms) | Codex sol; for work Codex wrote, additionally Claude `reviewer` (sonnet); astra xhigh only for the most critical (one review is ~20% of the 5-hour window) | Gemini 3.1 Pro (unreliable with narrow permissions: 1 in 4 in the 2026-10-02 run) |
| developer | Gemini 3.8 Flash (write; worked with narrow permissions too) or Codex sol | Codex sol high (write; state the file boundary in the task plus "if something outside the boundary is needed, make the smallest change and report it in the final message; do not stop"; at most 3–4 jobs per 5 hours, ~12% each) | Claude `developer` (sonnet; opus if needed) and optionally Codex astra on a separate branch, pick the better | Codex sol |
| image reading and measuring | Codex astra / sol (read, `-i` image) | Codex | Claude `artist` (opus): artistic judgment | Gemini Pro |
| artist (critique) | Claude `artist` | Claude `artist` | Claude `artist` (opus) | — |
| image generation | Codex `image_gen` | Codex | Codex (+ Gemini as a second opinion for concepts) | Gemini Pro |
| designer | PM | Claude `designer` (opus) | Claude `designer` (opus) + Gemini Pro second opinion | — |
| lead | PM | PM | Claude `lead` (sonnet), only for a truly parallel large stream | — |

- **Concurrency:** at most 2–3 developers running tests (machine), at most 2 Claude agents. External workers have separate quotas but share the machine.
- **Model and effort of the roles** (frontmatter):
  - lead: sonnet, medium;
  - developer: sonnet, high;
  - artist: opus, medium;
  - reviewer: sonnet, high;
  - designer: opus, high;
  - researcher: haiku.

  `-master` variants were not needed so far: for an H job the PM starts the role with `model: opus`.

**Second run (2026-10-02, Pixlender 6.6, record `deney/2026-10-02-kosu2/kayit.md`):** Codex sol 4/5 writing, 5/5 reading; Gemini Pro succeeded once in 4 read attempts; Claude artist 4.7/5. What ate most of Claude's weekly limit was the PM's context.

**Quota (measured):** run `external-agent.sh quota` before handing out work. Codex's 5-hour window is narrow: one coding run takes about 25–30%. Gemini is plentiful: the whole experiment was 4% of the weekly quota. Claude via agy ran out after a few jobs. If the Codex window is past 60%, medium jobs go to Gemini.

Known pitfalls: agy cannot be a developer with narrow permissions (the job drops at the first command without permission); Claude Opus via agy has a small quota; Codex may follow AGENTS.md and write PLAN and decision notes (state the file boundary in the task); Gemini Flash is fast but heavy on tokens.
