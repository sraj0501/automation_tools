#!/usr/bin/env python3
"""
DevTrack Python Bridge - IPC Handler

This script receives triggers from the Go daemon via IPC and processes them.
It handles commit triggers and timer triggers, prompting for user input and
sending responses back to Go.
"""

import sys
import os
import time
import logging
from datetime import datetime

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ipc_client import (
    IPCClient, IPCMessage, MessageType,
    create_ack_message, create_task_update_message,
    create_response_message, create_error_message
)

# Import NLP parser (will be None if spaCy not installed)
try:
    from backend.nlp_parser import NLPTaskParser, parse_task
    nlp_available = True
except (ImportError, RuntimeError) as e:
    logger.warning(f"NLP parser not available: {e}")
    logger.warning("Install spaCy and model: pip install spacy && python -m spacy download en_core_web_sm")
    nlp_available = False
    NLPTaskParser = None
    parse_task = None


class DevTrackBridge:
    """Main bridge between Go daemon and Python AI layer"""
    
    def __init__(self):
        self.ipc_client = IPCClient()
        self.running = False
        self.trigger_count = {"commit": 0, "timer": 0}
        
        # Initialize NLP parser if available
        self.nlp_parser = None
        if nlp_available:
            try:
                self.nlp_parser = NLPTaskParser(use_ollama=True)
                logger.info("✓ NLP parser initialized")
            except Exception as e:
                logger.warning(f"Could not initialize NLP parser: {e}")
    
    def handle_commit_trigger(self, msg: IPCMessage):
        """Handle commit trigger from Go daemon"""
        self.trigger_count["commit"] += 1
        
        logger.info("=" * 60)
        logger.info(f"🎯 COMMIT TRIGGER #{self.trigger_count['commit']}")
        logger.info("=" * 60)
        
        data = msg.data
        logger.info(f"Repository: {data.get('repo_path', 'unknown')}")
        logger.info(f"Commit Hash: {data.get('commit_hash', 'unknown')[:12]}")
        logger.info(f"Author: {data.get('author', 'unknown')}")
        logger.info(f"Message: {data.get('commit_message', '')}")
        
        files = data.get('files_changed', [])
        if files:
            logger.info(f"Files Changed: {len(files)}")
            for f in files[:5]:  # Show first 5 files
                logger.info(f"  - {f}")
            if len(files) > 5:
                logger.info(f"  ... and {len(files) - 5} more")
        
        logger.info("")
        
        # Send acknowledgment
        ack = create_ack_message(msg.id)
        self.ipc_client.send_message(ack)
        
        # Parse commit message with NLP if available
        commit_msg = data.get('commit_message', '')
        if self.nlp_parser and commit_msg:
            logger.info("📝 Parsing commit message with NLP...")
            try:
                parsed = self.nlp_parser.parse(commit_msg)
                logger.info(f"   Project: {parsed.project}")
                logger.info(f"   Ticket:  {parsed.ticket_id}")
                logger.info(f"   Action:  {parsed.action_verb}")
                logger.info(f"   Status:  {parsed.status}")
                logger.info(f"   Confidence: {parsed.confidence:.2f}")
                
                # Send task update with parsed data
                task_update = create_task_update_message(
                    project=parsed.project or "automation_tools",
                    ticket_id=parsed.ticket_id or "",
                    description=parsed.description or commit_msg,
                    status=parsed.status or "in_progress",
                    time_spent=parsed.time_spent or "",
                    synced=False
                )
                self.ipc_client.send_message(task_update)
                logger.info("✓ Sent parsed task update to Go daemon")
            except Exception as e:
                logger.error(f"Error parsing commit message: {e}")
        else:
            # Fallback: send basic task update
            logger.info("ℹ️  NLP parser not available, sending basic update")
        
        # TODO: Phase 3 - Use Ollama to enhance task descriptions
        # TODO: Phase 4 - Update Azure DevOps/GitHub with task status
        # TODO: Phase 5 - Log to SQLite database
        
        logger.info("")
        logger.info("📝 Next steps (to be implemented):")
        if not self.nlp_parser:
            logger.info("   1. Install spaCy: pip install spacy")
            logger.info("   2. Download model: python -m spacy download en_core_web_sm")
        logger.info("   3. Use Ollama to enhance descriptions (Ollama only)")
        logger.info("   4. Match to existing tasks (semantic matching)")
        logger.info("   5. Update Azure DevOps/GitHub")
        logger.info("")
        
        # Simulate a task update response (for demonstration)
        # In production, this would be the result of NLP parsing and task matching
        if not self.nlp_parser:
            task_update = create_task_update_message(
                project="automation_tools",
                ticket_id="",  # Would be extracted from commit message
                description=data.get('commit_message', ''),
                status="in_progress",
                time_spent="",
                synced=False
            )
            self.ipc_client.send_message(task_update)
    
    def handle_timer_trigger(self, msg: IPCMessage):
        """Handle timer trigger from Go daemon"""
        self.trigger_count["timer"] += 1
        
        logger.info("=" * 60)
        logger.info(f"⏰ TIMER TRIGGER #{self.trigger_count['timer']}")
        logger.info("=" * 60)
        
        data = msg.data
        logger.info(f"Timestamp: {data.get('timestamp', '')}")
        logger.info(f"Interval: {data.get('interval_mins', 0)} minutes")
        logger.info(f"Trigger Count: {data.get('trigger_count', 0)}")
        logger.info("")
        
        # Send acknowledgment
        ack = create_ack_message(msg.id)
        self.ipc_client.send_message(ack)
        
        # TODO: Phase 3 - Prompt user for update via TUI or web interface
        # TODO: Phase 3 - Parse user input with spaCy NLP
        # TODO: Phase 3 - Use Ollama to enhance descriptions
        # TODO: Phase 4 - Update task management systems
        # TODO: Phase 5 - Generate daily report if end of day
        
        logger.info("📝 Next steps (to be implemented):")
        logger.info("   1. Prompt user: 'What did you work on?'")
        logger.info("   2. Parse response with spaCy NLP")
        logger.info("   3. Extract tasks, tickets, time spent")
        logger.info("   4. Use Ollama for task description enhancement")
        logger.info("   5. Match to existing tasks (semantic matching)")
        logger.info("   6. Update Azure DevOps/GitHub/JIRA")
        logger.info("   7. Check if EOD - generate email report")
        logger.info("")
    
    def handle_status_query(self, msg: IPCMessage):
        """Handle status query from Go daemon"""
        logger.info("📊 Status query received")
        
        response = create_response_message(
            request_id=msg.id,
            data={
                "status": "running",
                "triggers_processed": sum(self.trigger_count.values()),
                "commit_triggers": self.trigger_count["commit"],
                "timer_triggers": self.trigger_count["timer"],
                "python_version": sys.version,
                "uptime_seconds": time.time() - self.start_time
            }
        )
        self.ipc_client.send_message(response)
    
    def handle_shutdown(self, msg: IPCMessage):
        """Handle shutdown message from Go daemon"""
        logger.info("🛑 Shutdown message received")
        self.running = False
    
    def start(self):
        """Start the Python bridge"""
        self.start_time = time.time()
        
        logger.info("🚀 DevTrack Python Bridge Starting...")
        logger.info("=" * 60)
        
        # Register handlers
        self.ipc_client.register_handler(MessageType.COMMIT_TRIGGER, self.handle_commit_trigger)
        self.ipc_client.register_handler(MessageType.TIMER_TRIGGER, self.handle_timer_trigger)
        self.ipc_client.register_handler(MessageType.STATUS_QUERY, self.handle_status_query)
        self.ipc_client.register_handler(MessageType.SHUTDOWN, self.handle_shutdown)
        
        # Connect to IPC server
        logger.info("Connecting to Go daemon IPC server...")
        if not self.ipc_client.connect(timeout=5, retry_count=5):
            logger.error("❌ Failed to connect to IPC server")
            logger.error("   Make sure the Go daemon is running: ./devtrack start")
            return 1
        
        logger.info("✅ Connected to IPC server")
        logger.info("")
        logger.info("🎧 Listening for triggers from Go daemon...")
        logger.info("   - Commit triggers (Git activity)")
        logger.info("   - Timer triggers (scheduled prompts)")
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        logger.info("")
        
        # Start listening
        self.running = True
        self.ipc_client.start_listening()
        
        # Keep running until shutdown
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n⚠️  Interrupted by user")
        finally:
            logger.info("Shutting down...")
            self.ipc_client.stop_listening()
            self.ipc_client.disconnect()
            logger.info("✓ Python bridge stopped")
        
        return 0


def main():
    """Main entry point"""
    bridge = DevTrackBridge()
    return bridge.start()


if __name__ == "__main__":
    sys.exit(main())
