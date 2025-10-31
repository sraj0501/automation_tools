# Scheduler System

Time-based trigger system for the DevTrack automation tool. Prompts users at configurable intervals and respects work hours settings.

## Features

### ✅ Implemented

- **Configurable Intervals**: Set custom prompt intervals (default: 180 minutes / 3 hours)
- **Pause/Resume**: Temporarily pause and resume scheduling
- **Force Trigger**: Manually trigger prompts on demand
- **Skip Next**: Skip the next scheduled trigger
- **Work Hours Support**: Optional restriction to work hours only
- **Statistics**: Track trigger count and timing
- **Dynamic Interval**: Change interval without restart
- **Cron-based**: Uses robust cron scheduling library

### 🎯 Core Components

1. **`scheduler.go`**: Main scheduler implementation
   - `Scheduler`: Time-based trigger manager
   - `TriggerEvent`: Structured trigger events
   - Pause/resume functionality
   - Work hours checking
   - Statistics tracking

2. **`integrated.go`**: Combined Git + Timer monitoring
   - `IntegratedMonitor`: Unified event handling
   - Handles both commit and timer triggers
   - Single callback interface
   - Status reporting

## Usage

### Test Scheduler Alone

```bash
cd go-cli
go run . test-scheduler
```

This will:
- Start scheduler with 1-minute interval (for testing)
- Show trigger events every minute
- Allow interactive pause/resume/force/skip
- Display statistics

### Test Integrated System

```bash
go run . test-integrated
```

This will:
- Monitor Git commits
- Trigger every 2 minutes (timer)
- Show unified trigger handling
- Demonstrate complete system

## Configuration

### Interval Settings

In `~/.devtrack/config.yaml`:

```yaml
settings:
  prompt_interval: 180  # Minutes between prompts (default: 3 hours)
  work_hours_only: false  # Only trigger during work hours
  work_start_hour: 9   # Start of work hours (24h format)
  work_end_hour: 18    # End of work hours (24h format)
  timezone: Asia/Kolkata  # Timezone for work hours
```

### Work Hours

When `work_hours_only: true`:
- Triggers only fire between `work_start_hour` and `work_end_hour`
- Outside work hours, triggers are skipped
- System calculates next work start time

## How It Works

### Trigger Flow

1. **Cron Schedule**: Uses cron expression `0 */N * * * *` for N-minute intervals
2. **Trigger Check**: On schedule, checks if paused or outside work hours
3. **Fire Event**: Creates `TriggerEvent` with metadata
4. **Callback**: Calls registered `onTrigger` function
5. **Next Steps** (to be implemented):
   - Show user prompt
   - Send to Python via IPC
   - Log to database

### TriggerEvent Structure

```go
type TriggerEvent struct {
    Type      TriggerType  // "timer", "commit", "manual"
    Timestamp time.Time
    Source    string       // "scheduler", "git", etc.
    Data      interface{}  // Additional context
}
```

## API Reference

### Create Scheduler

```go
config, _ := LoadConfig()

scheduler := NewScheduler(config, func(event TriggerEvent) {
    fmt.Printf("Trigger at %s\n", event.Timestamp)
    // Handle trigger
})
```

### Start/Stop

```go
// Start scheduler
scheduler.Start()

// Stop scheduler
scheduler.Stop()
```

### Pause/Resume

```go
// Pause (skips triggers but keeps running)
scheduler.Pause()

// Resume
scheduler.Resume()

// Check if paused
isPaused := scheduler.IsPaused()
```

### Manual Control

```go
// Force immediate trigger
scheduler.ForceImmediate()

// Skip next trigger
scheduler.SkipNext()

// Change interval
scheduler.SetInterval(60) // 60 minutes
```

### Status & Stats

```go
// Get statistics
stats := scheduler.GetStats()
// Returns: is_paused, trigger_count, last_trigger, next_trigger, etc.

// Get work hours status
workStatus := scheduler.GetWorkHoursStatus()
// Returns: enabled, current_hour, is_work_hours, next_work_start, etc.

// Time until next trigger
duration := scheduler.GetTimeUntilNextTrigger()
```

### Integrated Monitoring

```go
// Create integrated monitor (Git + Timer)
monitor, _ := NewIntegratedMonitor("/path/to/repo")

// Start both Git and Timer monitoring
monitor.Start()

// Get unified status
status := monitor.GetStatus()

// Stop everything
monitor.Stop()
```

## Interactive Commands

When running tests, use these commands:

- `p` - Pause scheduler
- `r` - Resume scheduler  
- `f` - Force immediate trigger
- `s` - Skip next trigger / Show status
- `i` - Show statistics
- `q` - Quit

## Integration Points

### Current Status
- ✅ Scheduler implemented
- ✅ Work hours support
- ✅ Pause/resume functionality
- ✅ Statistics tracking
- ✅ Integrated with Git monitor
- ⏳ IPC communication (next step)
- ⏳ Python bridge (next step)
- ⏳ Database logging (next step)

### Next Steps
1. Connect to IPC layer for Go ↔ Python communication
2. Add SQLite logging for trigger history
3. Implement user prompt system
4. Connect to Python NLP parser
5. Add email notifications

## Examples

### Basic Usage

```go
// Load config
config, _ := LoadConfig()

// Create scheduler with 3-hour interval
scheduler := NewScheduler(config, func(event TriggerEvent) {
    log.Printf("Time to update! Trigger #%d", event.Data["trigger_count"])
    // Prompt user, parse input, update tasks
})

// Start
scheduler.Start()
defer scheduler.Stop()

// Wait for signals
<-make(chan struct{})
```

### Work Hours Only

```yaml
# In config.yaml
settings:
  work_hours_only: true
  work_start_hour: 9
  work_end_hour: 17
  timezone: America/New_York
```

```go
scheduler := NewScheduler(config, handleTrigger)
scheduler.Start()

// Check if currently in work hours
if scheduler.IsWorkingHours() {
    log.Println("Currently in work hours")
} else {
    status := scheduler.GetWorkHoursStatus()
    log.Printf("Outside work hours. Next start: %v", 
        status["next_work_start"])
}
```

### Dynamic Interval

```go
// Start with default interval
scheduler.Start()

// Change to 30-minute intervals
scheduler.SetInterval(30)

// Change to 4-hour intervals
scheduler.SetInterval(240)
```

## Testing

```bash
# Test scheduler with 1-minute intervals
go run . test-scheduler

# Test complete system (Git + Scheduler)
go run . test-integrated

# Build
go build
```

## Dependencies

- `github.com/robfig/cron/v3`: Cron scheduling

## Future Enhancements

- [ ] Smart intervals (adjust based on activity)
- [ ] Snooze functionality (delay next trigger)
- [ ] Multiple schedules (different intervals per project)
- [ ] Holiday calendar integration
- [ ] Meeting-aware scheduling (skip during meetings)
- [ ] Adaptive prompts (different questions based on time/context)
- [ ] Notification system (desktop alerts)
