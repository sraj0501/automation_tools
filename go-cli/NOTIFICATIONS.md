# Notification Configuration

Configure how DevTrack sends output and reports - via Email, Microsoft Teams, or both.

## Configuration Options

### Output Types

In `~/.devtrack/config.yaml`, under `settings.notifications`:

```yaml
settings:
  notifications:
    output_type: "email"  # Options: "email", "teams", "both"
    
    # When to send notifications
    send_on_trigger: false      # Send on each trigger event
    send_daily_summary: true    # Send daily summary report
    daily_report_time: "18:00"  # Time to send daily report (HH:MM)
    weekly_report_day: "Friday" # Day for weekly summary
```

### Email Configuration

```yaml
settings:
  notifications:
    output_type: "email"  # or "both"
    
    email:
      enabled: true
      to_addresses:
        - "your.email@example.com"
        - "colleague@example.com"
      cc_addresses:
        - "manager@example.com"
      subject: "DevTrack Daily Report - {{.Date}}"
      manager_email: "manager@example.com"
```

**Email Settings:**
- `enabled`: Turn email notifications on/off
- `to_addresses`: List of recipient email addresses
- `cc_addresses`: List of CC email addresses
- `subject`: Email subject line (supports templates)
- `manager_email`: Manager's email for reports

### Teams Configuration

```yaml
settings:
  notifications:
    output_type: "teams"  # or "both"
    
    teams:
      enabled: true
      chat_type: "channel"  # Options: "channel" or "chat"
      
      # For Channel messages
      channel_id: "19:abc123..."
      channel_name: "DevTrack Updates"
      
      # For 1-on-1 Chat messages
      chat_id: "19:xyz789..."
      
      # Alternative: Incoming Webhook
      webhook_url: "https://outlook.office.com/webhook/..."
      
      mention_user: false  # @mention user in messages
```

**Teams Settings:**
- `enabled`: Turn Teams notifications on/off
- `chat_type`: Send to "channel" or "chat"
- `channel_id`: Teams channel ID (for channel messages)
- `channel_name`: Display name of the channel
- `chat_id`: Teams chat ID (for 1-on-1 messages)
- `webhook_url`: Incoming webhook URL (alternative method)
- `mention_user`: Whether to @mention the user

### Both Email and Teams

To send to both destinations:

```yaml
settings:
  notifications:
    output_type: "both"
    
    email:
      enabled: true
      to_addresses: ["your.email@example.com"]
      
    teams:
      enabled: true
      channel_id: "19:abc123..."
      chat_type: "channel"
```

## Usage Examples

### 1. Email Only (Manager Reports)

```yaml
notifications:
  output_type: "email"
  send_daily_summary: true
  daily_report_time: "18:00"
  
  email:
    enabled: true
    to_addresses: ["me@example.com"]
    cc_addresses: ["manager@example.com"]
    manager_email: "manager@example.com"
```

**Result:** Daily email at 6 PM to you and manager with your progress.

### 2. Teams Channel Only

```yaml
notifications:
  output_type: "teams"
  send_daily_summary: true
  daily_report_time: "17:30"
  
  teams:
    enabled: true
    chat_type: "channel"
    channel_id: "19:abc123..."
    channel_name: "Team Updates"
```

**Result:** Daily summary posted to Teams channel at 5:30 PM.

### 3. Both Email and Teams

```yaml
notifications:
  output_type: "both"
  send_on_trigger: true  # Notify on each trigger
  send_daily_summary: true
  
  email:
    enabled: true
    to_addresses: ["me@example.com"]
    
  teams:
    enabled: true
    chat_type: "chat"
    chat_id: "19:xyz789..."  # Direct message
```

**Result:** 
- Immediate notifications to Teams chat on each trigger
- Daily email summary to your inbox

### 4. Manager Email + Team Channel

```yaml
notifications:
  output_type: "both"
  daily_report_time: "18:00"
  
  email:
    enabled: true
    to_addresses: ["manager@example.com"]
    subject: "Daily Progress Report - {{.Date}}"
    
  teams:
    enabled: true
    channel_id: "19:abc123..."
    channel_name: "Development Updates"
```

**Result:**
- Daily email to manager
- Progress posted to team channel

## Getting Teams IDs

### Channel ID

1. Open Teams in web browser
2. Navigate to your channel
3. Look at the URL:
   ```
   https://teams.microsoft.com/...channelId=19%3Aabc123...
   ```
