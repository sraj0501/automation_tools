"""
Centralized configuration for DevTrack backend.

Loads all configurable values from .env file at project root.
All backend modules should import from this module instead of using os.getenv directly.
"""

import os
from pathlib import Path
from typing import Optional

# Load .env from project root - must be called before any config access
_env_loaded = False


def _find_project_root() -> Path:
    """Find project root by looking for .env or .git in parent directories."""
    # Check DEVTRACK_ENV_FILE or PROJECT_ROOT first
    env_file = os.getenv("DEVTRACK_ENV_FILE")
    if env_file and Path(env_file).exists():
        return Path(env_file).parent

    project_root = os.getenv("PROJECT_ROOT")
    if project_root:
        p = Path(project_root).expanduser()
        if p.exists():
            return p

    # Walk up from this file's location
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / ".env").exists():
            return current
        if (current / ".env_sample").exists():
            return current
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Fallback: parent of backend/ is project root
    return Path(__file__).resolve().parent.parent


def _load_env() -> None:
    """Load .env from project root. Idempotent."""
    global _env_loaded
    if _env_loaded:
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        _env_loaded = True
        return

    project_root = _find_project_root()
    env_paths = [
        project_root / ".env",
        project_root / ".env_sample",
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            _env_loaded = True
            return

    _env_loaded = True


def get(key: str, default: Optional[str] = None) -> str:
    """Get config value. Loads .env on first access."""
    _load_env()
    return os.getenv(key, default or "")


def get_int(key: str, default: int = 0) -> int:
    """Get config value as integer."""
    val = get(key)
    if not val:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


def get_bool(key: str, default: bool = False) -> bool:
    """Get config value as boolean."""
    val = get(key, "").lower().strip()
    if not val:
        return default
    return val in ("true", "1", "yes", "on")


def get_path(key: str, default: Optional[str] = None) -> Path:
    """Get config value as expanded path."""
    val = get(key, default)
    if not val:
        return Path(default or ".").expanduser()
    return Path(val).expanduser()


# --- Project paths ---
def project_root() -> Path:
    """Project root directory."""
    return _find_project_root()


def database_path() -> Path:
    """Full path to SQLite database. From .env: DATABASE_DIR, DATA_DIR, or PROJECT_ROOT/Data/db."""
    db_dir = get("DATABASE_DIR")
    db_file = get("DATABASE_FILE_NAME") or "devtrack.db"
    if db_dir:
        return get_path("DATABASE_DIR") / db_file
    data_dir = get("DATA_DIR")
    if data_dir:
        return get_path("DATA_DIR") / "db" / db_file
    proot = get("PROJECT_ROOT")
    if proot:
        return get_path("PROJECT_ROOT") / "Data" / "db" / db_file
    return project_root() / "Data" / "db" / db_file


def reports_dir() -> Path:
    """Directory for saved reports. From .env: DATA_DIR or PROJECT_ROOT/Data."""
    data_dir = get("DATA_DIR")
    if data_dir:
        return get_path("DATA_DIR") / "reports"
    proot = get("PROJECT_ROOT")
    if proot:
        return get_path("PROJECT_ROOT") / "Data" / "reports"
    return project_root() / "Data" / "reports"


def learning_dir() -> Path:
    """Directory for learning data. From .env: LEARNING_DIR_PATH or PROJECT_ROOT/Data/learning."""
    learning_path = get("LEARNING_DIR_PATH")
    if learning_path:
        return get_path("LEARNING_DIR_PATH")
    proot = get("PROJECT_ROOT")
    if proot:
        return get_path("PROJECT_ROOT") / "Data" / "learning"
    return project_root() / "Data" / "learning"


def log_dir() -> Path:
    """Directory for log files. From .env: LOG_DIR or PROJECT_ROOT/Data/logs."""
    log_path = get("LOG_DIR")
    if log_path:
        return get_path("LOG_DIR")
    proot = get("PROJECT_ROOT")
    if proot:
        return get_path("PROJECT_ROOT") / "Data" / "logs"
    return project_root() / "Data" / "logs"


# --- Ollama ---
def ollama_host() -> str:
    """Ollama API host URL."""
    return get("OLLAMA_HOST", "http://localhost:11434")


def ollama_model() -> str:
    """Default Ollama model for AI tasks."""
    return get("OLLAMA_MODEL", "llama3.2")


# --- IPC ---
def ipc_host() -> str:
    """IPC server host."""
    return get("IPC_HOST", "127.0.0.1")


def ipc_port() -> str:
    """IPC server port."""
    return get("IPC_PORT", "35893")


# --- Azure DevOps (supports both AZURE_DEVOPS_PAT and AZURE_API_KEY for compatibility) ---
def azure_pat() -> str:
    """Azure DevOps Personal Access Token."""
    return get("AZURE_DEVOPS_PAT") or get("AZURE_API_KEY", "")


def azure_org() -> str:
    """Azure DevOps organization."""
    return get("ORGANIZATION", "")


def azure_project() -> str:
    """Azure DevOps project."""
    return get("PROJECT", "")


# --- Task generation defaults (from env, no hardcoded personal data) ---
def azure_default_assignee() -> str:
    """Default assignee for generated tasks."""
    return get("AZURE_DEFAULT_ASSIGNEE", "")


def azure_parent_work_item_id() -> str:
    """Parent work item ID for task hierarchy."""
    return get("AZURE_PARENT_WORK_ITEM_ID", "")


def azure_starting_work_item_id() -> int:
    """Starting work item ID for new tasks."""
    return get_int("AZURE_STARTING_WORK_ITEM_ID", 0)


# --- Sentiment / Chat analysis ---
def sentiment_target_sender() -> str:
    """Target sender name for responsiveness analysis."""
    return get("SENTIMENT_TARGET_SENDER", "")


# --- GitHub ---
def github_token() -> str:
    """GitHub Personal Access Token."""
    return get("GITHUB_TOKEN", "")


def timezone() -> str:
    """Default timezone for date handling."""
    return get("TIMEZONE", "Asia/Kolkata")


def log_file_path() -> Path:
    """Path for GitHub analysis log file."""
    return log_dir() / "github_branch_analysis.log"


# --- Semantic model ---
def semantic_model_name() -> str:
    """Sentence transformer model for task matching."""
    return get("SEMANTIC_MODEL_NAME", "all-MiniLM-L6-v2")


# --- Excel / Azure updator ---
def azure_excel_file() -> Path:
    """Path to Excel file for Azure task import."""
    excel = get("AZURE_EXCEL_FILE")
    if excel:
        return get_path("AZURE_EXCEL_FILE")
    return project_root() / "backend" / "data" / "tasks.xlsx"


def azure_excel_sheet() -> str:
    """Sheet name in Excel file."""
    return get("AZURE_EXCEL_SHEET", "my_tasks")
