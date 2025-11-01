package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// CLI provides command-line interface for daemon management
type CLI struct {
	daemon *Daemon
}

// NewCLI creates a new CLI instance
func NewCLI() (*CLI, error) {
	// For status/help commands, we don't need a full daemon
	if len(os.Args) > 1 {
		cmd := os.Args[1]
		if cmd == "help" || cmd == "version" {
			return &CLI{}, nil
		}
	}

	// Get current working directory as default repo path
	repoPath, err := os.Getwd()
	if err != nil {
		repoPath = "."
	}

	// Check if we're in a git repository
	if !IsGitRepository(repoPath) {
		// Try parent directory
		parentPath := filepath.Dir(repoPath)
		if IsGitRepository(parentPath) {
			repoPath = parentPath
		} else {
			// For status command, still allow but with limited info
			if len(os.Args) > 1 && os.Args[1] == "status" {
				return &CLI{}, nil
			}
			return nil, fmt.Errorf("not in a git repository. Please run from a git repository or specify one in config")
		}
	}

	daemon, err := NewDaemon(repoPath)
	if err != nil {
		return nil, err
	}

	return &CLI{daemon: daemon}, nil
}

// Execute runs the CLI command
func (cli *CLI) Execute() error {
	if len(os.Args) < 2 {
		cli.printUsage()
		return nil
	}

	command := os.Args[1]

	switch command {
	case "start":
		return cli.handleStart()
	case "stop":
		return cli.handleStop()
	case "restart":
		return cli.handleRestart()
	case "status":
		return cli.handleStatus()
	case "pause":
		return cli.handlePause()
	case "resume":
		return cli.handleResume()
	case "logs":
		return cli.handleLogs()
	case "force-trigger":
		return cli.handleForceTrigger()
	case "send-summary":
		return cli.handleSendSummary()
	case "skip-next":
		return cli.handleSkipNext()
	case "version":
		return cli.handleVersion()
	case "help":
		cli.printUsage()
		return nil
	default:
		// Check if it's a test command
		if strings.HasPrefix(command, "test-") {
			return nil // Let main handle test commands
		}
		fmt.Printf("Unknown command: %s\n\n", command)
		cli.printUsage()
		return fmt.Errorf("unknown command: %s", command)
	}
}

// handleStart starts the daemon
func (cli *CLI) handleStart() error {
	fmt.Println("🚀 Starting DevTrack daemon...")

	if cli.daemon.IsRunning() {
		pid, _ := cli.daemon.readPID()
		fmt.Printf("❌ Daemon is already running (PID: %d)\n", pid)
		fmt.Println("\nUse 'devtrack status' to see details")
		fmt.Println("Use 'devtrack restart' to restart")
		return nil
	}

	// Start in foreground for now (will background in production)
	if err := cli.daemon.Start(); err != nil {
		fmt.Printf("❌ Failed to start daemon: %v\n", err)
		return err
	}

	return nil
}

// handleStop stops the daemon
func (cli *CLI) handleStop() error {
	fmt.Println("⏹️  Stopping DevTrack daemon...")

	if !cli.daemon.IsRunning() {
		fmt.Println("❌ Daemon is not running")
		return nil
	}

	// Try graceful stop first
	homeDir, _ := os.UserHomeDir()
	pidFile := filepath.Join(homeDir, ".devtrack", "daemon.pid")

	if err := KillDaemon(pidFile); err != nil {
		fmt.Printf("❌ Failed to stop daemon: %v\n", err)
		return err
	}

	fmt.Println("✓ Daemon stopped successfully")
	return nil
}

// handleRestart restarts the daemon
func (cli *CLI) handleRestart() error {
	fmt.Println("🔄 Restarting DevTrack daemon...")

	// Stop if running
	if cli.daemon.IsRunning() {
		fmt.Println("Stopping current instance...")
		if err := cli.handleStop(); err != nil {
			return err
		}
		time.Sleep(1 * time.Second)
	}

	// Start again
	return cli.handleStart()
}

