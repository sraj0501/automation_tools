#!/usr/bin/env python3
"""
Teams Chat Responsiveness Analysis using OLLAMA
Analyzes responsiveness patterns and message clarity
"""

import duckdb
import json
import requests
import os
import sys
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import glob

class ChatResponsivenessAnalyzer:
    def __init__(self, db_path: str, ollama_url: str = "http://localhost:11434", model: str = "llama3:latest"):
        """Initialize the responsiveness analyzer"""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        self.db_path = db_path
        self.ollama_url = ollama_url
        self.model = model
        self.conn = duckdb.connect(db_path, read_only=True)
        
        # Test OLLAMA connection
        self._test_ollama_connection()
        
        # Load metadata
        self._load_metadata()
    
    def _test_ollama_connection(self):
        """Test if OLLAMA is running and accessible"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [model['name'] for model in models]
                print(f"✅ OLLAMA connection successful. Available models: {available_models}")
                
                if not any(self.model in model for model in available_models):
                    print(f"⚠️  Model '{self.model}' not found. Available: {available_models}")
                    print(f"💡 Run: ollama pull {self.model}")
                    sys.exit(1)
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ OLLAMA connection failed: {e}")
            print("💡 Make sure OLLAMA is running: ollama serve")
            sys.exit(1)
    
    def _load_metadata(self):
        """Load chat metadata"""
        try:
            result = self.conn.execute("SELECT * FROM chat_metadata").fetchone()
            if result:
                self.metadata = {
                    'chat_id': result[0],
                    'chat_topic': result[1],
                    'chat_type': result[2],
                    'created_datetime': result[3],
                    'last_updated_datetime': result[4],
                    'export_datetime': result[5],
                    'total_messages': result[6]
                }
            else:
                self.metadata = {}
        except Exception:
            self.metadata = {}
    
    def _clean_html_tags(self, text: str) -> str:
        """Remove HTML tags and decode common HTML entities"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode common HTML entities
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'"
        }
        
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        return text
    
    def _call_ollama(self, prompt: str) -> str:
        """Call OLLAMA API with a prompt"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 300
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()['response'].strip()
            else:
                print(f"OLLAMA API error: {response.status_code}")
                return "Error: API call failed"
                
        except requests.exceptions.Timeout:
            print("OLLAMA request timed out - continuing without this analysis")
            return "Error: Request timed out"
        except Exception as e:
            print(f"Error calling OLLAMA: {e}")
            return "Error: Connection failed"
    
    def _is_question_or_request(self, message_content: str) -> bool:
        """Check if a message contains a question or request that requires a response"""
        if not message_content:
            return False
        
        clean_content = self._clean_html_tags(message_content).lower().strip()
        
        # Question indicators
        question_indicators = [
            '?',  # Direct question mark
            'can you', 'could you', 'would you', 'will you',
            'please', 'kindly',
            'what', 'when', 'where', 'why', 'how', 'which', 'who',
            'do you', 'did you', 'have you', 'are you', 'is there',
            'any update', 'any news', 'status', 'progress',
            'let me know', 'update me', 'inform me',
            'thoughts', 'opinion', 'feedback',
            'confirm', 'confirmation', 'verify',
            'need', 'required', 'urgent',
            'asap', 'priority',
            'review', 'check', 'look at',
            'send', 'share', 'provide',
            'schedule', 'meeting', 'call',
            'availability', 'available', 'free'
        ]
        
        # Check if message contains question indicators
        for indicator in question_indicators:
            if indicator in clean_content:
                return True
        
        # Check for imperative sentences (requests)
        request_patterns = [
            clean_content.startswith('please '),
            clean_content.startswith('can '),
            clean_content.startswith('could '),
            clean_content.startswith('would '),
            clean_content.startswith('kindly '),
            clean_content.endswith(' please'),
            clean_content.endswith('?')
        ]
        
        return any(request_patterns)

    def _calculate_responsiveness_metrics(self, messages: List[Dict], all_messages: List[Dict]) -> Dict:
        """Calculate quantitative responsiveness metrics"""
        if len(messages) < 1:
            return {
                'total_messages': 0,
                'response_rate': 0,
                'avg_response_time_minutes': 0,
                'initiated_conversations': 0,
                'responded_to_others': 0,
                'others_message_count': 0,
                'questions_or_requests_count': 0,
                'no_response_24h_count': 0,
                'response_rate_with_penalty': 0
            }
        
        sender_name = messages[0]['sender']
        total_messages = len(messages)
        
        # Get all messages sorted by time
        sorted_all = sorted(all_messages, key=lambda x: x['timestamp'])
        
        # Calculate metrics
        responses_given = 0
        conversations_initiated = 0
        response_times = []
        others_message_count = 0
        questions_or_requests_count = 0
        no_response_24h_count = 0
        
        for i in range(len(sorted_all)):
            current_msg = sorted_all[i]
            
            # Count messages from others
            if current_msg['sender'] != sender_name:
                others_message_count += 1
                found_response = False
                
                # Check if this message is a question or request
                is_question_or_request = self._is_question_or_request(current_msg['content'])
                if is_question_or_request:
                    questions_or_requests_count += 1
                
                # Check if our sender responded within reasonable time
                for j in range(i + 1, min(i + 5, len(sorted_all))):  # Check next 5 messages
                    next_msg = sorted_all[j]
                    if next_msg['sender'] == sender_name:
                        time_diff = (next_msg['timestamp'] - current_msg['timestamp']).total_seconds() / 60
                        if time_diff <= 120:  # Within 2 hours
                            responses_given += 1
                            response_times.append(time_diff)
                            found_response = True
                        break
                
                # Check for 24-hour penalty ONLY for questions/requests
                if not found_response and is_question_or_request:
                    # Look for any response within 24 hours
                    found_24h_response = False
                    for j in range(i + 1, len(sorted_all)):
                        next_msg = sorted_all[j]
                        if next_msg['sender'] == sender_name:
                            time_diff = (next_msg['timestamp'] - current_msg['timestamp']).total_seconds() / 60
                            if time_diff <= 1440:  # Within 24 hours (1440 minutes)
                                found_24h_response = True
                                break
                            elif time_diff > 1440:  # More than 24 hours, stop checking
                                break
                    
                    if not found_24h_response:
                        no_response_24h_count += 1
            
            # Check for conversation initiation (our sender starts after gap)
            elif current_msg['sender'] == sender_name and i > 0:
                prev_msg = sorted_all[i - 1]
                time_diff = (current_msg['timestamp'] - prev_msg['timestamp']).total_seconds() / 60
                if time_diff > 120 and prev_msg['sender'] != sender_name:  # Gap > 2 hours, different sender
                    conversations_initiated += 1
        
        # Calculate response rate
        response_rate = (responses_given / others_message_count * 100) if others_message_count > 0 else 0
        
        # Calculate response rate with 24-hour penalty (only for questions/requests)
        penalty_factor = no_response_24h_count * 15  # 15% penalty per unanswered question/request
        response_rate_with_penalty = max(0, response_rate - penalty_factor)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_messages': total_messages,
            'response_rate': round(response_rate, 1),
            'avg_response_time_minutes': round(avg_response_time, 1),
            'initiated_conversations': conversations_initiated,
            'responded_to_others': responses_given,
            'others_message_count': others_message_count,
            'questions_or_requests_count': questions_or_requests_count,
            'no_response_24h_count': no_response_24h_count,
            'response_rate_with_penalty': round(response_rate_with_penalty, 1)
        }
    
    def _get_individual_ai_analysis(self, sender: str, messages: List[Dict], metrics: Dict) -> str:
        """Get AI's individual analysis for a specific person"""
        
        try:
            # Get sample messages from this person
            sample_messages = []
            for msg in messages[:10]:  # First 10 messages
                clean_content = self._clean_html_tags(msg['content'])
                if clean_content.strip():
                    content = clean_content[:80] + "..." if len(clean_content) > 80 else clean_content
                    sample_messages.append(content)
            
            messages_text = "\n".join(sample_messages) if sample_messages else "No readable messages"
            
            prompt = f"""
                    Analyze {sender}'s communication and responsiveness based on these metrics and sample messages:

                    METRICS:
                    - Messages Sent: {metrics['total_messages']}
                    - Response Rate: {metrics['response_rate']}%
                    - Response Rate (with penalty for unanswered questions): {metrics['response_rate_with_penalty']}%
                    - Average Response Time: {metrics['avg_response_time_minutes']} minutes
                    - Conversations Initiated: {metrics['initiated_conversations']}
                    - Questions/Requests received: {metrics['questions_or_requests_count']}
                    - Unanswered questions within 24h: {metrics['no_response_24h_count']}

                    SAMPLE MESSAGES:
                    {messages_text}

                    Provide a brief professional assessment (2-3 sentences) covering:
                    1. Communication effectiveness and responsiveness
                    2. Response patterns to questions/requests (including any 24-hour delays)
                    3. Overall collaboration reliability

                    Keep response under 100 words.
                    """
            
            response = self._call_ollama(prompt)
            return response if response and "Error:" not in response else f"AI analysis unavailable for {sender}."
            
        except Exception as e:
            print(f"Warning: Individual analysis failed for {sender}: {e}")
            return f"Individual analysis unavailable for {sender} due to technical limitations."
    
    def _get_overall_conversation_analysis(self, all_messages: List[Dict]) -> str:
        """Get AI's overall analysis of the entire conversation"""
        
        try:
            # Create conversation timeline with fewer messages
            timeline = []
            for msg in all_messages[:20]:  # Reduced to 20 messages
                clean_content = self._clean_html_tags(msg['content'])
                if clean_content.strip():
                    # Truncate long messages
                    content = clean_content[:100] + "..." if len(clean_content) > 100 else clean_content
                    timeline.append(f"{msg['sender']}: {content}")
            
            conversation_text = "\n".join(timeline)
            
            # Shorter, more focused prompt
            prompt = f"""
                    Analyze this business chat conversation briefly:

                    {conversation_text}

                    Provide a concise analysis covering:
                    1. Communication effectiveness
                    2. Response patterns
                    3. Notable observations

                    Keep response under 200 words.
                    """
            
            response = self._call_ollama(prompt)
            return response if response and "Error:" not in response else "Analysis unavailable due to technical issues."
            
        except Exception as e:
            print(f"Warning: Overall analysis failed: {e}")
            return "Overall conversation analysis unavailable due to technical limitations."
    
    def analyze_conversation(self, target_sender: str = "Shashank Raj") -> Dict:
        """Analyze the entire conversation for responsiveness"""
        print(f"🔍 Analyzing conversation responsiveness...")
        print(f"📊 Target sender: {target_sender}")
        
        # Get all messages with more details
        result = self.conn.execute("""
            SELECT 
                sender_name,
                created_datetime,
                content
            FROM chat_messages 
            WHERE is_deleted = false
                AND content IS NOT NULL
                AND TRIM(content) != ''
            ORDER BY created_datetime
        """).fetchall()
        
        if not result:
            print("❌ No messages found for analysis")
            return {}
        
        # Convert to list of dictionaries
        all_messages = []
        for row in result:
            all_messages.append({
                'sender': row[0],
                'timestamp': row[1],
                'content': row[2]
            })
        
        # Group messages by sender
        messages_by_sender = {}
        for msg in all_messages:
            sender = msg['sender']
            if sender not in messages_by_sender:
                messages_by_sender[sender] = []
            messages_by_sender[sender].append(msg)
        
        print(f"📈 Found {len(all_messages)} total messages from {len(messages_by_sender)} senders")
        
        # Analyze each sender
        analysis_results = {}
        
        for sender, messages in messages_by_sender.items():
            print(f"⏳ Analyzing {len(messages)} messages from {sender}...")
            
            # Calculate responsiveness metrics with all messages context
            responsiveness_metrics = self._calculate_responsiveness_metrics(messages, all_messages)
            
            # Get individual AI analysis
            print(f"🤖 Getting AI analysis for {sender}...")
            individual_ai_analysis = self._get_individual_ai_analysis(
                sender, messages, responsiveness_metrics
            )
            
            analysis_results[sender] = {
                'message_count': len(messages),
                'responsiveness_metrics': responsiveness_metrics,
                'individual_ai_analysis': individual_ai_analysis,
                'is_target_sender': sender.lower() == target_sender.lower()
            }
        
        # Get overall conversation analysis
        print("🤖 Getting overall conversation analysis...")
        overall_analysis = self._get_overall_conversation_analysis(all_messages)
        
        return {
            'metadata': self.metadata,
            'target_sender': target_sender,
            'analysis_date': datetime.now().isoformat(),
            'total_messages': len(all_messages),
            'total_participants': len(messages_by_sender),
            'sender_analysis': analysis_results,
            'overall_conversation_analysis': overall_analysis,
            'summary': self._generate_summary(analysis_results, target_sender)
        }
    
    def _generate_summary(self, analysis_results: Dict, target_sender: str) -> Dict:
        """Generate a summary comparison"""
        target_analysis = None
        others_analysis = []
        
        for sender, analysis in analysis_results.items():
            if analysis['is_target_sender']:
                target_analysis = analysis
            else:
                others_analysis.append(analysis)
        
        summary = {
            'target_sender_data': target_analysis,
            'others_data': others_analysis
        }
        
        return summary
    
    def save_analysis_report(self, analysis_results: Dict, output_file: str = None):
        """Save analysis results to JSON and generate a readable report"""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"responsiveness_analysis_{timestamp}"
        
        # Save JSON
        json_file = f"{output_file}.json"
        with open(json_file, 'w') as f:
            json.dump(analysis_results, f, indent=2, default=str)
        
        # Generate readable report
        txt_file = f"{output_file}.txt"
        with open(txt_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("TEAMS CHAT RESPONSIVENESS ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            # Metadata
            f.write("CHAT INFORMATION:\n")
            f.write("-" * 40 + "\n")
            if analysis_results.get('metadata'):
                meta = analysis_results['metadata']
                f.write(f"Topic: {meta.get('chat_topic', 'Unknown')}\n")
                f.write(f"Chat Type: {meta.get('chat_type', 'Unknown')}\n")
            f.write(f"Total Messages: {analysis_results.get('total_messages', 0)}\n")
            f.write(f"Total Participants: {analysis_results.get('total_participants', 0)}\n")
            f.write(f"Analysis Date: {analysis_results.get('analysis_date', 'Unknown')}\n")
            f.write(f"Target Sender: {analysis_results.get('target_sender', 'Unknown')}\n\n")
            
            # Individual sender analysis with raw numbers
            f.write("DETAILED SENDER ANALYSIS:\n")
            f.write("=" * 50 + "\n")
            
            for sender, analysis in analysis_results.get('sender_analysis', {}).items():
                marker = " (TARGET)" if analysis['is_target_sender'] else ""
                f.write(f"\n{sender}{marker}:\n")
                f.write("-" * (len(sender) + len(marker) + 1) + "\n")
                
                # Raw numbers
                metrics = analysis['responsiveness_metrics']
                f.write(f"Total Messages Sent: {metrics['total_messages']}\n")
                f.write(f"Messages from Others: {metrics['others_message_count']}\n")
                f.write(f"Questions/Requests received: {metrics['questions_or_requests_count']}\n")
                f.write(f"Responses Given: {metrics['responded_to_others']}\n")
                f.write(f"Conversations Initiated: {metrics['initiated_conversations']}\n")
                f.write(f"Unanswered Questions within 24h: {metrics['no_response_24h_count']}\n")
                
                # Calculated metrics
                f.write(f"Response Rate: {metrics['response_rate']}%\n")
                f.write(f"Response Rate (with 24h penalty): {metrics['response_rate_with_penalty']}%\n")
                f.write(f"Average Response Time: {metrics['avg_response_time_minutes']} minutes\n")
                f.write(f"AI Assessment: {analysis['individual_ai_analysis']}\n")
            
            # Individual performance summary
            f.write("\n" + "=" * 50 + "\n")
            f.write("INDIVIDUAL PERFORMANCE SUMMARY:\n")
            f.write("=" * 50 + "\n")
            
            # Show each participant's performance individually
            for sender, analysis in analysis_results.get('sender_analysis', {}).items():
                marker = " (TARGET)" if analysis['is_target_sender'] else ""
                metrics = analysis['responsiveness_metrics']
                
                f.write(f"\n{sender}{marker} Performance:\n")
                f.write("-" * (len(sender) + len(marker) + 13) + "\n")
                f.write(f"Response Effectiveness: {metrics['response_rate']}%\n")
                f.write(f"Response Effectiveness (with penalty for unanswered questions): {metrics['response_rate_with_penalty']}%\n")
                f.write(f"Average Response Time: {metrics['avg_response_time_minutes']} minutes\n")
                f.write(f"Unanswered Questions (24h): {metrics['no_response_24h_count']}\n")
                f.write(f"Engagement Level: {metrics['total_messages']} messages sent\n")
                f.write(f"AI Assessment: {analysis['individual_ai_analysis']}\n")
            
            # Overall AI analysis
            f.write("\n" + "=" * 50 + "\n")
            f.write("OVERALL CONVERSATION ANALYSIS (AI Assessment):\n")
            f.write("=" * 50 + "\n")
            f.write(f"{analysis_results.get('overall_conversation_analysis', 'No analysis available')}\n")
        
        print(f"📄 Analysis saved to:")
        print(f"   📊 JSON: {json_file}")
        print(f"   📝 Report: {txt_file}")
        
        return json_file, txt_file
    
    def close(self):
        """Close database connection"""
        self.conn.close()

def find_database_files():
    """Find all Teams chat database files"""
    return glob.glob("teams_chat_*.duckdb")

def main():
    """Main function"""
    print("🤖 Teams Chat Responsiveness Analysis with OLLAMA")
    print("=" * 60)
    
    # Find database files
    db_files = find_database_files()
    
    if not db_files:
        print("❌ No Teams chat database files found.")
        print("💡 Expected files: teams_chat_*.duckdb")
        return
    
    # Select database
    if len(db_files) == 1:
        db_path = db_files[0]
        print(f"📁 Using database: {db_path}")
    else:
        print("📁 Multiple database files found:")
        for i, file in enumerate(db_files, 1):
            print(f"  {i}. {file}")
        
        try:
            choice = int(input("Select file (number): ")) - 1
            if 0 <= choice < len(db_files):
                db_path = db_files[choice]
            else:
                print("❌ Invalid selection.")
                return
        except ValueError:
            print("❌ Invalid input.")
            return
    
    # Get target sender
    target_sender = input("\n🎯 Enter target sender name (default: Shashank Raj): ").strip()
    if not target_sender:
        target_sender = "Shashank Raj"
    
    # Get OLLAMA model
    model = input("🤖 Enter OLLAMA model (default: llama3:latest): ").strip()
    if not model:
        model = "llama3:latest"
    
    try:
        # Initialize analyzer
        print(f"\n🚀 Initializing responsiveness analyzer...")
        analyzer = ChatResponsivenessAnalyzer(db_path, model=model)
        
        # Run analysis
        print(f"⚡ Starting responsiveness analysis...")
        results = analyzer.analyze_conversation(target_sender)
        
        if results:
            # Save results
            json_file, txt_file = analyzer.save_analysis_report(results)
            
            # Display summary for all participants with AI analysis
            print(f"\n📋 ANALYSIS SUMMARY:")
            print("-" * 50)
            
            for sender, analysis in results.get('sender_analysis', {}).items():
                marker = " (TARGET)" if analysis['is_target_sender'] else ""
                metrics = analysis['responsiveness_metrics']
                
                print(f"\n{sender}{marker}:")
                print(f"  Messages Sent: {metrics['total_messages']}")
                print(f"  Messages from Others: {metrics['others_message_count']}")
                print(f"  Questions/Requests received: {metrics['questions_or_requests_count']}")
                print(f"  Responses Given: {metrics['responded_to_others']}")
                print(f"  Response Rate: {metrics['response_rate']}%")
                print(f"  Response Rate (with penalty): {metrics['response_rate_with_penalty']}%")
                print(f"  Avg Response Time: {metrics['avg_response_time_minutes']} min")
                print(f"  Unanswered Questions (24h): {metrics['no_response_24h_count']}")
                print(f"  🤖 AI Assessment: {analysis['individual_ai_analysis']}")
            
            print(f"\n✅ Analysis completed successfully!")
        else:
            print("❌ Analysis failed - no results generated.")
        
        analyzer.close()
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

if __name__ == "__main__":
    main()