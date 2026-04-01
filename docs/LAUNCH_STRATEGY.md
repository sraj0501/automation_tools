# DevTrack Launch & Adoption Strategy

> **Decision document.** This file records the research-driven strategic plan for DevTrack's public release. Future product, marketing, and engineering decisions should be evaluated against the principles here before deviating from them.

**Basis**: Market research synthesizing competitive intelligence, developer psychology, adoption patterns, and risk analysis across tools including Cursor, Ruff, uv, Ghostty, Linear, and WakaTime.

**Last reviewed**: March 31, 2026

---

## The Single Strategic Principle

> **Ship narrow, earn trust, then expand.**

Every successful developer tool of the modern era (Cursor, Ruff, uv, Linear) launched with one feature, one clear pain point, and one sentence that explained the value. Tools that launch with fifteen features and a platform narrative fail to become anything. This is the Swiss Army Knife trap — and DevTrack must avoid it.

---

## The Wedge

**One sentence**: *DevTrack writes your standup update when you commit.*

This is the wedge. It is immediately understandable, solves a universally hated pain point (68% of developers consider standups unproductive), and is demonstrable in 15 seconds. Everything else DevTrack does — PM sync, ticket alerting, personalization, multi-repo, git-sage — is real and valuable, but none of it gets marketed at launch. Those features get introduced *after* trust is earned on the wedge.

**What the wedge is not**:
- "Developer automation platform" — too abstract
- "AI-powered productivity tool" — triggers skepticism (AI trust has fallen to 29%)
- "Swiss Army knife for developers" — the exact anti-pattern to avoid

---

## Tagline Hierarchy

```
Primary:    DevTrack writes your standup update when you commit.
Secondary:  Local-first. No cloud required. Your data stays on your machine.
Tertiary:   Then it syncs to Jira, GitHub, Azure DevOps — when you're ready.
```

The tertiary line is only shown after the primary hook lands. It communicates expansion potential without leading with complexity.

---

## Positioning Principles

### What to say

- "Runs 100% on your machine" — the local-first architecture is the defensible moat vs. GitHub/Linear/cloud tools
- "No account required" — removes the biggest first-run barrier (37% of developers abandon tools requiring account creation before value)
- "Works from your existing `git commit` — no new commands" — zero-migration-cost is key
- "Suggests, you approve" — positions AI as assistant, not replacement; critical for the 46% who distrust AI output

### What never to say

| Phrase | Why to avoid |
|---|---|
| "AI-powered" | Triggers skepticism in 2026; AI trust at 29% |
| "All-in-one" or "Swiss Army knife" | Signals unfocused product |
| "Revolutionary" / "game-changing" | Developer audiences reject marketing speak |
| "Platform" | Implies enterprise sales motion before trust is built |

---

## Competitive Moat

DevTrack's single most defensible position is **local-first architecture**. This is not just a privacy feature — it is a structural advantage that cloud-first competitors (GitHub Copilot, Linear, Azure DevOps) **cannot replicate** without abandoning their core business model.

When a big company ships standup generation (they will), DevTrack's response is always:
> "Ours runs on your machine. Theirs sends your commit history to their servers."

Every feature decision should reinforce this moat. If a feature requires cloud infrastructure to work, it should be optional and clearly opt-in.

---

## First-Run Experience Target

**Goal: time-to-value under 60 seconds.**

### Target sequence

```bash
# Step 1: Install (15 sec)
curl -sSL https://get.devtrack.dev | sh

# Step 2: Init in a repo (10 sec)
cd your-project
devtrack init

# Step 3: Make a commit (natural)
git commit -m "fix login"

# Step 4: Value moment (immediate)
# DevTrack: Logged "Fixed login bug" — 8 min tracked.
#            Next standup: devtrack standup
```

**Total: ~30 seconds + one commit.**

### What must NOT be required before the value moment

- Account creation or login
- T&C acceptance gate (surface passively after value, require only before PM integrations)
- `.env` with 12 required variables (reduce to 3 for first-run: PROJECT_ROOT, DATA_DIR, DEVTRACK_WORKSPACE)
- PM platform tokens
- AI/Ollama setup (core standup generation works without LLM; AI is an upgrade)