// handleStatus shows daemon status
func (cli *CLI) handleStatus() error {
	// Handle case where daemon is nil (status check without repo)
	if cli.daemon == nil {
		homeDir, _ := os.UserHomeDir()
		pidFile := filepath.Join(homeDir, ".devtrack", "daemon.pid")

		// Check if daemon is running by PID file
		data, err := os.ReadFile(pidFile)
		if err != nil {
			fmt.Println("📊 DevTrack Daemon Status")
			fmt.Println("═════════════════════════")
			fmt.Println()
			fmt.Println("Status:     ❌ STOPPED")
			fmt.Println()
			fmt.Println("Configuration:")
			fmt.Printf("  Config:   %s\n", GetConfigPath())
			fmt.Printf("  Logs:     %s\n", filepath.Join(homeDir, ".devtrack", "daemon.log"))
			fmt.Printf("  PID file: %s\n", pidFile)
			fmt.Println()
			fmt.Println("Commands:")
			fmt.Println("  devtrack start  - Start the daemon")
			return nil
		}

		fmt.Println("📊 DevTrack Daemon Status")
		fmt.Println("═════════════════════════")
		fmt.Println()
		fmt.Printf("Status:     ✅ RUNNING (PID: %s)\n", strings.TrimSpace(string(data)))
		fmt.Println()
		fmt.Println("Use 'devtrack status' from repository directory for full details")
		return nil
	}

	status, err := cli.daemon.Status()
	if err != nil {
		fmt.Printf("❌ Failed to get status: %v\n", err)
		return err
	}

	fmt.Println("📊 DevTrack Daemon Status")
	fmt.Println("═════════════════════════")
	fmt.Println()

	if status.Running {
		fmt.Println("Status:     ✅ RUNNING")
		fmt.Printf("PID:        %d\n", status.PID)

		if !status.StartTime.IsZero() {
			fmt.Printf("Uptime:     %s\n", formatDuration(status.Uptime))
			fmt.Printf("Started:    %s\n", status.StartTime.Format(time.RFC1123))
		}

		if status.TriggerCount > 0 {
			fmt.Printf("Triggers:   %d\n", status.TriggerCount)
		}

		if !status.LastTrigger.IsZero() {
			fmt.Printf("Last:       %s\n", status.LastTrigger.Format(time.RFC1123))
		}
	} else {
		fmt.Println("Status:     ❌ STOPPED")
	}

	fmt.Println()
	fmt.Println("Configuration:")
	fmt.Printf("  Config:   %s\n", status.ConfigPath)
	fmt.Printf("  Logs:     %s\n", status.LogPath)
	fmt.Printf("  PID file: %s\n", status.PIDPath)
	fmt.Println()

	if status.Running {
		// Show monitoring details
		if cli.daemon.monitor != nil && cli.daemon.monitor.scheduler != nil {
			stats := cli.daemon.monitor.scheduler.GetStats()
			workStatus := cli.daemon.monitor.scheduler.GetWorkHoursStatus()

			fmt.Println("Scheduler:")
			fmt.Printf("  Paused:       %v\n", stats["is_paused"])
			fmt.Printf("  Interval:     %v minutes\n", stats["interval_minutes"])
			fmt.Printf("  Next trigger: %v\n", stats["time_until_next"])

			fmt.Println()
			fmt.Println("Work Hours:")
			fmt.Printf("  Enabled:      %v\n", workStatus["enabled"])
			if workStatus["enabled"].(bool) {
				fmt.Printf("  Hours:        %d:00 - %d:00\n",
					workStatus["work_start_hour"], workStatus["work_end_hour"])
				fmt.Printf("  In hours:     %v\n", workStatus["is_work_hours"])
			}
		}

		fmt.Println()
		fmt.Println("Commands:")
		fmt.Println("  devtrack stop          - Stop the daemon")
		fmt.Println("  devtrack restart       - Restart the daemon")
		fmt.Println("  devtrack pause         - Pause scheduler")
		fmt.Println("  devtrack resume        - Resume scheduler")
		fmt.Println("  devtrack force-trigger - Force immediate trigger")
		fmt.Println("  devtrack skip-next     - Skip next trigger")
		fmt.Println("  devtrack send-summary  - Generate summary now")
		fmt.Println("  devtrack logs          - View recent logs")
	} else {
		fmt.Println("Commands:")
		fmt.Println("  devtrack start  - Start the daemon")
	}

	return nil
}