4. The `channelId` parameter is your channel ID (URL decode it)

### Chat ID

1. Open a 1-on-1 chat in Teams web
2. Look at the URL:
   ```
   https://teams.microsoft.com/...chatId=19%3Axyz789...
   ```
3. The `chatId` parameter is your chat ID

### Webhook URL

1. Go to your Teams channel
2. Click "..." → Connectors → Incoming Webhook
3. Configure webhook and copy the URL
4. Use this URL in `webhook_url` setting

## Report Scheduling

### Daily Reports

```yaml
notifications:
  send_daily_summary: true
  daily_report_time: "18:00"  # 6 PM local time
```

The daily report includes:
- All commits made today
- Time spent on tasks
- Status updates
- Task completions
- Next day's plans

### Weekly Reports

```yaml
notifications:
  weekly_report_day: "Friday"  # Options: Monday-Sunday
  daily_report_time: "17:00"   # Time to send on that day
```

The weekly report includes:
- Summary of the week's commits
- Tasks completed
- Time tracking summary
- Velocity metrics
- Next week's priorities

### Trigger Notifications

```yaml
notifications:
  send_on_trigger: true  # Send on each Git commit or timer trigger
```

When enabled, sends a brief notification on each:
- Git commit detection
- Scheduled timer trigger (every 3 hours)

**Note:** This can be noisy. Recommended for testing only.

## Email Templates

The email subject supports template variables:

```yaml
email:
  subject: "DevTrack Report - {{.Date}}"
```

**Available variables:**
- `{{.Date}}` - Current date (Nov 1, 2025)
- `{{.Project}}` - Project name
- `{{.User}}` - Your name
- `{{.TriggerCount}}` - Number of triggers today

## Testing Notifications

To test your notification setup:

```bash
# 1. Configure notifications in config.yaml

# 2. Test the configuration
go run . test-config

# 3. Start the daemon
./devtrack start

# 4. Force a trigger to test notifications
./devtrack force-trigger  # (to be implemented)
```

## Privacy & Security

### Email Security
- Never commit credentials to git
- Use environment variables for sensitive data:
  ```yaml
  email:
    password: "${EMAIL_PASSWORD}"
  ```

### Teams Security
- Webhook URLs contain secrets - keep them private
- Use channel IDs instead of webhooks when possible
- Restrict webhook connectors to specific channels

### Data Sent
- Git commit messages
- Time spent on tasks
- Task descriptions and status
- **NOT sent:** Code content, file diffs, credentials

## Future Enhancements

Coming soon:
- [ ] Slack integration
- [ ] Discord webhooks
- [ ] Custom notification templates
- [ ] Conditional notifications (only if X tasks)
- [ ] Notification preferences per project
- [ ] Rich formatting (HTML emails, Adaptive Cards)
- [ ] Attachment support (logs, reports)
- [ ] Manager approval workflow
- [ ] Silent hours (don't notify during meetings)

## Troubleshooting

### Email not sending
- Check email credentials
- Verify SMTP settings
- Check firewall/network
- Look in daemon logs: `./devtrack logs`

### Teams not receiving
- Verify channel/chat ID
- Check webhook URL validity
- Ensure Teams integration is enabled
- Test webhook with curl:
  ```bash
  curl -X POST "YOUR_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d '{"text": "Test message"}'
  ```

### Both not working
- Check `output_type` is set correctly
- Verify both integrations are `enabled: true`
- Check daemon is running: `./devtrack status`
- Review logs: `./devtrack logs`

## Examples by Use Case

### Individual Developer
```yaml
notifications:
  output_type: "email"
  send_daily_summary: true
  daily_report_time: "17:00"
  email:
    to_addresses: ["me@work.com"]
```

### Team Lead
```yaml
notifications:
  output_type: "both"
  email:
    to_addresses: ["me@work.com"]
    cc_addresses: ["manager@work.com"]
  teams:
    chat_type: "channel"
    channel_name: "Team Progress"
```

### Remote Worker
```yaml
notifications:
  output_type: "teams"
  send_daily_summary: true
  daily_report_time: "18:00"
  teams:
    chat_type: "chat"
    chat_id: "19:manager_chat_id"
```

### Consultant/Contractor
```yaml
notifications:
  output_type: "email"
  send_daily_summary: true
  email:
    to_addresses: ["client@company.com"]
    subject: "Daily Progress Report - {{.Project}} - {{.Date}}"
```
