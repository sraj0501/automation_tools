# Manual Trigger Commands

These commands allow you to manually control the DevTrack scheduler without waiting for automatic triggers.

## Commands

### 1. `devtrack force-trigger`
**Purpose**: Immediately trigger the scheduler callback (simulates a timer event)

**Use Cases**:
- Testing the trigger system
- Forcing a prompt when you want to log work immediately
- Demo purposes

**Example**:
```bash
./devtrack force-trigger
```

**Output**:
```
⚡ Forcing immediate trigger...
✓ Trigger initiated successfully

The trigger is executing in the background.
Check logs for details:
  devtrack logs
```

**Notes**:
- Runs asynchronously (doesn't block)
- Respects work hours if configured
- Won't trigger if scheduler is paused

---

### 2. `devtrack skip-next`
**Purpose**: Skip the next scheduled trigger and reschedule for the following interval

**Use Cases**:
- You're in a meeting and don't want to be interrupted
- Already logged your work manually
- Need uninterrupted time for focused work

**Example**:
```bash
./devtrack skip-next
```

**Output**:
```
⏭️  Skipping next trigger (was due in 1h 30m)
✓ Next trigger skipped

New next trigger: 4h 30m
```

**Notes**:
- Only skips ONE trigger
- Doesn't pause the scheduler (it will trigger again after the interval)
- Use `devtrack pause` if you want to stop all triggers

---

### 3. `devtrack send-summary`
**Purpose**: Generate and send the daily summary report immediately (regardless of configured time)

**Use Cases**:
- End of day and want to send report now
- Need to share progress with manager urgently
- Testing email/notification system

**Example**:
```bash
./devtrack send-summary
```

**Output**:
```
📊 Generating daily summary...

📅 Summary for November 1, 2025
═══════════════════════════════
Triggers today:    5

⚠️  Full summary generation not yet implemented

Coming soon:
  • Query SQLite database for today's activities
  • Aggregate commits and work items
  • Format as email/Teams message
  • Send to configured recipients

For now, this shows current trigger count.
```

**Notes**:
- Currently shows basic stats (full implementation pending)
- Will respect notification configuration (email/Teams)
- Won't affect the automatic daily summary at configured time

---

## Comparison with Other Commands

### `pause` vs `skip-next`
- **`pause`**: Stops ALL future triggers until you `resume`
- **`skip-next`**: Skips only the next ONE trigger, then continues normally

### `force-trigger` vs Normal Trigger
- Both execute the same callback
- `force-trigger` happens immediately (ignores interval)
- Both respect work hours and pause status

### `send-summary` vs Daily Summary
- **`send-summary`**: Manual, immediate report generation
- **Daily Summary**: Automatic at configured time (e.g., 6 PM)
- Both will use the same template and data

---

## Workflow Examples

### Example 1: Focused Work Session
```bash
# Start of focused session
./devtrack pause

# ... 2 hours of deep work ...

# Resume when done
./devtrack resume
```

### Example 2: Skip One Interruption
```bash
# You're about to start a 1-hour meeting
./devtrack skip-next

# Scheduler will trigger after the meeting (3 hours from now instead of 2)
```

### Example 3: End of Day Report
```bash
# It's 5:30 PM, you're leaving early
./devtrack send-summary

# Report generated immediately instead of waiting until 6 PM
```

### Example 4: Test the System
```bash
# Force a trigger to test
./devtrack force-trigger

# Check what happened
./devtrack logs

# Check updated status
./devtrack status
```

---

## Status Display

All these commands update the daemon status. Check with:
```bash
./devtrack status
```

You'll see:
- Current trigger count
- Next trigger time
- Paused status
- Work hours configuration
- Uptime and other stats

---

## Troubleshooting

**`force-trigger` doesn't do anything?**
- Check if scheduler is paused: `./devtrack status`
- Check if outside work hours (if configured)
- Look at logs: `./devtrack logs`

**`skip-next` shows negative time?**
- This is a known issue with the time calculation
- The trigger will still be skipped correctly

**`send-summary` says "not yet implemented"?**
- This feature requires the database and email integration
- Currently shows basic stats only
- Full implementation coming in Phase 3

---

## Future Enhancements

Planned additions:
- `devtrack force-git-check` - Manually check for new commits
- `devtrack trigger-history` - Show all triggers today
- `devtrack test-notification` - Test email/Teams setup
- `devtrack summary --yesterday` - Generate yesterday's report
- `devtrack trigger-at <time>` - Schedule a one-time trigger
