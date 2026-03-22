# Installation Guide

DevTrack is a native Go binary with a Python backend. No Docker required for local use.

---

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| Git | 2.0+ | To clone the repo |
| Go | 1.20+ | Builds the `devtrack` binary |
| Python | 3.12+ | Runs the AI/NLP backend |
| uv | latest | Python package manager ([astral.sh/uv](https://astral.sh/uv)) |
| Ollama | latest | Optional — local LLM. Can use OpenAI/Anthropic/Groq instead |

---

## Quickest Path — Setup Script (macOS & Linux)

```bash
git clone https://github.com/sraj0501/automation_tools.git
cd automation_tools
chmod +x setup_local.sh
./setup_local.sh
```

The script handles everything: dependency checks, Python env, spaCy model, Go build, `~/.local/bin` install, and `.env` bootstrap. Follow the prompts.

---

## Manual Installation

If you prefer to run steps yourself or are on Windows:

### 1. Clone

```bash
git clone https://github.com/sraj0501/automation_tools.git
cd automation_tools
```

### 2. Install system dependencies

#### macOS
```bash
brew install go python@3.12
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Linux (Ubuntu/Debian)
```bash
# Go
wget https://go.dev/dl/go1.22.3.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.3.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc && source ~/.bashrc

# Python + uv
sudo apt install python3.12 python3.12-venv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows
```powershell
scoop install go python uv    # requires Scoop: scoop.sh
```
> **Note:** `devtrack git commit` (AI commit enhancement) requires WSL or Git Bash on Windows as it depends on a shell script. All other commands work natively.

### 3. Install Python dependencies

```bash
uv sync
uv run python -m spacy download en_core_web_sm
```

### 4. Build the Go binary

```bash
cd devtrack-bin
go build -o devtrack .
mkdir -p ~/.local/bin
cp devtrack ~/.local/bin/
cp devtrack ..          # also keep a copy in project root
cd ..
```

Add to PATH if needed:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc  # or ~/.bashrc
source ~/.zshrc
```

### 5. Configure `.env`

```bash
cp .env_sample .env
nano .env   # or your editor of choice
```

Three variables are required to start:

| Variable | Example | Description |
|---|---|---|
| `PROJECT_ROOT` | `/home/you/automation_tools` | Absolute path to this directory |
| `DEVTRACK_WORKSPACE` | `/home/you/myproject` | Git repo DevTrack monitors |
| `DATA_DIR` | `${PROJECT_ROOT}/Data` | Where logs, DB, and reports are stored |

See [CONFIGURATION.md](CONFIGURATION.md) for all variables.

### 6. Start DevTrack

```bash
devtrack start
devtrack status
```

### 7. Optional: Shell Integration

Enable `git commit` to route through DevTrack without the `devtrack` prefix:

```bash
# Add to ~/.zshrc or ~/.bashrc
echo 'eval "$(devtrack shell-init)"' >> ~/.zshrc
source ~/.zshrc
```

Then opt repos in:

```bash
cd /path/to/your/repo
devtrack enable-git      # sets git config devtrack.enabled=true
```

After this, `git commit` in that repo runs the full DevTrack AI enhancement flow. To undo: `devtrack disable-git`. Repos listed in `workspaces.yaml` are intercepted automatically — no `enable-git` needed.

See [Git Features](GIT_FEATURES.md) for details.

---

## Optional: Ollama (Local AI)

Ollama runs LLMs locally so no data leaves your machine:

```bash
# Install: https://ollama.com/download
ollama pull llama3          # or mistral, phi3, etc.
ollama serve                # start the server

# macOS background service
brew services start ollama
```

Set in `.env`:
```bash
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
GIT_SAGE_DEFAULT_MODEL=llama3
```

To use a cloud provider instead, see [LLM Guide](LLM_GUIDE.md).

---

## Verification

```bash
devtrack status                                          # daemon running?
uv run python -c "import spacy; spacy.load('en_core_web_sm'); print('NLP OK')"
curl http://localhost:11434/api/tags                     # Ollama OK? (if using)
devtrack help                                            # all commands
```

---

## Uninstall

```bash
devtrack stop
rm ~/.local/bin/devtrack
rm -rf /path/to/automation_tools      # removes everything including Data/
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `devtrack: command not found` | Run `source ~/.zshrc` or check `echo $PATH` contains `~/.local/bin` |
| `spaCy model not found` | `uv run python -m spacy download en_core_web_sm` |
| `IPC connection failed` | Check port: `lsof -i :35893`. Change `IPC_PORT` in `.env` if in use |
| `.env not found` | `cp .env_sample .env` from the project root |
| `Ollama unreachable` | `ollama serve` in a separate terminal |
| `git commit` still uses plain git | Run `source ~/.zshrc`, or check that `eval "$(devtrack shell-init)"` is in your shell config |

More: [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**Next:** [Quick Start Guide](QUICK_START.md) — get up and running in 5 minutes.
