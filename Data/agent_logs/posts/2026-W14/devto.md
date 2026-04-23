# I Turned My Google Sheets Hack Into a Real Tool. It Took Six Months and I Have No Regrets.

*A sequel to [The Daily Standup Slayer](https://dev.to/shashank_raj/the-daily-standup-slayer-how-this-lazy-manager-automated-everything-except-meetings-540)*

---

Six months ago I wrote about automating my standups with a Google Sheet, a cron job, and the kind of infrastructure that makes real engineers wince. Nightly runs. A Docker container on EC2. Apps Script that worked until it didn't. The whole thing was duct tape at scale, and I was weirdly proud of it.

Then my PM asked me to update the ticket *before* the standup, not after.

The sheet broke. The cron job silently failed for three days. And I found myself, at 11pm on a Wednesday, manually updating four Jira tickets while my Apps Script sat in production doing absolutely nothing, successfully.

That was the night I decided to rewrite the whole thing properly.

---

## The New Problem (Same as the Old Problem, Just More Honest)

The Google Sheet approach had one fatal flaw: it was still *me* doing work. I was just doing it in a spreadsheet instead of a Jira UI. Every night. Before midnight. In a specific format. Because if the format was wrong, the script silently ate the row and nobody found out until the standup.

What I actually wanted was: **commit code, ticket updates itself, standup writes itself, I do nothing.**

Not a dashboard. Not a different place to type. Nothing.

The tooling for this apparently doesn't exist if you want it to work locally, with your own LLM, without sending every commit message to a SaaS vendor who charges per-seat.

So, naturally, I built it.

---

## What I Actually Built

**DevTrack** is a Go daemon that watches your git repositories. When you commit, it fires. When a timer hits (configurable — mine is every 90 minutes), it fires. Each trigger gets routed over HTTP to a Python backend that runs NLP, calls an LLM, figures out what you were working on, and pushes an update to whatever PM tool you use.

The binary is 5MB. The AI runs locally on Ollama if you want. The whole thing runs offline.

Here's what the commit flow actually looks like now:

```bash
$ git add backend/auth/session.py
$ devtrack git commit -m "fix session expiry on token refresh"
```

What happens next, without me touching anything:

1. The commit message goes through an AI pass — not to rewrite it, just to enrich it with context (branch name, open PR, recent related commits)
2. The NLP layer extracts that this touched auth, cross-references my open Azure work items
3. A comment gets posted on the relevant ticket: *"Session expiry fix applied — token refresh flow updated in commit a3f91c"*
4. The ticket moves from "In Progress" to "Review" because the branch name followed the pattern
5. That evening's standup already has a bullet point waiting for me

The whole thing from `devtrack git commit` to ticket comment: about 4 seconds.

---

## The Numbers After Six Months

I've been running this on my own projects since October. Here's what the logs actually say:

- **~23 minutes saved per day** on ticket updates, standup prep, and EOD reports
- **94% of work items updated automatically** — the 6% that missed were commits on branches I'd explicitly told it to ignore
- **Standup is pre-written 4 out of 5 days** — I edit it, I don't write it
- **Zero nights** of 11pm manual Jira sessions since January

That last one is the one that still surprises me. Not because the automation is perfect — it isn't — but because the bar for "good enough to post" is so much lower than I thought. A ticket comment that says *"touched auth layer, see commit a3f91c"* is genuinely more useful than the nothing that was there before.

---

## The Part I'm Still Not Proud Of

Setting up Ollama for the first time is a pain. If you've never done it, you'll spend 45 minutes figuring out which model to pull, why the first model you tried is too slow, and what `nomic-embed-text` is and why you apparently need it.

The documentation exists but it's scattered, and I'm only now admitting that this is my fault not Ollama's.

Also, the `.env` setup has 12 required variables. I know. I needed them all for different things and at some point the config grew teeth. There's a sample file, but I know what it looks like to someone encountering it for the first time. I'm working on a `devtrack setup` wizard that holds your hand through the first run.

---

## The Part That Still Feels Like Magic

The personalization feature. I spent a month building a pipeline that reads your Teams messages, extracts how you communicate, and makes the AI generate updates *in your voice*. The standup bullets sound like me — short sentences, no filler words, specific rather than vague.

My manager asked me last month if I'd started writing better status updates.

I said yes.

---

## What's Actually Shipping Today

DevTrack v1.0 went out this morning. Multi-platform binaries on GitHub Releases — macOS arm64/amd64, Linux arm64/amd64. Fully local, no account, no API key required if you use Ollama.

The features I actually use every day:
- Git commit interception with AI enhancement
- Azure DevOps, GitHub, and Jira PM sync
- Ticket alerter (no more tab-switching to check if something was assigned to me)
- EOD report generator that pulls from the day's commit history
- `git-sage` — an agentic git tool for the messy stuff (rebases, conflict resolution, squash flows)

The features I built but use less often: GitLab integration, the Telegram bot for remote prompts, the Teams learning pipeline. They work, they're just not part of my daily loop.

---

## The Honest Pitch

If you spend more than 15 minutes a day updating tickets or writing standup notes by hand, DevTrack will probably save you time. If your team uses Azure DevOps or GitHub, it'll save you more.

If you want it to run entirely on your machine, on a local model, with no data leaving your laptop — it does that. That was actually the point.

If you want a 60-second demo: `git commit`, watch a ticket comment appear. That's the whole thing.

The code is at [github.com/sraj0501/automation_tools](https://github.com/sraj0501/automation_tools). The Google Sheet is retired. The cron job is gone. Apps Script never knew what hit it.

---

*Next post: I'm building a local-first admin console for the server mode, and a two-month experiment starts Monday where an AI agent does all my commits while I watch and write about what happens. Should be either enlightening or a disaster. Probably both.*
