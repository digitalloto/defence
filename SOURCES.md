# Sources and Credits

Third-party material vendored into this repository, with attribution and
provenance. Anything listed here was written by someone else — keep this file
updated when you add, re-sync, or remove vendored code.

---

## `pocket-bot/` — Midnight Make Pocket Bot

| | |
|---|---|
| **Upstream** | https://github.com/midnightmake/pocket-bot-downloads |
| **Author / owner** | Midnight Make (https://www.midnightmake.com) |
| **Product page** | https://www.midnightmake.com/products/pocket-bot |
| **Vendored at commit** | `ac242e45ba6ea8d1ff9fa5556b5385ae82af0e72` ("Update README.md", 2026-08-01) |
| **Copied on** | 2026-08-06 |
| **License** | **Not stated upstream** — see the note below |

### Why it's here

Midnight Make publish the Pocket Bot's firmware source, 3D-printable STLs, and
sample courses freely. A local copy is kept in this repository so the material
is available for reference and modification without depending on the upstream
repo staying online or unchanged.

### What was copied

* `pocket-bot/firmware/` — complete AVR firmware source (drivers, core, example
  programs) in a Microchip Studio project, plus the prebuilt `Release/` output
  and the `program-linux` / `program-win.bat` flashing scripts.
* `pocket-bot/stls/` — 3D-printable replacement and expansion parts
  (chassis, wheels, marker mount, round table).
* `pocket-bot/courses/` — sample line and demo courses as `.docx` and `.pdf`.
* `pocket-bot/README.md` — the upstream README, kept as-is.

The upstream `firmware/.vs/` directory (Visual Studio editor state) was dropped
as local IDE cruft. Nothing else was removed, and no file contents were altered.

### Licensing — read before redistributing

The upstream repository **does not include a LICENSE file**. The maker has
stated publicly that the code and STLs are freely available, but "freely
available" is not the same as a granted license: with no license declared, the
default position under copyright is that all rights are reserved by the author.

Practical reading:

* Using, printing, building on, and modifying this for your own purposes is
  consistent with how it was published and with the maker's stated intent.
* Redistributing it, shipping it inside a product, or relicensing it is **not**
  covered by anything in writing. If any of that is on the table, ask Midnight
  Make for an explicit license first.

Attribution to Midnight Make should be preserved in any derivative work.

### Related upstream repositories

Not vendored here, but from the same author and useful alongside this code:

* [`course-encoder`](https://github.com/midnightmake/course-encoder) — CLI tool
  for embedding bytes into Pocket Bot line courses.
* [`pocket-bot-global-vision`](https://github.com/midnightmake/pocket-bot-global-vision)
  — global vision server demonstrating swarm formation control.
* [`camera-calibrate`](https://github.com/midnightmake/camera-calibrate) —
  checkerboard camera undistortion for global vision systems.
* [`mbee-drone-downloads`](https://github.com/midnightmake/mbee-drone-downloads)
  — files for the Midnight Make μBee Drone Kit.

### Re-syncing with upstream

This is a plain file copy, not a submodule or subtree, so local edits are yours
to keep and nothing points back at upstream automatically. To pull in later
upstream changes:

```sh
git clone --depth 1 https://github.com/midnightmake/pocket-bot-downloads.git /tmp/pocket-bot-upstream
diff -ru pocket-bot /tmp/pocket-bot-upstream --exclude=.git --exclude=.vs
```

Review the diff and apply what you want by hand, so local modifications aren't
clobbered. Then update the "Vendored at commit" row above.

---

## `agency-agents/` — The Agency (AI agent definitions)

| | |
|---|---|
| **Upstream** | https://github.com/msitarzewski/agency-agents |
| **Author / owner** | msitarzewski and 107 other contributors ("AgentLand Contributors") |
| **Project site** | https://agencyagents.app |
| **Vendored at commit** | `647c8baa42b6842afb4a97bf2c0950d45ba88e8b` (2026-09-06) |
| **Copied on** | 2026-09-07 |
| **License** | **MIT** — see `agency-agents/LICENSE` |

### Why it's here

A library of 268 specialist AI agent definitions (markdown prompt files) plus
the tooling to install them into 16 different AI coding tools. Copied locally so
the roster can be browsed, adapted, and cherry-picked without depending on
upstream.

### What was copied

All 356 tracked files from upstream, unmodified — every division directory, the
`scripts/` tooling, `tools.json`, `divisions.json`, `LICENSE`, and the
documentation. Nothing was removed and no file contents were altered.

Note: `agency-agents/.github/` carries upstream's 6 CI workflows. These are
**inert here** — GitHub only reads workflows from `.github/workflows/` at the
repository root, and these sit one level down. They were kept so the copy stays
faithful. Do not move that directory to the repository root unless you actually
want upstream's CI running on this repo.

### Licensing

MIT — genuinely permissive. You may use, modify, merge, publish, and even sell
this, commercially or not. The single condition is that the copyright notice and
licence text in `agency-agents/LICENSE` are preserved in any copy or substantial
portion. Keep that file where it is.

### What's actually in it

* **268 agent definitions** across 21 divisions — engineering (59), specialized
  (58), marketing (36), gis (13), security (12), design (10), and smaller sets
  for sales, testing, finance, healthcare, academic, game development, spatial
  computing, and others.
* Each agent is a markdown file with YAML frontmatter (`name`, `description`,
  `color`, `emoji`, `vibe`) followed by identity, mission, workflows, and
  success metrics.
* `scripts/convert.sh` converts one agent definition into the formats expected
  by 16 tools: Claude Code, Codex, Gemini CLI, GitHub Copilot, Qwen, Cursor,
  opencode, Osaurus, Aider, Antigravity, Kimi, OpenClaw, Windsurf, Hermes,
  Mistral Vibe, ZCode.
* `scripts/install.sh` auto-detects installed tools and installs by division or
  by individual agent; supports `--dry-run`.
* `scripts/lint-agents.sh` and `check-agent-originality.sh` enforce house style
  and catch duplicated agents.

### Re-syncing with upstream

As with `pocket-bot/`, this is a plain file copy — no submodule, no upstream
link. To check for changes:

```sh
git clone --depth 1 https://github.com/msitarzewski/agency-agents.git /tmp/agency-upstream
diff -ru agency-agents /tmp/agency-upstream --exclude=.git
```

Upstream is very active (413 commits, 108 contributors, first commit Oct 2025),
so expect this copy to drift quickly. If you want to track it properly rather
than re-diffing by hand, fork the upstream repo on GitHub instead — a fork keeps
the upstream link and GitHub will surface new commits for you.