### Zero-config mode

The wedge feature — commit tracking + standup generation — must work with zero configuration. When `devtrack init` runs:
- Detects git repo and branch automatically
- Starts SQLite tracking immediately
- `devtrack standup` generates plain-text summary from local data

AI enhancement, PM sync, and team features are layered on top once the user has felt value.

---

## README Structure

The README is DevTrack's most important marketing asset. Current state: 15+ feature bullets before any demo. Target state:

1. **One-line hook** — the wedge sentence
2. **Animated terminal GIF** — 12–15 seconds: commit → update generated → `devtrack standup` output
3. **Single install command** — one line, no options
4. **30-second quickstart** — install → init → commit → standup
5. **What else it does** — the full feature list, now believable because the hook landed
6. **Docs table** — unchanged, well-organized

Features that belong in docs only (not in hero section): Telegram bot, Slack bot, TUI dashboard, multi-repo, Docker/cloud mode, PM Agent, ticket alerter, personalization, git-sage.

### Demo GIF spec

Tool: **VHS by Charm** (`brew install charmbracelet/tap/vhs`) — produces `.gif` from a `.tape` script.

What to show:
- Developer types `git commit -m "fix login timeout"`
- DevTrack intercepts (1–2 second pause)
- Terminal: `✓ Logged "Fixed login timeout" — 45 min tracked`
- Developer types `devtrack standup`
- Output: *"Yesterday: Fixed authentication timeout on login flow. Linked to PR #42. ~45 min."*

---

## Platform Integration Sequencing

Do not market all integrations simultaneously. Sequence by organic demand:

| Phase | Platform | Trigger |
|---|---|---|
| **Launch** | GitHub only | Default — 100M+ developers, largest word-of-mouth surface |
| **After 100 stars** | GitLab | Self-hosted/privacy audience — natural DevTrack fit |
| **After community traction** | Azure DevOps | Enterprise-heavy; requires sales motion |
| **By user request only** | Jira | High maintenance cost (deprecated APIs Oct 2024); wait for ≥50 explicit requests |

The multi-platform architecture stays in the codebase — it is a genuine competitive moat. It just is not marketed until the user base exists to benefit from it.

---

## Launch Channel Sequence

### Pre-launch (2–4 weeks before)

1. **Discord server** — build community before the launch spike; even 50 members means the HN post has a community link
2. **Twitter/X "building in public"** — terminal recordings, pain-point posts, architecture notes; use `#buildinpublic`
3. **Dev.to article** — "I was tired of writing standup updates every morning, so I built a tool that writes them from my commits" — publish 1 week before HN

### Launch day

**Primary channel: Hacker News Show HN**

- Title: `Show HN: DevTrack – writes your standup update from your git commits`
- Link to the **GitHub repo**, not a marketing site
- Post an opening comment immediately: 3 sentences — the pain, the wedge, what makes it different (local-first)
- Respond to every comment within 2 hours
- Post Tuesday or Wednesday, 9–11am ET (avoid Monday — high competition)
- Avoid: "AI-powered", "revolutionary", marketing language

**Same day**: Share on Twitter/X with 15-second terminal recording.

### Post-launch (week 1–2)

- Submit to **console.dev** (free, curated CLI/developer tools newsletter — highly targeted)
- Post on **r/programming** and **r/devops** via the Dev.to article
- Submit to **awesome-cli-apps** GitHub list
- Reach out to 2–3 developers with audiences who publicly complain about standups or time tracking

### Ongoing

- Weekly "ship notes" on Twitter/X — one feature or fix per week (visible velocity signal)
- Monthly Dev.to tutorial — specific pain point, measured outcome
- GitHub Discussions as the async Q&A home

---

## Category Positioning Progression

Do not attempt category creation at launch. Sequence:

