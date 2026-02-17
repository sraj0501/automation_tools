"""
Git Diff Analyzer using Ollama

This module analyzes git diffs when no project management system (Azure DevOps/JIRA) is connected.
It uses Ollama to generate intelligent commit message summaries based on code changes.
"""

import os
import subprocess
import logging
import requests
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class GitDiffAnalyzer:
    """Analyzes git diffs and generates intelligent summaries using Ollama"""
    
    def __init__(self, ollama_host: Optional[str] = None):
        """
        Initialize the Git Diff Analyzer
        
        Args:
            ollama_host: Ollama API endpoint (defaults to env var OLLAMA_HOST)
        """
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama2")  # Default model
        
    def is_project_management_connected(self) -> bool:
        """
        Check if a project management system is connected
        
        Returns:
            True if Azure DevOps, JIRA, or similar is configured
        """
        # Check for Azure DevOps
        if os.getenv("AZURE_DEVOPS_ORG") and os.getenv("AZURE_DEVOPS_TOKEN"):
            return True
            
        # Check for JIRA
        if os.getenv("JIRA_URL") and os.getenv("JIRA_TOKEN"):
            return True
            
        # Check for GitHub Projects (optional)
        if os.getenv("GITHUB_PROJECT_ENABLED") == "true":
            return True
            
        return False
    
    def get_commit_diff(self, repo_path: str, commit_hash: str) -> Optional[str]:
        """
        Get the diff for a specific commit
        
        Args:
            repo_path: Path to the git repository
            commit_hash: The commit hash to analyze
            
        Returns:
            The diff as a string, or None if error
        """
        try:
            # Get the diff for this commit
            result = subprocess.run(
                ["git", "show", "--stat", "--format=", commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to get diff: {result.stderr}")
                return None
                
            stat_output = result.stdout.strip()
            
            # Also get actual code changes (limited to avoid huge diffs)
            result = subprocess.run(
                ["git", "show", "--format=", "--unified=3", commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return stat_output  # Return just stats if diff fails
                
            diff_output = result.stdout
            
            # Limit diff size to avoid overwhelming Ollama
            max_diff_lines = 100
            diff_lines = diff_output.split('\n')
            if len(diff_lines) > max_diff_lines:
                diff_output = '\n'.join(diff_lines[:max_diff_lines]) + '\n\n... (diff truncated)'
            
            return f"{stat_output}\n\n{diff_output}"
            
        except subprocess.TimeoutExpired:
            logger.error("Git command timed out")
            return None
        except Exception as e:
            logger.error(f"Error getting commit diff: {e}")
            return None
    
    def analyze_diff_with_ollama(self, diff: str, commit_message: str, files_changed: List[str]) -> Dict[str, str]:
        """
        Analyze diff using Ollama and generate an intelligent summary
        
        Args:
            diff: The git diff text
            commit_message: Original commit message
            files_changed: List of changed files
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Prepare prompt for Ollama
            files_list = "\n".join([f"  - {f}" for f in files_changed[:10]])
            if len(files_changed) > 10:
                files_list += f"\n  ... and {len(files_changed) - 10} more"
            
            prompt = f"""Analyze this git commit and provide a concise summary.

                    Original Commit Message: {commit_message}

                    Files Changed ({len(files_changed)}):
                    {files_list}

                    Diff Preview:
                    {diff[:1500]}

                    Based on the changes, provide:
                    1. A brief summary of what was changed (1-2 sentences)
                    2. The type of change (feature, bugfix, refactor, docs, test, config, etc.)
                    3. Impact level (minor, moderate, major)

                    Format your response as:
                    SUMMARY: <summary>
                    TYPE: <type>
                    IMPACT: <impact>
                """

            # Call Ollama API
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more factual responses
                        "num_predict": 200   # Limit response length
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return self._fallback_analysis(commit_message, files_changed)
            
            result = response.json()
            analysis_text = result.get("response", "")
            
            # Parse the response
            analysis = self._parse_ollama_response(analysis_text)
            
            # Add original commit message for reference
            analysis["original_message"] = commit_message
            analysis["files_count"] = len(files_changed)
            
            return analysis
            
        except requests.exceptions.Timeout:
            logger.warning("Ollama request timed out, using fallback")
            return self._fallback_analysis(commit_message, files_changed)
        except Exception as e:
            logger.error(f"Error analyzing diff with Ollama: {e}")
            return self._fallback_analysis(commit_message, files_changed)
    
    def _parse_ollama_response(self, response_text: str) -> Dict[str, str]:
        """Parse Ollama's structured response"""
        analysis = {
            "summary": "",
            "type": "unknown",
            "impact": "minor"
        }
        
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith("SUMMARY:"):
                analysis["summary"] = line.replace("SUMMARY:", "").strip()
            elif line.startswith("TYPE:"):
                analysis["type"] = line.replace("TYPE:", "").strip().lower()
            elif line.startswith("IMPACT:"):
                analysis["impact"] = line.replace("IMPACT:", "").strip().lower()
        
        # If summary is still empty, use first meaningful line
        if not analysis["summary"]:
            lines = [l.strip() for l in response_text.split('\n') if l.strip()]
            if lines:
                analysis["summary"] = lines[0][:200]  # Limit length
        
        return analysis
    
    def _fallback_analysis(self, commit_message: str, files_changed: List[str]) -> Dict[str, str]:
        """Fallback analysis when Ollama is unavailable"""
        # Simple heuristic-based analysis
        msg_lower = commit_message.lower()
        
        # Determine type
        if any(word in msg_lower for word in ["fix", "bug", "patch", "repair"]):
            change_type = "bugfix"
        elif any(word in msg_lower for word in ["add", "feature", "implement", "new"]):
            change_type = "feature"
        elif any(word in msg_lower for word in ["refactor", "clean", "reorganize"]):
            change_type = "refactor"
        elif any(word in msg_lower for word in ["doc", "readme", "comment"]):
            change_type = "docs"
        elif any(word in msg_lower for word in ["test", "spec"]):
            change_type = "test"
        elif any(word in msg_lower for word in ["config", "setup", "env"]):
            change_type = "config"
        else:
            change_type = "update"
        
        # Determine impact based on files changed
        if len(files_changed) > 10:
            impact = "major"
        elif len(files_changed) > 3:
            impact = "moderate"
        else:
            impact = "minor"
        
        return {
            "summary": f"Modified {len(files_changed)} file(s): {commit_message}",
            "type": change_type,
            "impact": impact,
            "original_message": commit_message,
            "files_count": len(files_changed),
            "ollama_unavailable": True
        }
    
    def process_commit(self, repo_path: str, commit_hash: str, 
                      commit_message: str, files_changed: List[str]) -> Dict[str, str]:
        """
        Main entry point: process a commit and return analysis
        
        Args:
            repo_path: Path to git repository
            commit_hash: Commit hash
            commit_message: Original commit message
            files_changed: List of changed files
            
        Returns:
            Dictionary with analysis results
        """
        # Check if project management system is connected
        if self.is_project_management_connected():
            logger.info("Project management system detected, skipping diff analysis")
            return {
                "summary": commit_message,
                "type": "tracked",
                "impact": "unknown",
                "project_system_connected": True
            }
        
        logger.info("No project management system detected, analyzing diff with AI...")
        
        # Get diff
        diff = self.get_commit_diff(repo_path, commit_hash)
        
        if not diff:
            logger.warning("Could not get diff, using fallback analysis")
            return self._fallback_analysis(commit_message, files_changed)
        
        # Analyze with Ollama
        analysis = self.analyze_diff_with_ollama(diff, commit_message, files_changed)
        
        logger.info(f"Analysis complete: {analysis['type']} - {analysis['impact']} impact")
        
        return analysis
