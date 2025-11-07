# Personalized AI Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER INTERACTIONS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. devtrack enable-learning  ← Enable & collect data          │
│  2. devtrack learning-status  ← Check learning progress        │
│  3. devtrack show-profile     ← View learned patterns          │
│  4. devtrack test-response    ← Generate personalized text     │
│  5. devtrack revoke-consent   ← Delete data & disable          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         GO CLI LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  learning.go                                                     │
│  ├─ EnableLearning()    → Execute Python learning script        │
│  ├─ ShowProfile()       → Display learned profile               │
│  ├─ GetLearningStatus() → Read consent/samples/profile files    │
│  └─ RevokeConsent()     → Remove data files                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       PYTHON BRIDGE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  learning_integration.py                                         │
│  └─ LearningIntegration                                         │
│      ├─ initialize()           → Setup with MS Graph            │
│      ├─ collect_teams_data()   → Gather communication samples   │
│      ├─ show_profile()         → Display analysis results       │
│      └─ test_response_generation() → Generate personalized text │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
           ┌──────────────────┴──────────────────┐
           ↓                                      ↓
┌──────────────────────────┐      ┌──────────────────────────────┐
│   DATA COLLECTORS        │      │    PERSONALIZED AI           │
├──────────────────────────┤      ├──────────────────────────────┤
│                          │      │                              │
│ data_collectors.py       │      │ personalized_ai.py           │
│                          │      │                              │
│ ┌──────────────────────┐ │      │ ┌──────────────────────────┐ │
│ │ TeamsDataCollector   │ │      │ │ PersonalizedAI           │ │
│ │  - Chat history      │ │      │ │  - Consent management    │ │
│ │  - User responses    │ │      │ │  - Sample storage        │ │
│ │  - Context tracking  │ │      │ │  - Style analysis        │ │
│ └──────────────────────┘ │      │ │  - Response generation   │ │
│                          │      │ └──────────────────────────┘ │
│ ┌──────────────────────┐ │      │                              │
│ │ AzureDataCollector   │ │      │ ┌──────────────────────────┐ │
│ │  - Work item comments│ │      │ │ CommunicationSample      │ │
│ │  - Discussion replies│ │      │ │  - trigger               │ │
│ │  - Code review notes │ │      │ │  - response              │ │
│ └──────────────────────┘ │      │ │  - source/context        │ │
│                          │      │ │  - metadata              │ │
│ ┌──────────────────────┐ │      │ └──────────────────────────┘ │
│ │ OutlookCollector     │ │      │                              │
│ │  - Sent emails       │ │      │ ┌──────────────────────────┐ │
│ │  - Email replies     │ │      │ │ UserProfile              │ │
│ │  - Threading         │ │      │ │  - writing_style         │ │
│ └──────────────────────┘ │      │ │  - response_patterns     │ │
│                          │      │ │  - vocabulary            │ │
└──────────────────────────┘      │ │  - sign_offs/greetings   │ │
           ↓                       │ └──────────────────────────┘ │
┌──────────────────────────┐      │                              │
│  MS GRAPH API            │      └──────────────────────────────┘
├──────────────────────────┤                    ↓
│                          │      ┌──────────────────────────────┐
│ - Chat.Read             │      │     OLLAMA (LOCAL AI)         │
│ - Mail.Read             │      ├──────────────────────────────┤
│ - User.Read             │      │                              │
│                          │      │  - llama2 model              │
│ Teams ─────────┐         │      │  - Local processing          │
│ Outlook ───────┼────→    │      │  - No cloud calls            │
│ Azure DevOps ──┘         │      │  - Response generation       │
│                          │      │                              │
└──────────────────────────┘      └──────────────────────────────┘
                                                ↓
                              ┌─────────────────────────────────┐
                              │   LOCAL STORAGE                 │
                              ├─────────────────────────────────┤
                              │                                 │
                              │  ~/.devtrack/learning/          │
                              │  ├─ consent.json                │
                              │  ├─ samples.json                │
                              │  └─ profile.json                │
                              │                                 │
                              └─────────────────────────────────┘
```

## Data Flow

### 1. Collection Phase

```
User: devtrack enable-learning 30
   ↓