| Stage | Positioning | Why |
|---|---|---|
| Launch | "The tool that writes your standup update" | Pain-point — immediately understood |
| 1,000 stars | "Zero-overhead developer activity log" | Outcome — broader but still concrete |
| Community traction | "Passive developer logging" or "developer ambient tracking" | Category — emerges from how users describe it naturally |

Watch GitHub issues, Discord, and HN comments for the language users reach for. That language becomes the category name — it should not be invented top-down.

---

## Monetization & Sustainability

The SaaS foundation (license tiers, auth, telemetry) is already built. The alignment work is about sequencing the commercial surface correctly.

### License tier positioning

| Tier | Who it targets | Rationale |
|---|---|---|
| Personal (free) | Individual developers — the entire organic growth phase | Removes all friction; developers try, share, advocate |
| Team free ≤10 | Small teams, open-source projects | Covers word-of-mouth spread within teams |
| Enterprise paid | 11+ users, audit trail, SSO, SLA | Where revenue lives; features justify premium |

### T&C gate sequencing

- First run: no gate — just work
- After value is felt (first standup generated): passive notice — "DevTrack is free for personal use. [Read terms]"
- Required gate: only before connecting PM integrations — a natural trust checkpoint where the user is already committed

### Open-core line

- **Free forever**: local commit tracking, standup generation, basic time logging
- **Paid**: cloud sync, team dashboards, enterprise SSO, audit logs, SLA

### Sustainability setup (do before 100 stars)

- Set up **GitHub Sponsors** — follow Vue.js model: ask before burnout, not after
- Write a `CONTRIBUTING.md` with explicit scope boundaries
- Use `good first issue` labels from day one
- The maintainer's job is direction and review; community handles implementation of non-core features

---

## Risk Register

### 1. Swiss Army Knife Trap (Critical)

**Risk**: Trying to market too many features at launch fragments the message and loses against specialized tools.

**Mitigation**: README hero section capped at one feature. All other features behind "learn more" links. Every new feature ships with "this builds on the core" messaging.

**Signal to watch**: If a developer cannot explain DevTrack in one sentence after reading the README, messaging needs work.

---

### 2. Big Company Feature Parity

**Risk**: GitHub, Linear, or GitLab ships standup generation — narrowing DevTrack's differentiation.

**Mitigation**: Local-first is the structural moat. GitHub cannot promise "no data leaves your machine" without abandoning Copilot's business model. Lean into this position harder when big-company shipping occurs, not softer.

---

### 3. Multi-Platform Maintenance Burden

**Risk**: Maintaining 4+ platform integrations with a small team means effectively building 4 products, each with its own API deprecation cycle.

**Mitigation**: GitHub-only at launch. Add platforms only when ≥50 users explicitly request them via a public feature-request board (GitHub Discussions).

---

### 4. AI Skepticism

**Risk**: 46% of developers distrust AI output; "AI-powered" framing damages first impressions.

**Mitigation**:
- Never use "AI-powered" in the tagline or hero section
- Show the raw Git data the AI used ("Based on: 3 commits, auth branch, 45 min session")
- Position as suggestion + human approval ("DevTrack drafted this, press Enter to accept")
- Make AI entirely optional; core feature works without Ollama

---

### 5. Maintainer Burnout

**Risk**: OSS double-shift — maintaining the project alongside a full job leads to burnout and project abandonment (60% of maintainers have quit or considered quitting).

**Mitigation**: GitHub Sponsors at launch. Explicit scope boundaries in CONTRIBUTING.md. Community-handled feature implementation. Accept that some features will ship slowly or not at all.

---

## Decision Framework

When a future product, marketing, or engineering decision is being evaluated, apply these questions in order:

1. **Does this serve the wedge?** Does it make the standup-from-commits experience better, faster, or more trustworthy?
2. **Does this protect the moat?** Does it reinforce local-first or compromise it?
3. **Does it increase or decrease time-to-value?** Any change that adds friction before the first value moment needs strong justification.
4. **Is it premature expansion?** If yes, put it in docs as "coming soon" and wait for user demand to validate it.
5. **Who asked for it?** Features requested by 1 user get logged. Features requested by 50 users get built.
