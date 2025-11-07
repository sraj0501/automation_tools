# Personalized AI - Quick Start Guide

## Installation (5 minutes)

### 1. Install Dependencies
```bash
cd /Users/sraj/git_apps/personal/automation_tools
./install_learning_deps.sh
```

This will install:
- ollama (Python package)
- spacy + en_core_web_sm model
- Ollama (optional, if not already installed)
- llama2 model (optional, ~4GB download)

### 2. Build CLI
```bash
cd go-cli
go build -o devtrack
```

### 3. Verify MS Graph Authentication
```bash
cd backend/msgraph_python
python main.py
```

Follow the device code flow to authenticate.

## First Use (2 minutes)

### Enable Learning
```bash
cd go-cli
./devtrack enable-learning
```

You'll be prompted for consent. Type `yes` to grant.

The system will then:
1. Collect last 30 days of Teams chats
2. Collect Azure DevOps comments
3. Collect Outlook sent emails
4. Analyze your communication patterns
5. Build your personalized profile

**Time:** 2-5 minutes depending on data volume

## Daily Usage

### Check What's Learned
```bash
./devtrack learning-status
```

Shows:
- Learning enabled/disabled
- Number of samples collected
- Last update time

### View Your Profile
```bash
./devtrack show-profile
```

Shows:
- Writing style (tone, formality, sentence length)
- Common phrases and sign-offs
- Response patterns
- Vocabulary statistics

### Generate a Response
```bash
./devtrack test-response "Can you review my code?"
```

AI will generate a response in YOUR style.

### Update Profile (Monthly)
```bash
./devtrack enable-learning 30
```

Re-collects last 30 days to keep profile current as your style evolves.

## Commands Reference

| Command | Description |
|---------|-------------|
| `devtrack enable-learning [days]` | Enable learning, collect data (default 30 days) |
| `devtrack learning-status` | Show learning status and stats |
| `devtrack show-profile` | Display learned communication profile |
| `devtrack test-response <text>` | Test generating a personalized response |
| `devtrack revoke-consent` | Revoke consent and delete learning data |

## Data Location

All learning data stored in:
```
~/.devtrack/learning/
├── consent.json          # Consent record
├── samples.json          # Communication samples
└── profile.json          # Learned profile
```

## Privacy

- ✅ All data stored locally
- ✅ No cloud AI services
- ✅ Explicit consent required
- ✅ Full data deletion on revoke
- ✅ Uses only local Ollama

## Troubleshooting

### "Consent not given" error
```bash
./devtrack enable-learning
# Answer 'yes' when prompted
```

### "Graph client not initialized"
```bash
cd ../backend/msgraph_python
python main.py
# Complete authentication
```

### No samples collected
- Check you have chat/email history in timeframe
- Verify MS Graph permissions include Chat.Read, Mail.Read
- Try increasing days: `./devtrack enable-learning 60`

### Ollama errors
```bash
# Check Ollama is running
ollama list

# Pull model if missing
ollama pull llama2
```

## Example Session

```bash
# First time setup
$ ./devtrack enable-learning

⚠️  Learning consent not given.
    Would you like to grant consent? (yes/no): yes
✅ Consent granted

📥 Collecting communication data...
📱 MS Teams: 198 samples
🔷 Azure DevOps: 89 samples  
📧 Outlook: 60 samples
✅ Total: 347 samples

🧠 Profile updated

# Check what was learned
$ ./devtrack show-profile

╔══════════════════════════════════════════════════════════╗
║            YOUR COMMUNICATION PROFILE                    ║
╚══════════════════════════════════════════════════════════╝

📊 STATISTICS:
   Total Samples: 347
   Teams: 198 | Azure: 89 | Outlook: 60

✍️  WRITING STYLE:
   Tone: Casual
   Formality: Informal
   Avg Sentence: 15 words

📝 COMMON PHRASES:
   Sign-offs: Thanks, Cheers, Best
   Greetings: Hey, Hi there, Hello

# Test it out
$ ./devtrack test-response "What's the status on the feature?"

🤖 GENERATING RESPONSE...

Suggested Response:
──────────────────────────────────────────────────────────
Hey! Good progress on the feature. Just finished the core 
implementation and working on tests now. Should have it 
ready for review by EOD tomorrow.

Thanks for checking in!
──────────────────────────────────────────────────────────
```

## What Gets Learned

The AI learns:

**From Teams:**
- How you respond in chats
- Your casual communication style
- Quick responses vs detailed explanations

**From Azure DevOps:**
- How you give feedback
- Your technical communication
- Code review style

**From Outlook:**
- Professional email tone
- Greetings and sign-offs
- Formal communication patterns

## Tips for Best Results

1. **Collect enough data**: Minimum 50 samples, 200+ ideal
2. **Update regularly**: Re-run monthly as your style evolves
3. **Review suggestions**: AI provides starting points, customize as needed
4. **Specify context**: Use different triggers for formal vs casual
5. **Check your profile**: See what patterns were learned

## Support

- Documentation: `PERSONALIZED_AI.md`
- Status check: `./devtrack learning-status`
- Logs: `~/.devtrack/daemon.log`

---

**Ready to get started?** Run `./install_learning_deps.sh` now! 🚀
