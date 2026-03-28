# DevTrack Demo — Speaker Notes

15-minute walkthrough for team / peers. The script (`run_demo.sh`) drives the terminal — use these notes to narrate each section.

---

## Pre-demo checklist

- [ ] Run `bash demo/setup.sh` (once — idempotent)
- [ ] Daemon running: `devtrack status`
- [ ] MongoDB running: `docker compose up -d`
- [ ] Terminal font size bumped (Cmd+= a few times)
- [ ] Notifications allowed in System Preferences
- [ ] Browser closed (you'll open the wiki at the end)

---

## Section 1 — Introduction (~1.5 min)

**What to say:**
> "DevTrack is a background daemon that sits alongside your normal workflow. You don't change how you code — you still use git, your IDE, your PM tool. DevTrack intercepts at the seams: the commit, the work update, the ticket status."

Show `devtrack status`. Point out:
- Which workspaces are being monitored
- IPC connection to the Python bridge
- Daemon PID / uptime

---

## Section 2 — The Commit Flow (~4 min)

**This is the centrepiece.** Let the AI enhancement run — don't rush it.

**What to say before the commit:**
> "We've got a real change here — implementing input validation that was just a TODO stub. Watch what happens when I commit."

**During AI enhancement prompt:**
> "DevTrack sent the diff and branch context to the LLM. It's offering a better commit message. I can accept, enhance further with a bigger token budget, or retry."
> Press **A** to accept.

**During ticket picker:**
> "Before the commit lands, DevTrack shows me the open issues in this repo. I can attach this commit to the right ticket — or skip."
> Select issue #2 (input validation).

**During 'Log this work?' prompt:**
> "This is the PM sync step. It'll comment on the GitHub issue with the commit hash, message, and time spent."
> Press **y**, enter `45m`.

**After sync:**
> "The comment is live on the GitHub issue right now. No copy-paste, no context switching."

**During push prompt:**
> Press **y** — shows the full loop closes in one flow.

---

## Section 3 — Ticket Alerter (~2 min)

**What to say:**
> "DevTrack also watches for things happening TO you — not just what you're doing. It polls GitHub and Azure DevOps every 5 minutes and surfaces relevant events."

Point out:
- GitHub events (assigned, comment from alice, review request from bob)
- Azure events (new assignment, charlie's comment, state change from david)
- Delta sync — each source has its own `last_checked` timestamp in MongoDB
- `devtrack alerts --clear` to mark all read

**Key differentiator to mention:**
> "This isn't a webhook setup requiring a public server. It's pure polling with MongoDB-backed deduplication — works entirely local, no infra."

---

## Section 4 — git-sage (~2.5 min)

**What to say:**
> "git-sage is an agentic git assistant. Give it a goal in plain English and it figures out the git operations. For the demo I'm using the 'ask' mode — it reads the repo and reasons about it."

While it runs:
> "It's reading the source files, the git log, and the open issues you saw in the ticket picker. It's reasoning about the delta between what's implemented and what the issues are asking for."

If time permits: `devtrack sage do "create a branch feature/add-auth for issue #1"` — shows the agentic loop taking real action.

---

## Section 5 — Personalization (~1.5 min)

**What to say:**
> "The AI parts of DevTrack don't just generate generic text. They learn from your actual communication — Teams messages, how you write updates, your vocabulary and tone — and inject that style into every generated message."

`show-profile` output: point out formality level, preferred length, emoji usage, common phrases.

`test-response`: show the output and point out it sounds like a human wrote it, not a bot.

---

## Section 6 — Reports + Wiki (~1.5 min)

**What to say:**
> "At the end of the day or week, DevTrack can generate an AI-enhanced report — what you worked on, tickets updated, time distribution — and deliver it to your terminal, email, or Teams."

Wiki: briefly scroll through the feature list in the wiki. Point out the architecture diagram if there are technical people in the audience.

---

## Common questions

**"Does it work offline?"**
> Yes — the Go daemon queues everything locally (SQLite). The Python bridge retries. Sync happens when connectivity returns.

**"What LLMs does it support?"**
> Ollama (fully local), OpenAI, Anthropic, Groq. Configurable fallback chain — if one fails, the next kicks in automatically.

**"Does it work with GitLab?"**
> Yes — bidirectional sync with GitLab is fully wired, same as GitHub and Azure DevOps.

**"What about privacy / security?"**
> All credentials stay local in `.env`. Commit diffs only leave the machine if you're using a cloud LLM. Ollama mode is 100% local.
