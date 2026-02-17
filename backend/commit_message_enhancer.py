#!/usr/bin/env python3
"""
Git Commit Message Enhancer

This script is called by git's prepare-commit-msg hook to enhance commit messages
using AI analysis of staged changes.
"""

import os
import sys
import subprocess
import logging
import requests
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CommitMessageEnhancer:
    """Enhances git commit messages using AI analysis of staged changes"""
    
    def __init__(self, ollama_host: Optional[str] = None, ollama_model: Optional[str] = None):
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "gemma3:12b")
        
    def get_staged_diff(self, repo_path: str) -> Optional[str]:
        """Get diff of staged changes"""
        try:
            # Get stats
            result = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get diff stats: {result.stderr}")
                return None
            
            stats = result.stdout.strip()
            
            # Get actual diff (limited)
            result = subprocess.run(
                ["git", "diff", "--cached", "--unified=3"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return stats
            
            diff = result.stdout
            
            # Limit diff size
            max_lines = 150
            diff_lines = diff.split('\n')
            if len(diff_lines) > max_lines:
                diff = '\n'.join(diff_lines[:max_lines]) + '\n\n... (diff truncated)'
            
            return f"{stats}\n\n{diff}"
            
        except Exception as e:
            logger.error(f"Error getting staged diff: {e}")
            return None
    
    def get_staged_files(self, repo_path: str) -> list:
        """Get list of staged files"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            return []
        except Exception:
            return []
    
    def enhance_message_with_ai(self, original_message: str, diff: str, files: list) -> str:
        """Use AI to enhance/generate commit message"""
        try:
            files_list = "\n".join([f"  - {f}" for f in files[:10]])
            if len(files) > 10:
                files_list += f"\n  ... and {len(files) - 10} more"
            
            # Check if original message is meaningful or just placeholder
            is_placeholder = (
                not original_message or 
                original_message.strip() in ["", "temp", "wip", "update", "fix", "test"] or
                len(original_message.strip()) < 5
            )
            
            if is_placeholder:
                prompt = f"""You are writing a git commit message. Analyze the code changes and write a clear, professional commit message.

Files Changed ({len(files)}):
{files_list}

Code Changes:
{diff[:2000]}

REQUIREMENTS:
1. First line: Brief summary of WHAT changed (under 72 characters)
2. Blank line
3. Body (2-4 sentences): Explain WHY this change was made and what problem it solves

GOOD EXAMPLE:
Add interactive feedback prompt after commit

Provides immediate confirmation when commits are created, showing users
what was logged and which systems were updated. This improves user
confidence and helps track work more effectively.

BAD EXAMPLE (DO NOT DO THIS):
Update files

Changed some code.

Write ONLY the commit message. DO NOT include options, explanations, meta-commentary, or anything except the commit message itself."""
            else:
                prompt = f"""You are improving a git commit message. Analyze the code changes and rewrite the message to be more informative.

Original Message: {original_message}

Files Changed ({len(files)}):
{files_list}

Code Changes:
{diff[:2000]}

REQUIREMENTS:
1. First line: Improved summary of WHAT changed (under 72 characters)
2. Blank line  
3. Body (2-4 sentences): Explain WHY this change was made and its benefits

GOOD EXAMPLE:
Fix authentication timeout in user sessions

Resolves issue where users were logged out unexpectedly after 5 minutes
of inactivity. Updates session timeout to 30 minutes and adds proper
refresh logic to improve user experience.

BAD EXAMPLE (DO NOT DO THIS):
Fixed bug

Made some changes to auth.

Write ONLY the improved commit message. DO NOT include options, explanations, meta-commentary, or anything except the commit message itself."""

            # Call Ollama
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Lower temperature for more focused output
                        "num_predict": 200   # Allow space for body paragraphs
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return original_message
            
            result = response.json()
            enhanced = result.get("response", "").strip()
            
            # Clean up response - remove markdown, meta-commentary, and formatting
            enhanced = enhanced.replace("```", "").strip()
            
            # Remove common meta-commentary patterns
            meta_patterns = [
                "Here's", "here's", "Okay,", "Option ", "OPTION ",
                "I've aimed", "Choose the", "This is", "Let me"
            ]
            for pattern in meta_patterns:
                if enhanced.startswith(pattern):
                    # Find first newline and take everything after
                    lines = enhanced.split('\n')
                    for i, line in enumerate(lines):
                        if not any(p in line for p in meta_patterns):
                            enhanced = '\n'.join(lines[i:])
                            break
            
            # If AI response is empty or looks wrong, return original
            if not enhanced or len(enhanced) < 5 or enhanced.startswith("I "):
                return original_message
            
            return enhanced
            
        except requests.exceptions.Timeout:
            logger.warning("Ollama timeout, using original message")
            return original_message
        except Exception as e:
            logger.error(f"Error enhancing message: {e}")
            return original_message
    
    def process_commit_message(self, commit_msg_file: str, repo_path: str) -> bool:
        """
        Main entry point: enhance the commit message file
        
        Args:
            commit_msg_file: Path to the COMMIT_EDITMSG file
            repo_path: Path to the git repository
            
        Returns:
            True if message was enhanced, False otherwise
        """
        try:
            # Read original message
            with open(commit_msg_file, 'r') as f:
                original = f.read()
            
            # Remove comment lines
            lines = original.split('\n')
            message_lines = [l for l in lines if not l.startswith('#')]
            original_message = '\n'.join(message_lines).strip()
            
            # Get staged changes
            diff = self.get_staged_diff(repo_path)
            if not diff:
                logger.warning("No staged changes found")
                return False
            
            files = self.get_staged_files(repo_path)
            if not files:
                logger.warning("No staged files found")
                return False
            
            logger.info(f"Enhancing commit message with AI ({len(files)} files changed)...")
            
            # Enhance with AI
            enhanced = self.enhance_message_with_ai(original_message, diff, files)
            
            if enhanced == original_message:
                logger.info("No enhancement needed or AI unavailable")
                return False
            
            # Write enhanced message back (clean, no metadata)
            with open(commit_msg_file, 'w') as f:
                f.write(enhanced)
                # Add back the git comments
                comment_lines = [l for l in lines if l.startswith('#')]
                if comment_lines:
                    f.write('\n\n')
                    f.write('\n'.join(comment_lines))
                    f.write('\n')
            
            logger.info("✓ Commit message enhanced")
            return True
            
        except Exception as e:
            logger.error(f"Error processing commit message: {e}")
            return False


def main():
    """CLI entry point for git hook"""
    if len(sys.argv) < 2:
        print("Usage: commit_message_enhancer.py <commit-msg-file> [commit-source] [commit-sha]")
        sys.exit(1)
    
    commit_msg_file = sys.argv[1]
    commit_source = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Don't enhance if this is a merge or squash (but DO enhance for 'message', 'commit', etc.)
    if commit_source in ['merge', 'squash']:
        sys.exit(0)
    
    # Get repo path from environment variable (set by git hook) or use cwd
    repo_path = os.getenv('GIT_DIR')
    if repo_path and repo_path.endswith('.git'):
        repo_path = os.path.dirname(repo_path)
    if not repo_path or not os.path.exists(repo_path):
        repo_path = os.getcwd()
    
    # Try to find .git directory in parents if not at repo root
    check_path = repo_path
    for _ in range(5):  # Check up to 5 levels up
        if os.path.exists(os.path.join(check_path, '.git')):
            repo_path = check_path
            break
        parent = os.path.dirname(check_path)
        if parent == check_path:  # Reached root
            break
        check_path = parent
    
    logger.info(f"Working in repository: {repo_path}")
    logger.info(f"Commit source: {commit_source or 'manual'}")
    
    # Load env vars
    try:
        from dotenv import load_dotenv
        env_paths = [
            Path.home() / ".devtrack" / ".env",
            Path.home() / "Documents" / "GitHub" / "automation_tools" / ".env",
        ]
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded env from: {env_path}")
                break
    except ImportError:
        pass
    
    enhancer = CommitMessageEnhancer()
    enhancer.process_commit_message(commit_msg_file, repo_path)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