Go CLI: learning.go:EnableLearning()
   ↓
Python: learning_integration.py:collect_teams_data()
   ↓
Check Consent → personalized_ai.py:consent_given
   ↓
IF NOT GIVEN → Request consent → Save to consent.json
   ↓
Collectors: data_collectors.py
   ├─ TeamsDataCollector.collect_chat_history_async()
   │    ↓
   │  MS Graph API: GET /chats
   │    ↓
   │  For each chat:
   │    GET /chats/{id}/messages
   │    ↓
   │  Extract trigger-response pairs
   │    ↓
   │  Save: personalized_ai.py:add_communication_sample()
   │
   ├─ AzureDataCollector.collect_comments_history()
   │    ↓
   │  Azure DevOps API: GET work items
   │    ↓
   │  Extract comment threads
   │    ↓
   │  Save: add_communication_sample()
   │
   └─ OutlookCollector.collect_sent_emails()
        ↓
      MS Graph API: GET /me/mailFolders/sentItems
        ↓
      Extract email replies
        ↓
      Save: add_communication_sample()
   ↓
All samples → samples.json
   ↓
Update Profile → personalized_ai.py:_update_profile()
   ↓
Analyze samples:
   ├─ _analyze_writing_style()
   ├─ _analyze_response_patterns()
   └─ _analyze_vocabulary()
   ↓
Build UserProfile → profile.json
   ↓
Display: "✅ 347 samples collected"
```

### 2. Learning Phase (Automatic)

```
personalized_ai.py:_update_profile()
   ↓
Read all samples from samples.json
   ↓
┌─────────────────────────────────────┐
│ Writing Style Analysis              │
├─────────────────────────────────────┤
│                                     │
│ For each response:                  │
│   - Count sentences                 │
│   - Calculate avg length            │
│   - Detect tone (formal/casual)     │
│   - Check exclamation marks         │
│   - Check emojis                    │
│                                     │
│ Result: writing_style dict         │
│   {                                 │
│     "tone": "casual",               │
│     "formality": "informal",        │
│     "avg_sentence_length": 15,      │
│     "uses_exclamation": true        │
│   }                                 │
└─────────────────────────────────────┘
   ↓
┌─────────────────────────────────────┐
│ Response Pattern Analysis           │
├─────────────────────────────────────┤
│                                     │
│ Group by context_type:              │
│   - question responses              │
│   - request responses               │
│   - feedback responses              │
│                                     │
│ Extract common starts:              │
│   - "Sure, I can..."               │
│   - "Good question..."             │
│   - "Let me explain..."            │
│                                     │
│ Result: response_patterns dict      │
└─────────────────────────────────────┘
   ↓
┌─────────────────────────────────────┐
│ Vocabulary Analysis                 │
├─────────────────────────────────────┤
│                                     │
│ Count word frequency                │
│ Extract common phrases              │
│ Find technical terms                │
│ Detect sign-offs                    │
│ Detect greetings                    │
│                                     │
│ Result: vocabulary dict             │
│   {                                 │
│     "common_words": [words],        │
│     "technical_terms": [terms],     │
│     "common_sign_offs": [signs],    │
│     "common_greetings": [greets]    │
│   }                                 │
└─────────────────────────────────────┘
   ↓
Combine all analyses → UserProfile
   ↓
Save to profile.json
```

### 3. Response Generation Phase

```
User: devtrack test-response "Can you review this?"
   ↓
Go CLI: learning.go:TestResponse()
   ↓
Python: learning_integration.py:test_response_generation()
   ↓
personalized_ai.py:generate_response_suggestion()
   ↓
Load UserProfile from profile.json
   ↓
Analyze trigger:
   - Context: "work" or "casual"?
   - Type: question/request/feedback?
   ↓
Build style prompt from profile:
   """
   Generate a response matching this style:
   - Tone: casual
   - Formality: informal
   - Typical phrases: "Sure, I can...", "Thanks!"
   - Sign-off: Thanks, Cheers
   - Avg sentence: 15 words
   
   Respond to: "Can you review this?"
   """
   ↓