// handlePause pauses the scheduler
func (cli *CLI) handlePause() error {
	if !cli.daemon.IsRunning() {
		fmt.Println("❌ Daemon is not running")
		return nil
	}

	if err := cli.daemon.Pause(); err != nil {
		fmt.Printf("❌ Failed to pause: %v\n", err)
		return err
	}

	fmt.Println("✓ Scheduler paused")
	fmt.Println("\nGit monitoring is still active")
	fmt.Println("Use 'devtrack resume' to resume scheduler")
	return nil
}

// handleResume resumes the scheduler
func (cli *CLI) handleResume() error {
	if !cli.daemon.IsRunning() {
		fmt.Println("❌ Daemon is not running")
		return nil
	}

	if err := cli.daemon.Resume(); err != nil {
		fmt.Printf("❌ Failed to resume: %v\n", err)
		return err
	}

	fmt.Println("✓ Scheduler resumed")
	return nil
}

// handleForceTrigger forces an immediate trigger
func (cli *CLI) handleForceTrigger() error {
	if !cli.daemon.IsRunning() {
		fmt.Println("❌ Daemon is not running")
		fmt.Println("\nStart the daemon first:")
		fmt.Println("  devtrack start")
		return nil
	}

	if cli.daemon.monitor == nil || cli.daemon.monitor.scheduler == nil {
		fmt.Println("❌ Scheduler not initialized")
		return fmt.Errorf("scheduler not available")
	}

	fmt.Println("⚡ Forcing immediate trigger...")

	cli.daemon.monitor.scheduler.ForceImmediate()

	// Give it a moment to execute
	time.Sleep(500 * time.Millisecond)

	fmt.Println("✓ Trigger initiated successfully")
	fmt.Println("\nThe trigger is executing in the background.")
	fmt.Println("Check logs for details:")
	fmt.Println("  devtrack logs")
	return nil
}

// handleSendSummary generates and sends the daily summary
func (cli *CLI) handleSendSummary() error {
	if !cli.daemon.IsRunning() {
		fmt.Println("❌ Daemon is not running")
		fmt.Println("\nStart the daemon first:")
		fmt.Println("  devtrack start")
		return nil
	}

	fmt.Println("📊 Generating daily summary...")
	fmt.Println()

	// Get today's statistics
	stats := map[string]interface{}{
		"date":     time.Now().Format("January 2, 2006"),
		"triggers": 0,
	}

	if cli.daemon.monitor != nil && cli.daemon.monitor.scheduler != nil {
		schedulerStats := cli.daemon.monitor.scheduler.GetStats()
		stats["triggers"] = schedulerStats["trigger_count"]
	}

	fmt.Printf("📅 Summary for %s\n", stats["date"])
	fmt.Println("═══════════════════════════════")
	fmt.Printf("Triggers today:    %v\n", stats["triggers"])
	fmt.Println()

	// TODO: When database is implemented, query actual data
	fmt.Println("⚠️  Full summary generation not yet implemented")
	fmt.Println()
	fmt.Println("Coming soon:")
	fmt.Println("  • Query SQLite database for today's activities")
	fmt.Println("  • Aggregate commits and work items")
	fmt.Println("  • Format as email/Teams message")
	fmt.Println("  • Send to configured recipients")
	fmt.Println()
	fmt.Println("For now, this shows current trigger count.")

	return nil
}

// handleSkipNext skips the next scheduled trigger
func (cli *CLI) handleSkipNext() error {
	if !cli.daemon.IsRunning() {
		fmt.Println("❌ Daemon is not running")
		fmt.Println("\nStart the daemon first:")
		fmt.Println("  devtrack start")
		return nil
	}

	if cli.daemon.monitor == nil || cli.daemon.monitor.scheduler == nil {
		fmt.Println("❌ Scheduler not initialized")
		return fmt.Errorf("scheduler not available")
	}

	// Get current stats to show what's being skipped
	stats := cli.daemon.monitor.scheduler.GetStats()
	nextTrigger := stats["time_until_next"]

	fmt.Printf("⏭️  Skipping next trigger (was due in %v)\n", nextTrigger)

	cli.daemon.monitor.scheduler.SkipNext()

	// Get updated stats
	stats = cli.daemon.monitor.scheduler.GetStats()
	newNextTrigger := stats["time_until_next"]

	fmt.Println("✓ Next trigger skipped")
	fmt.Printf("\nNew next trigger: %v\n", newNextTrigger)

	return nil
}

