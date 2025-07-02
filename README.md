# AI-Powered Task Management System

> An intelligent assistant that converts natural language daily updates into structured task management and automated progress reports.

## 🎯 Project Overview

This system acts as your personal AI-powered project management assistant that:
- Takes natural language input about your daily work
- Updates Microsoft Lists with task progress
- Generates professional email reports for your manager
- Creates intelligent subtasks for complex activities
- Learns your patterns and improves over time

## 🚀 Core Workflow

```
You → AI Agent → Parse Activities → Update MS Lists → Generate Email → Send to Manager
             ↓
        Create Subtasks (when needed)
```

### Example Interaction
```
You: "Today I completed the database migration, started working on the API endpoints, 
      and had a meeting with the design team about the new UI mockups"

AI: "I've updated your tasks:
     ✅ Database Migration → Completed
     🔄 API Development → In Progress  
     📝 UI Design Review → New task created
     
     Should I create subtasks for API Development?"
```

## 🏗️ System Architecture

### Input Processing Pipeline
```
Raw Input → NLP Processing → Task Extraction → Fuzzy Matching → 
Status Updates → Subtask Generation → Email Composition → Send
```

### Data Flow
- **Input Sources**: Daily voice/text updates, MS Lists current state, calendar events
- **AI Processing**: Natural language understanding, task matching, progress analysis
- **Output Destinations**: Updated MS Lists, manager email reports, personal analytics

## 🧠 AI Components

### 1. Task Parser Module
- **Entity Recognition**: Extract task names, dates, people, priorities
- **Action Classification**: Detect completed/started/blocked/delayed status
- **Time Estimation**: Track time spent on activities
- **Context Understanding**: Link activities to existing projects

### 2. Task Matcher Module
- **Semantic Search**: Find similar existing tasks using AI similarity
- **Fuzzy Matching**: Handle variations in task naming
- **Confidence Scoring**: Measure certainty of task matches
- **Disambiguation**: Ask clarifying questions when unsure

### 3. Subtask Generator Module
- **Complexity Analysis**: Determine if tasks need breakdown
- **Domain Knowledge**: Apply best practices for different task types
- **Dependency Detection**: Identify task relationships
- **Template-Based**: Use proven subtask patterns

### 4. Progress Analyzer Module
- **Trend Analysis**: Track productivity patterns over time
- **Bottleneck Detection**: Identify recurring delays
- **Goal Tracking**: Monitor progress toward deadlines
- **Recommendation Engine**: Suggest workflow improvements

## 📚 Technology Stack

### AI/ML Libraries
- **OLLAMA** - Local LLM for text understanding and generation
- **spaCy** - Named Entity Recognition (NER) for task extraction
- **sentence-transformers** - Semantic similarity matching for tasks
- **fuzzywuzzy** - Fuzzy string matching for task names
- **transformers** (Hugging Face) - Advanced NLP tasks

### Microsoft Integration
- **msgraph-sdk-python** - Microsoft Lists and Email APIs
- **msal** - Microsoft Authentication Library
- **Office 365 APIs** - SharePoint Lists integration

### Natural Language Processing
- **nltk** or **spaCy** - Text preprocessing and tokenization
- **dateparser** - Parse natural language dates ("tomorrow", "next week")
- **regex** - Pattern matching for text parsing

### Data Processing
- **pandas** - Data manipulation for task analysis
- **json** - Structured data handling
- **sqlite3** - Local learning database

### Optional Enhancements
- **speech_recognition** - Voice input capability
- **pyttsx3** - Text-to-speech for AI responses
- **schedule** - Automated daily/weekly triggers

## 🔧 Required Permissions

### Microsoft Graph API Scopes
```python
graphUserScopes = [
    "User.Read",           # Read user profile
    "Mail.Send",           # Send emails  
    "Sites.Read.All",      # Read SharePoint Lists
    "Sites.ReadWrite.All"  # Update SharePoint Lists
]
```

## 🎯 Feature Roadmap

### Phase 1: Basic AI Parser
- [ ] Simple task extraction from natural language
- [ ] Manual Microsoft Lists integration
- [ ] Basic email template generation
- [ ] Core NLP processing pipeline

### Phase 2: Smart Matching
- [ ] Fuzzy matching for existing tasks
- [ ] Confidence scoring and disambiguation
- [ ] Improved natural language understanding
- [ ] Learning from user corrections