Send to Ollama (LOCAL):
   ollama.chat(
       model='llama2',
       messages=[
           {"role": "system", "content": style_prompt},
           {"role": "user", "content": trigger}
       ]
   )
   ↓
Ollama generates response locally
   ↓
Return: "Sure, I can take a look! I'll review it 
         within the next hour and leave comments 
         if I spot anything. Thanks!"
   ↓
Display to user
```

## Privacy Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PRIVACY CHECKPOINTS                       │
└─────────────────────────────────────────────────────────────┘

BEFORE Collection:
   ↓
Check consent.json → consent_given == true?
   │
   ├─ YES → Proceed with collection
   │
   └─ NO  → Show consent request
            "The AI needs your permission..."
            User input: yes/no
            │
            ├─ yes → Save consent.json → Proceed
            └─ no  → ABORT, no collection

DURING Collection:
   ↓
All data stays local:
   ├─ API calls: Only to fetch data (Teams/Azure/Outlook)
   ├─ Processing: On local machine
   └─ Storage: ~/.devtrack/learning/

DURING Generation:
   ↓
Check consent again
   ↓
All AI processing:
   ├─ Ollama: Local AI (no cloud)
   ├─ Model: Downloaded locally
   └─ No network calls during generation

REVOKE Consent:
   ↓
User: devtrack revoke-consent
   ↓
Confirm: "This will delete all learned data"
   ↓
User confirms
   ↓
Delete all files:
   ├─ consent.json
   ├─ samples.json
   └─ profile.json
   ↓
All data GONE, no traces
```

## File Structure

```
automation_tools/
├─ backend/
│  ├─ personalized_ai.py         ← Core AI learning
│  ├─ data_collectors.py         ← Data collection
│  └─ learning_integration.py    ← Integration layer
│
├─ go-cli/
│  ├─ learning.go                ← CLI commands
│  ├─ cli.go                     ← Command routing
│  └─ PERSONALIZED_AI.md         ← Documentation
│
├─ install_learning_deps.sh      ← Dependency installer
│
├─ PERSONALIZED_AI_QUICKSTART.md ← Quick start
├─ PERSONALIZED_AI_COMPLETE.md   ← Implementation details
└─ PERSONALIZED_AI_FINAL_SUMMARY.md ← This summary

~/.devtrack/
└─ learning/
   ├─ consent.json               ← Consent record
   ├─ samples.json               ← Communication samples
   └─ profile.json               ← Learned profile
```

## Key Design Decisions

### 1. Privacy First
- ALL data local
- NO cloud AI
- Explicit consent REQUIRED
- Full deletion available

### 2. Ollama Only (Per Requirement)
- Uses local Ollama
- No OpenAI/Claude/etc
- Configurable model
- Offline capable

### 3. Separation of Concerns
- Go: CLI & orchestration
- Python: Data & AI processing
- Clear boundaries
- Modular design

### 4. Async Collection
- Non-blocking data fetch
- Parallel collectors
- Progress reporting
- Graceful errors

### 5. Transparent Learning
- JSON storage (human-readable)
- Profile viewing
- Sample inspection
- Clear explanations

## Component Responsibilities

```
┌──────────────────────────────────────────────────────────────┐
│ COMPONENT            │ RESPONSIBILITY                        │
├──────────────────────┼──────────────────────────────────────┤
│ learning.go          │ CLI commands, Python execution        │
│ cli.go               │ Command routing, help text            │
│ learning_integration │ MS Graph integration, orchestration   │
│ data_collectors      │ Fetch data from Teams/Azure/Outlook   │
│ personalized_ai      │ Consent, learning, generation         │
│ Ollama               │ Local AI response generation          │
│ MS Graph API         │ Data source (Teams, Outlook)          │
│ Azure DevOps API     │ Data source (work items)              │
│ ~/.devtrack/learning │ Local persistent storage              │
└──────────────────────┴──────────────────────────────────────┘
```

---

**This architecture ensures:**
- ✅ Complete privacy (all local)
- ✅ User control (explicit consent)
- ✅ Transparency (readable JSON)
- ✅ Performance (async collection)
- ✅ Modularity (clean separation)
- ✅ Extensibility (easy to add sources)
