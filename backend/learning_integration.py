"""
Integration module for personalized AI learning

This module integrates the personalized AI with existing MS Graph and Azure DevOps
implementations, making it easy to enable learning from the CLI.
"""

import asyncio
import os
import sys
from typing import Optional
from datetime import datetime

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'msgraph_python'))

from personalized_ai import PersonalizedAI, CommunicationSample
from data_collectors import (
    TeamsDataCollector,
    AzureDevOpsDataCollector,
    OutlookDataCollector,
    DataCollectionOrchestrator
)


class GraphClientAdapter:
    """Adapter for the existing Graph client to work with data collectors"""
    
    def __init__(self, graph_client):
        self.graph = graph_client
    
    async def get_teams_chats(self):
        """Get all teams chats"""
        chats_response = await self.graph.get_teams_chats()
        if chats_response and hasattr(chats_response, 'value'):
            return [self._chat_to_dict(chat) for chat in chats_response.value]
        return []
    
    async def get_chat_messages(self, chat_id: str):
        """Get messages from a specific chat"""
        messages_response = await self.graph.get_all_chat_messages(chat_id)
        return [self._message_to_dict(msg) for msg in messages_response]
    
    async def get_sent_emails(self, days: int = 30):
        """Get sent emails"""
        # Would use Graph API to get sent items
        # Placeholder for now
        return []
    
    def _chat_to_dict(self, chat):
        """Convert chat object to dictionary"""
        return {
            'id': chat.id if hasattr(chat, 'id') else None,
            'topic': chat.topic if hasattr(chat, 'topic') else None,
            'chatType': chat.chat_type if hasattr(chat, 'chat_type') else None,
            'createdDateTime': chat.created_date_time.isoformat() if hasattr(chat, 'created_date_time') and chat.created_date_time else None,
            'lastUpdatedDateTime': chat.last_updated_date_time.isoformat() if hasattr(chat, 'last_updated_date_time') and chat.last_updated_date_time else None
        }
    
    def _message_to_dict(self, message):
        """Convert message object to dictionary"""
        from_user = None
        if hasattr(message, 'from_') and message.from_:
            from_user = {
                'user': {
                    'userPrincipalName': message.from_.email_address.address if hasattr(message.from_, 'email_address') and hasattr(message.from_.email_address, 'address') else None,
                    'displayName': message.from_.email_address.name if hasattr(message.from_, 'email_address') and hasattr(message.from_.email_address, 'name') else None
                }
            }
        
        body_content = None
        if hasattr(message, 'body') and message.body:
            body_content = message.body.content if hasattr(message.body, 'content') else None
        
        return {
            'id': message.id if hasattr(message, 'id') else None,
            'createdDateTime': message.created_date_time.isoformat() if hasattr(message, 'created_date_time') and message.created_date_time else None,
            'from': from_user,
            'body': {
                'content': body_content
            }
        }


class AsyncTeamsDataCollector(TeamsDataCollector):
    """Async version of Teams data collector"""
    
    async def collect_chat_history_async(self, days: int = 30) -> int:
        """Async version of collect_chat_history"""
        if not self.ai.consent_given:
            print("⚠️  Consent not given. Cannot collect data.")
            return 0
        
        if not self.graph_client:
            print("❌ Graph client not initialized")
            return 0
        
        print(f"📱 Collecting Teams chat history for last {days} days...")
        samples_collected = 0
        
        try:
            from datetime import timedelta
            
            # Get all chats
            chats = await self.graph_client.get_teams_chats()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for i, chat in enumerate(chats, 1):
                chat_id = chat.get('id')
                if not chat_id:
                    continue
                
                print(f"   Processing chat {i}/{len(chats)}...", end='\r')
                
                # Get messages from this chat
                messages = await self.graph_client.get_chat_messages(chat_id)
                
                if not messages or len(messages) < 2:
                    continue
                
                # Look for user responses (message following another person's message)
                for j in range(1, len(messages)):
                    prev_msg = messages[j-1]
                    current_msg = messages[j]
                    
                    # Check if current message is from user
                    if self._is_user_message(current_msg):
                        # Check if previous message is NOT from user (someone asked/said something)
                        if not self._is_user_message(prev_msg):
                            trigger = self._extract_message_content(prev_msg)
                            response = self._extract_message_content(current_msg)
                            
                            # Skip if either is empty
                            if not trigger or not response:
                                continue
                            
                            msg_time = self._parse_timestamp(current_msg.get('createdDateTime', ''))
                            
                            if msg_time >= cutoff_date:
                                self.ai.add_communication_sample(
                                    source='teams',
                                    context_type='chat',
                                    trigger=trigger,
                                    response=response,
                                    metadata={
                                        'chat_id': chat_id,
                                        'timestamp': msg_time.isoformat(),
                                        'chat_type': chat.get('chatType', 'unknown')
                                    }
                                )
                                samples_collected += 1
            
            print(f"\n   ✓ Collected {samples_collected} Teams chat samples")
            return samples_collected
            
        except Exception as e:
            print(f"\n   ❌ Error collecting Teams data: {e}")
            import traceback
            traceback.print_exc()
            return samples_collected