### Phase 3: Subtask Intelligence
- [ ] Automated subtask generation
- [ ] Task complexity analysis
- [ ] Template-based recommendations
- [ ] Dependency tracking

### Phase 4: Advanced Analytics
- [ ] Productivity pattern analysis
- [ ] Predictive suggestions
- [ ] Manager communication optimization
- [ ] Cross-platform integration

## 📋 Example Use Cases

### Daily Status Update
```
Input: "Finished client presentation, made progress on budget analysis, 
        started new feature documentation"

AI Processing:
1. Maps "client presentation" → Existing task: "Q4 Client Pitch"
2. Updates status to "Completed"
3. Creates progress update for "Budget Analysis" 
4. Creates new task "Feature Documentation"
5. Generates email summary for manager
```

### Intelligent Subtask Creation
```
User: "Working on API development"
AI: "I notice 'API Development' is a complex task. Should I break it down?

Suggested subtasks:
- Design API endpoints
- Implement authentication  
- Create data models
- Write unit tests
- Update documentation"
```

### Automated Email Report
```
Subject: Daily Progress Update - [Date]

Hi [Manager],

Here's my progress summary for today:

✅ Completed:
- Database Migration (Project Alpha)
- Client Presentation Prep

🔄 In Progress:  
- API Development (60% complete)
- Budget Analysis (Review phase)

📝 Started Today:
- Feature Documentation
- UI Design Review

Tomorrow's Focus:
- Complete API authentication module
- Finish budget analysis review

Best regards,
[Your Name]
```

## 🔄 Implementation Considerations

### Data Privacy
- All AI processing can be done locally using OLLAMA
- Sensitive data stays within your organization
- Optional cloud AI for enhanced capabilities

### Learning & Adaptation
- System learns your communication patterns
- Adapts to manager's preferred report style
- Improves task matching accuracy over time

### Integration Points
- **Calendar**: Factor in meetings and availability
- **Email**: Learn from manager responses
- **Teams/Slack**: Cross-reference project discussions
- **Time Tracking**: Integrate with existing tools

## 🚀 Getting Started

### Prerequisites
1. Microsoft 365 account with Lists access
2. Python 3.8+ environment
3. OLLAMA installed locally
4. Required Python packages (see requirements.txt)

### Installation Steps
```bash
# Clone repository
git clone [repository-url]
cd ai-task-manager

# Install dependencies
pip install -r requirements.txt

# Set up Microsoft Graph credentials
cp config.example.cfg config.cfg
# Edit config.cfg with your Azure app details

# Install and start OLLAMA
# Download from https://ollama.ai
ollama pull llama3.1

# Run setup
python setup.py
```

### Basic Usage
```bash
# Start the AI assistant
python ai_assistant.py

# Daily update mode
python ai_assistant.py --mode daily

# Voice input mode  
python ai_assistant.py --voice
```

## 📊 Advanced Features

### Context Awareness
- **Project Phases**: Understands different project stages
- **Team Dependencies**: Knows when waiting for others
- **Deadline Proximity**: Adjusts urgency based on due dates

### Proactive Intelligence
- **Tomorrow's Plan**: Suggests next day priorities
- **Blocker Resolution**: Identifies stuck tasks needing attention
- **Resource Allocation**: Analyzes time distribution patterns

### Communication Optimization
- **Manager Preferences**: Adapts email tone and detail level
- **Team Updates**: Cross-references with team communications
- **Progress Visualization**: Creates charts and progress indicators

## 🤝 Contributing

This is a personal productivity system designed for individual use. However, contributions and suggestions are welcome:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with detailed description

## 📄 License

[Choose appropriate license - MIT recommended for personal tools]

## 🔗 Related Projects

- [Microsoft Graph Python SDK](https://github.com/microsoftgraph/msgraph-sdk-python)
- [OLLAMA](https://ollama.ai/)
- [spaCy](https://spacy.io/)
- [Sentence Transformers](https://www.sbert.net/)

## 📞 Support

For questions or issues:
- Create an issue in this repository
- Check the documentation wiki
- Review example configurations

---

**Note**: This system is designed for individual productivity enhancement and requires appropriate Microsoft 365 licensing and permissions.