// handleLogs displays recent log entries
func (cli *CLI) handleLogs() error {
	lines := 50 // Default: last 50 lines

	if len(os.Args) > 2 {
		if os.Args[2] == "-f" || os.Args[2] == "--follow" {
			fmt.Println("❌ Follow mode not yet implemented")
			fmt.Println("Use: tail -f ~/.devtrack/daemon.log")
			return nil
		}
	}

	logs, err := cli.daemon.GetLogs(lines)
	if err != nil {
		fmt.Printf("❌ Failed to read logs: %v\n", err)
		return err
	}

	if len(logs) == 0 {
		fmt.Println("No logs available")
		return nil
	}

	fmt.Printf("📄 Last %d log entries:\n", len(logs))
	fmt.Println("════════════════════════")
	for _, line := range logs {
		fmt.Println(line)
	}

	return nil
}

// handleVersion shows version information
func (cli *CLI) handleVersion() error {
	fmt.Println("DevTrack - Developer Automation Tools")
	fmt.Println("Version: 0.1.0-alpha")
	fmt.Println("Build date: November 1, 2025")
	fmt.Println()
	fmt.Println("Components:")
	fmt.Println("  • Git monitoring (go-git)")
	fmt.Println("  • Time-based scheduler (cron)")
	fmt.Println("  • Background daemon")
	fmt.Println("  • Configuration management (YAML)")
	fmt.Println()
	fmt.Println("Coming soon:")
	fmt.Println("  • IPC communication")
	fmt.Println("  • SQLite database")
	fmt.Println("  • NLP task parsing")
	fmt.Println("  • Semantic task matching")
	fmt.Println("  • Email reports")
	return nil
}

// printUsage prints CLI usage information
func (cli *CLI) printUsage() {
	fmt.Println("DevTrack - Developer Automation Tools")
	fmt.Println("======================================")
	fmt.Println()
	fmt.Println("DAEMON COMMANDS:")
	fmt.Println("  devtrack start         Start the daemon")
	fmt.Println("  devtrack stop          Stop the daemon")
	fmt.Println("  devtrack restart       Restart the daemon")
	fmt.Println("  devtrack status        Show daemon status")
	fmt.Println()
	fmt.Println("SCHEDULER COMMANDS:")
	fmt.Println("  devtrack pause         Pause scheduler (keep git monitoring)")
	fmt.Println("  devtrack resume        Resume scheduler")
	fmt.Println("  devtrack force-trigger Force immediate trigger")
	fmt.Println("  devtrack skip-next     Skip the next scheduled trigger")
	fmt.Println("  devtrack send-summary  Generate daily summary now")
	fmt.Println()
	fmt.Println("INFO COMMANDS:")
	fmt.Println("  devtrack logs          Show recent log entries")
	fmt.Println("  devtrack version       Show version information")
	fmt.Println("  devtrack help          Show this help message")
	fmt.Println()
	fmt.Println("TEST COMMANDS:")
	fmt.Println("  go run . test-git         Test Git commit detection")
	fmt.Println("  go run . test-scheduler   Test time-based scheduler")
	fmt.Println("  go run . test-config      Test configuration")
	fmt.Println("  go run . test-integrated  Test complete system")
	fmt.Println()
	fmt.Println("OTHER COMMANDS:")
	fmt.Println("  devtrack version       Show version information")
	fmt.Println("  devtrack help          Show this help message")
	fmt.Println()
	fmt.Println("CONFIGURATION:")
	fmt.Println("  Config file: ~/.devtrack/config.yaml")
	fmt.Println("  Log file:    ~/.devtrack/daemon.log")
	fmt.Println("  PID file:    ~/.devtrack/daemon.pid")
	fmt.Println()
}

// formatDuration formats a duration in human-readable form
func formatDuration(d time.Duration) string {
	if d < time.Minute {
		return fmt.Sprintf("%d seconds", int(d.Seconds()))
	} else if d < time.Hour {
		return fmt.Sprintf("%d minutes", int(d.Minutes()))
	} else if d < 24*time.Hour {
		hours := int(d.Hours())
		minutes := int(d.Minutes()) % 60
		return fmt.Sprintf("%dh %dm", hours, minutes)
	}

	days := int(d.Hours()) / 24
	hours := int(d.Hours()) % 24
	return fmt.Sprintf("%dd %dh", days, hours)
}