class LearningIntegration:
    """Main integration class for personalized AI learning"""
    
    def __init__(self, user_email: Optional[str] = None):
        """
        Initialize learning integration
        
        Args:
            user_email: User's email address (will try to fetch if not provided)
        """
        self.user_email = user_email
        self.ai = None
        self.graph_adapter = None
        self.teams_collector = None
    
    async def initialize(self, graph_client=None):
        """
        Initialize with MS Graph client
        
        Args:
            graph_client: Instance of msgraph_python.graph.Graph
        """
        # Get user email if not provided
        if not self.user_email and graph_client:
            try:
                user = await graph_client.get_user()
                self.user_email = user.mail or user.user_principal_name
                print(f"📧 Using email: {self.user_email}")
            except Exception as e:
                print(f"⚠️  Could not get user email: {e}")
                self.user_email = "user@example.com"
        
        # Initialize PersonalizedAI
        self.ai = PersonalizedAI(self.user_email)
        
        # Initialize collectors
        if graph_client:
            self.graph_adapter = GraphClientAdapter(graph_client)
            self.teams_collector = AsyncTeamsDataCollector(self.ai)
            self.teams_collector.graph_client = self.graph_adapter
    
    async def collect_teams_data(self, days: int = 30) -> int:
        """
        Collect data from MS Teams
        
        Args:
            days: Number of days of history to collect
            
        Returns:
            Number of samples collected
        """
        if not self.ai.consent_given:
            print("\n⚠️  Learning consent not given.")
            print("    The AI needs your permission to learn from your communications.")
            print()
            response = input("Would you like to grant consent? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y']:
                print()
                self.ai.request_consent()
                print()
            else:
                print("\n❌ Cannot collect data without consent.")
                return 0
        
        if not self.teams_collector:
            print("❌ Teams collector not initialized")
            return 0
        
        print()
        print("=" * 70)
        print("📥 COLLECTING COMMUNICATION DATA")
        print("=" * 70)
        print()
        
        count = await self.teams_collector.collect_chat_history_async(days)
        
        if count > 0:
            print()
            print("🧠 Updating AI profile with new data...")
            self.ai._update_profile()
            print("   ✓ Profile updated")
            print()
            print("=" * 70)
            print(f"✅ Successfully collected and processed {count} samples")
            print("=" * 70)
        
        return count
    
    def show_profile(self):
        """Display the current learning profile"""
        if not self.ai:
            print("❌ AI not initialized")
            return
        
        print()
        print(self.ai.get_profile_summary())
    
    async def test_response_generation(self, trigger: str, context: str = "work"):
        """
        Test generating a response for a given trigger
        
        Args:
            trigger: The message/question to respond to
            context: Context type (work, casual, formal)
        """
        if not self.ai:
            print("❌ AI not initialized")
            return
        
        if not self.ai.consent_given:
            print("⚠️  Consent not given. Cannot generate responses.")
            return
        
        print()
        print("=" * 70)
        print("🤖 GENERATING PERSONALIZED RESPONSE")
        print("=" * 70)
        print()
        print(f"Trigger: {trigger}")
        print(f"Context: {context}")
        print()
        print("Generating...")
        print()
        
        response = self.ai.generate_response_suggestion(trigger, context)
        
        print("Suggested Response:")
        print("-" * 70)
        print(response)
        print("-" * 70)
        print()


async def main():
    """CLI interface for learning integration"""
    import sys
    from configparser import ConfigParser
    from msgraph_python.graph import Graph
    
    # Load config
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'msgraph_python', 'config.cfg')
    
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        print("   Please set up MS Graph authentication first.")
        return
    
    config.read(config_path)
    
    if len(sys.argv) < 2:
        print("Usage: python learning_integration.py <command> [options]")
        print()
        print("Commands:")
        print("  enable-learning [days]  - Start collecting data and enable learning")
        print("  show-profile           - Show current learning profile")
        print("  test-response <text>   - Test generating a response")
        print("  revoke-consent         - Revoke learning consent and delete data")
        print()
        return
    
    command = sys.argv[1]
    
    # Initialize Graph client
    print("🔐 Authenticating with Microsoft Graph...")
    graph = Graph(config['azure'])
    
    # Initialize learning integration
    integration = LearningIntegration()
    await integration.initialize(graph)
    
    if command == "enable-learning":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        await integration.collect_teams_data(days)
        integration.show_profile()
    
    elif command == "show-profile":
        integration.show_profile()
    
    elif command == "test-response":
        if len(sys.argv) < 3:
            print("❌ Please provide text to respond to")
            return
        
        trigger = " ".join(sys.argv[2:])
        await integration.test_response_generation(trigger)
    
    elif command == "revoke-consent":
        if integration.ai:
            print()
            confirm = input("⚠️  This will delete all learned data. Continue? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                delete_data = input("Also delete all collected samples? (yes/no): ").strip().lower()
                integration.ai.revoke_consent(delete_data=(delete_data in ['yes', 'y']))
            else:
                print("Cancelled.")
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
