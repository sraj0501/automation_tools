package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
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
		if cmd == "help" || cmd == "version" || cmd == "commit-queue" || cmd == "commits" || cmd == "queue" || cmd == "telegram-status" || cmd == "azure-check" {
			return &CLI{}, nil
		}
	}

	repoPath, err := resolveRepoPath()
	if err != nil {
		// For status command, still allow but with limited info
		if len(os.Args) > 1 && os.Args[1] == "status" {
			return &CLI{}, nil
		}
		return nil, err
	}

	daemon, err := NewDaemon(repoPath)
	if err != nil {
		return nil, err
	}

	return &CLI{daemon: daemon}, nil
}

func resolveRepoPath() (string, error) {
	workspacePath := strings.TrimSpace(os.Getenv("DEVTRACK_WORKSPACE"))
	if workspacePath != "" {
		workspacePath = filepath.Clean(workspacePath)
		if IsGitRepository(workspacePath) {
			return workspacePath, nil
		}

		parentPath := filepath.Dir(workspacePath)
		if IsGitRepository(parentPath) {
			return parentPath, nil
		}

		return "", fmt.Errorf("DEVTRACK_WORKSPACE is not a git repository: %s", workspacePath)
	}

	repoPath, err := os.Getwd()
	if err != nil {
		repoPath = "."
	}

	if IsGitRepository(repoPath) {
		return repoPath, nil
	}

	parentPath := filepath.Dir(repoPath)
	if IsGitRepository(parentPath) {
		return parentPath, nil
	}

	return "", fmt.Errorf("not in a git repository and DEVTRACK_WORKSPACE is not set")
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
	case "db-stats", "stats":
		return cli.handleDBStats()
	case "enable-learning":
		return cli.handleEnableLearning()
	case "show-profile":
		return cli.handleShowProfile()
	case "test-response":
		return cli.handleTestResponse()
	case "revoke-consent":
		return cli.handleRevokeConsent()
	case "learning-status":
		return cli.handleLearningStatus()
	case "learning-setup-cron":
		return cli.handleLearningSetupCron()
	case "learning-remove-cron":
		return cli.handleLearningRemoveCron()
	case "learning-cron-status":
		return cli.handleLearningCronStatus()
	case "learning-sync":
		return cli.handleLearningSync()
	case "learning-reset":
		return cli.handleLearningReset()
	case "preview-report":
		return cli.handlePreviewReport()
	case "send-report":
		return cli.handleSendReport()
	case "save-report":
		return cli.handleSaveReport()
	case "force-trigger":
		return cli.handleForceTrigger()
	case "send-summary":
		return cli.handleSendSummary()
	case "skip-next":
		return cli.handleSkipNext()
	case "version":
		return cli.handleVersion()
	case "commit-queue":
		return cli.handleCommitQueue()
	case "commits":
		return cli.handleCommits()
	case "queue":
		return cli.handleQueueStats()
	case "telegram-status":
		return cli.handleTelegramStatus()
	case "azure-check":
		return cli.handleAzureCheck()
	case "azure-list":
		return cli.handleAzureList()
	case "azure-sync":
		return cli.handleAzureSync()
	case "azure-view":
		return cli.handleAzureView()
	case "settings":
		return cli.handleSettings()
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
	if cli.daemon.IsRunning() {
		pid, _ := cli.daemon.readPID()
		fmt.Printf("❌ Daemon is already running (PID: %d)\n", pid)
		fmt.Println("\nUse 'devtrack status' to see details")
		fmt.Println("Use 'devtrack restart' to restart")
		return nil
	}

	// Check if we're already daemonized (child process)
	if os.Getenv("DEVTRACK_DAEMON") == "1" {
		// We are the daemon process - run it
		if err := cli.daemon.Start(); err != nil {
			fmt.Printf("❌ Failed to start daemon: %v\n", err)
			return err
		}
		return nil
	}

	// Parent process - fork to background
	fmt.Println("🚀 Starting DevTrack daemon...")

	// Get current executable path
	exe, err := os.Executable()
	if err != nil {
		return fmt.Errorf("failed to get executable path: %w", err)
	}

	// Start ourselves as a background daemon
	cmd := exec.Command(exe, "start")
	cmd.Env = append(os.Environ(), "DEVTRACK_DAEMON=1")

	// Redirect output to log file
	logPath := GetLogFilePath()
	logFile, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return fmt.Errorf("failed to open log file: %w", err)
	}
	defer logFile.Close()

	cmd.Stdout = logFile
	cmd.Stderr = logFile

	// Detach from parent
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setsid: true,
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start daemon process: %w", err)
	}

	// Parent exits immediately
	fmt.Println("✓ Daemon started successfully")
	fmt.Printf("   PID: %d\n", cmd.Process.Pid)
	fmt.Printf("   Log: %s\n", logPath)
	fmt.Println("\nUse 'devtrack status' to check status")

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
	pidFile := GetPIDFilePath()

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

// handleStatus shows daemon status with full health dashboard
func (cli *CLI) handleStatus() error {
	// Handle case where daemon is nil (status check without repo)
	if cli.daemon == nil {
		pidFile := GetPIDFilePath()
		data, err := os.ReadFile(pidFile)
		if err != nil {
			fmt.Println("DevTrack Daemon        ● Stopped")
			return nil
		}

		fmt.Printf("DevTrack Daemon        ● Running (PID: %s)\n", strings.TrimSpace(string(data)))
		fmt.Println()
		fmt.Println("Use 'devtrack status' from repository directory for full details")
		return nil
	}

	status, err := cli.daemon.Status()
	if err != nil {
		fmt.Printf("Failed to get status: %v\n", err)
		return err
	}

	// Header
	if status.Running {
		uptime := ""
		if !status.StartTime.IsZero() {
			uptime = fmt.Sprintf(", uptime %s", formatDuration(status.Uptime))
		}
		fmt.Printf("DevTrack Daemon        ● Running (PID %d%s)\n", status.PID, uptime)
	} else {
		fmt.Println("DevTrack Daemon        ● Stopped")
	}
	fmt.Println()

	// Services section (from health snapshots)
	db, dbErr := NewDatabase()
	if dbErr == nil {
		defer db.Close()

		snapshots, err := db.GetLatestHealthSnapshots()
		if err == nil && len(snapshots) > 0 {
			fmt.Println("Services:")
			for _, snap := range snapshots {
				icon := "●"
				switch snap.Status {
				case "up":
					icon = "\033[32m●\033[0m" // green
				case "down":
					icon = "\033[31m●\033[0m" // red
				case "degraded":
					icon = "\033[33m●\033[0m" // yellow
				case "unconfigured":
					icon = "\033[90m○\033[0m" // gray
				}

				detail := formatHealthDetail(snap)
				fmt.Printf("  %-22s %s %s\n", serviceDisplayName(snap.Service), icon, detail)
			}
			fmt.Println()
		}

		// Queue stats
		pending, failed, sent, err := db.GetMessageQueueStats()
		if err == nil {
			fmt.Printf("Sync Queue:            %d pending, %d failed", pending, failed)
			if sent > 0 {
				fmt.Printf(" (%d sent)", sent)
			}
			fmt.Println()
		}

		// Deferred commit stats
		dcPending, dcEnhanced, dcCommitted, dcExpired, err := db.GetDeferredCommitStats()
		if err == nil && (dcPending+dcEnhanced+dcCommitted+dcExpired) > 0 {
			parts := []string{}
			if dcEnhanced > 0 {
				parts = append(parts, fmt.Sprintf("%d enhanced (ready for review)", dcEnhanced))
			}
			if dcPending > 0 {
				parts = append(parts, fmt.Sprintf("%d pending", dcPending))
			}
			if dcCommitted > 0 {
				parts = append(parts, fmt.Sprintf("%d committed", dcCommitted))
			}
			fmt.Printf("Deferred Commits:      %s\n", strings.Join(parts, ", "))
		}
		fmt.Println()
	}

	if status.Running {
		// Scheduler info
		if cli.daemon.monitor != nil && cli.daemon.monitor.scheduler != nil {
			stats := cli.daemon.monitor.scheduler.GetStats()
			workStatus := cli.daemon.monitor.scheduler.GetWorkHoursStatus()

			interval := stats["interval_minutes"]
			nextTrigger := stats["time_until_next"]
			paused := stats["is_paused"]

			schedLine := fmt.Sprintf("every %vm", interval)
			if p, ok := paused.(bool); ok && p {
				schedLine += " (PAUSED)"
			}
			if d, ok := nextTrigger.(time.Duration); ok && d > 0 {
				schedLine += fmt.Sprintf(", next in %s", formatDuration(d))
			}
			fmt.Printf("Scheduler:             %s\n", schedLine)

			if enabled, ok := workStatus["enabled"].(bool); ok && enabled {
				inHours := workStatus["is_work_hours"]
				startH := workStatus["work_start_hour"]
				endH := workStatus["work_end_hour"]
				hoursStr := "outside"
				if ih, ok := inHours.(bool); ok && ih {
					hoursStr = "active"
				}
				fmt.Printf("Work Hours:            %v:00-%v:00 (%s)\n", startH, endH, hoursStr)
			}
		}

	}

	return nil
}

// serviceDisplayName returns a human-friendly name for a service
func serviceDisplayName(service string) string {
	switch service {
	case "ipc":
		return "Python IPC"
	case "python_bridge":
		return "Python Bridge"
	case "ollama":
		return "Ollama"
	case "azure_devops":
		return "Azure DevOps"
	case "webhook_server":
		return "Webhook Server"
	case "telegram_bot":
		return "Telegram Bot"
	case "mongodb":
		return "MongoDB"
	default:
		return service
	}
}

// formatHealthDetail formats the detail string for a health snapshot
func formatHealthDetail(snap HealthSnapshot) string {
	switch snap.Status {
	case "up":
		if snap.LatencyMs > 0 {
			return fmt.Sprintf("Connected (latency: %dms)", snap.LatencyMs)
		}
		return "Connected"
	case "down":
		return "Down"
	case "degraded":
		return "Degraded"
	case "unconfigured":
		return "Not configured"
	default:
		return snap.Status
	}
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

// handleForceTrigger forces an immediate trigger by sending SIGUSR2 to the running daemon
func (cli *CLI) handleForceTrigger() error {
	if !cli.daemon.IsRunning() {
		fmt.Println("❌ Daemon is not running")
		fmt.Println("\nStart the daemon first:")
		fmt.Println("  devtrack start")
		return nil
	}

	pid, err := cli.daemon.readPID()
	if err != nil {
		fmt.Printf("❌ Could not read daemon PID: %v\n", err)
		return err
	}

	fmt.Println("⚡ Forcing immediate trigger...")

	process, err := os.FindProcess(pid)
	if err != nil {
		fmt.Printf("❌ Could not find daemon process: %v\n", err)
		return err
	}

	if err := process.Signal(syscall.SIGUSR2); err != nil {
		fmt.Printf("❌ Could not send signal to daemon: %v\n", err)
		return err
	}

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
			fmt.Printf("Use: tail -f %s\n", GetLogFilePath())
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
	fmt.Printf("Version: %s\n", GetDevTrackVersion())
	fmt.Printf("Build date: %s\n", GetDevTrackBuildDate())
	fmt.Println()
	fmt.Println("Components:")
	fmt.Println("  • Git monitoring (go-git)")
	fmt.Println("  • Time-based scheduler (robfig/cron)")
	fmt.Println("  • Background daemon + Python bridge")
	fmt.Println("  • IPC communication, SQLite database")
	fmt.Println("  • NLP task parsing (spaCy)")
	fmt.Println("  • Task matching, email reports")
	fmt.Println("  • AI-enhanced daily reports (Ollama)")
	return nil
}

// handleDBStats shows database statistics
func (cli *CLI) handleDBStats() error {
	fmt.Println("📊 Database Statistics")
	fmt.Println("=" + strings.Repeat("=", 50))
	fmt.Println()

	// Open database
	db, err := NewDatabase()
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Get statistics
	stats, err := db.GetStats()
	if err != nil {
		return fmt.Errorf("failed to get database stats: %w", err)
	}

	// Get analytics
	analytics, _ := db.GetAnalytics()

	// Display stats
	fmt.Printf("Database Path:    %s\n", stats["database_path"])
	fmt.Println()
	fmt.Printf("Total Triggers:   %d\n", stats["triggers"])
	if today, ok := analytics["triggers_today"].(int); ok {
		fmt.Printf("  Today:          %d\n", today)
	}
	if week, ok := analytics["triggers_this_week"].(int); ok {
		fmt.Printf("  This week:      %d\n", week)
	}
	fmt.Printf("Total Responses:  %d\n", stats["responses"])
	fmt.Printf("Task Updates:     %d\n", stats["task_updates"])
	fmt.Printf("Unsynced Updates: %d\n", stats["unsynced_updates"])
	fmt.Printf("Log Entries:      %d\n", stats["logs"])
	if top, ok := analytics["top_projects"].([]map[string]interface{}); ok && len(top) > 0 {
		fmt.Println()
		fmt.Println("Top Projects (last 30 days):")
		fmt.Println("─" + strings.Repeat("─", 50))
		for i, p := range top {
			if proj, ok := p["project"].(string); ok {
				switch cnt := p["count"].(type) {
				case int:
					fmt.Printf("  %d. %s (%d updates)\n", i+1, proj, cnt)
				case int64:
					fmt.Printf("  %d. %s (%d updates)\n", i+1, proj, cnt)
				}
			}
		}
	}
	fmt.Println()

	// Get recent triggers
	triggers, err := db.GetRecentTriggers(5)
	if err == nil && len(triggers) > 0 {
		fmt.Println("Recent Triggers (last 5):")
		fmt.Println("─" + strings.Repeat("─", 50))
		for i, t := range triggers {
			fmt.Printf("%d. [%s] %s at %s\n",
				i+1,
				t.TriggerType,
				t.Source,
				t.Timestamp.Format("2006-01-02 15:04:05"))
			if t.CommitMessage != "" {
				fmt.Printf("   %s\n", t.CommitMessage)
			}
		}
		fmt.Println()
	}

	// Get unsynced updates
	unsynced, err := db.GetUnsyncedTaskUpdates()
	if err == nil && len(unsynced) > 0 {
		fmt.Println("Unsynced Task Updates:")
		fmt.Println("─" + strings.Repeat("─", 50))
		for i, u := range unsynced {
			fmt.Printf("%d. [%s] %s - %s\n",
				i+1,
				u.Project,
				u.TicketID,
				u.Status)
			if u.UpdateText != "" {
				fmt.Printf("   %s\n", u.UpdateText)
			}
		}
		fmt.Println()
	}

	return nil
}

// handleEnableLearning enables personalized AI learning
func (cli *CLI) handleEnableLearning() error {
	days := GetLearningDefaultDays()
	if len(os.Args) > 2 {
		fmt.Sscanf(os.Args[2], "%d", &days)
	}

	learning := NewLearningCommands()
	return learning.EnableLearning(days)
}

// handleShowProfile shows the learning profile
func (cli *CLI) handleShowProfile() error {
	learning := NewLearningCommands()
	return learning.ShowProfile()
}

// handleTestResponse tests generating a response
func (cli *CLI) handleTestResponse() error {
	if len(os.Args) < 3 {
		fmt.Println("❌ Usage: devtrack test-response <text>")
		return fmt.Errorf("missing text argument")
	}

	text := strings.Join(os.Args[2:], " ")
	learning := NewLearningCommands()
	return learning.TestResponse(text)
}

// handleRevokeConsent revokes learning consent
func (cli *CLI) handleRevokeConsent() error {
	learning := NewLearningCommands()
	return learning.RevokeConsent()
}

// handleLearningStatus shows learning status
func (cli *CLI) handleLearningStatus() error {
	learning := NewLearningCommands()
	status, err := learning.GetLearningStatus()
	if err != nil {
		fmt.Printf("❌ Failed to get learning status: %v\n", err)
		return err
	}

	status.PrintStatus()
	return nil
}

// handleLearningReset wipes all learning data for a fresh start
func (cli *CLI) handleLearningReset() error {
	learning := NewLearningCommands()
	return learning.ResetLearning()
}

// handleLearningSetupCron installs the crontab entry from LEARNING_CRON_SCHEDULE
func (cli *CLI) handleLearningSetupCron() error {
	learning := NewLearningCommands()
	return learning.SetupCron()
}

// handleLearningRemoveCron removes the DevTrack learning crontab entry
func (cli *CLI) handleLearningRemoveCron() error {
	learning := NewLearningCommands()
	return learning.RemoveCron()
}

// handleLearningCronStatus shows cron entry status
func (cli *CLI) handleLearningCronStatus() error {
	learning := NewLearningCommands()
	return learning.CronStatus()
}

// handleLearningSync runs a delta (or full) sync immediately
func (cli *CLI) handleLearningSync() error {
	full := len(os.Args) > 2 && os.Args[2] == "--full"
	learning := NewLearningCommands()
	return learning.SyncNow(full)
}

// handlePreviewReport previews today's email report
func (cli *CLI) handlePreviewReport() error {
	date := ""
	if len(os.Args) > 2 {
		date = os.Args[2]
	}

	fmt.Println("📊 Generating daily report preview...")
	fmt.Println()

	scriptPath := GetEmailReporterPath()
	config, _ := LoadEnvConfig()
	projectRoot := ""
	if config != nil {
		projectRoot = config.ProjectRoot
	}
	if projectRoot == "" {
		projectRoot = os.Getenv("PROJECT_ROOT")
	}

	args := []string{"run", "--directory", projectRoot, "python", scriptPath, "preview"}
	if date != "" {
		args = append(args, date)
	}

	cmd := exec.Command("uv", args...)
	if projectRoot != "" {
		cmd.Dir = projectRoot
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fmt.Printf("❌ Failed to generate report: %v\n", err)
		return err
	}

	return nil
}

// handleSendReport sends email report
func (cli *CLI) handleSendReport() error {
	if len(os.Args) < 3 {
		fmt.Println("❌ Usage: devtrack send-report <email> [date]")
		return fmt.Errorf("missing email argument")
	}

	email := os.Args[2]
	date := ""
	if len(os.Args) > 3 {
		date = os.Args[3]
	}

	fmt.Printf("📧 Sending report to %s...\n", email)
	fmt.Println()

	scriptPath := GetEmailReporterPath()
	config, _ := LoadEnvConfig()
	projectRoot := ""
	if config != nil {
		projectRoot = config.ProjectRoot
	}
	if projectRoot == "" {
		projectRoot = os.Getenv("PROJECT_ROOT")
	}

	args := []string{"run", "--directory", projectRoot, "python", scriptPath, "send", email}
	if date != "" {
		args = append(args, date)
	}

	cmd := exec.Command("uv", args...)
	if projectRoot != "" {
		cmd.Dir = projectRoot
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fmt.Printf("❌ Failed to send report: %v\n", err)
		return err
	}

	return nil
}

// handleSaveReport saves report to file
func (cli *CLI) handleSaveReport() error {
	date := ""
	if len(os.Args) > 2 {
		date = os.Args[2]
	}

	fmt.Println("💾 Saving report to file...")
	fmt.Println()

	scriptPath := GetEmailReporterPath()
	config, _ := LoadEnvConfig()
	projectRoot := ""
	if config != nil {
		projectRoot = config.ProjectRoot
	}
	if projectRoot == "" {
		projectRoot = os.Getenv("PROJECT_ROOT")
	}

	args := []string{"run", "--directory", projectRoot, "python", scriptPath, "save"}
	if date != "" {
		args = append(args, date)
	}

	cmd := exec.Command("uv", args...)
	if projectRoot != "" {
		cmd.Dir = projectRoot
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fmt.Printf("❌ Failed to save report: %v\n", err)
		return err
	}

	return nil
}

// handleCommitQueue handles the internal commit-queue command (called by git wrapper)
func (cli *CLI) handleCommitQueue() error {
	// Parse flags
	message := ""
	branch := ""
	repoPath := ""
	filesStr := ""

	for i := 2; i < len(os.Args); i++ {
		switch os.Args[i] {
		case "--message":
			if i+1 < len(os.Args) {
				message = os.Args[i+1]
				i++
			}
		case "--branch":
			if i+1 < len(os.Args) {
				branch = os.Args[i+1]
				i++
			}
		case "--repo":
			if i+1 < len(os.Args) {
				repoPath = os.Args[i+1]
				i++
			}
		case "--files":
			if i+1 < len(os.Args) {
				filesStr = os.Args[i+1]
				i++
			}
		}
	}

	if message == "" {
		return fmt.Errorf("--message is required")
	}

	// Read diff from stdin
	diffPatch := ""
	stat, _ := os.Stdin.Stat()
	if (stat.Mode() & os.ModeCharDevice) == 0 {
		data := make([]byte, 0, 1024*1024) // 1MB max
		buf := make([]byte, 4096)
		for {
			n, err := os.Stdin.Read(buf)
			if n > 0 {
				data = append(data, buf[:n]...)
			}
			if err != nil {
				break
			}
			if len(data) > 1024*1024 {
				break // cap at 1MB
			}
		}
		diffPatch = string(data)
	}

	// Parse files
	var files []string
	if filesStr != "" {
		files = strings.Split(filesStr, ",")
	}

	// Open database and queue
	db, err := NewDatabase()
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	mgr := NewDeferredCommitManager(db)
	id, err := mgr.QueueCommit(message, diffPatch, branch, repoPath, files)
	if err != nil {
		return err
	}

	fmt.Printf("Commit queued (ID: %d)\n", id)
	return nil
}

// handleCommits handles commits subcommands (pending, review)
func (cli *CLI) handleCommits() error {
	subCmd := "pending"
	if len(os.Args) > 2 {
		subCmd = os.Args[2]
	}

	db, err := NewDatabase()
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	mgr := NewDeferredCommitManager(db)

	switch subCmd {
	case "pending":
		return mgr.ListPending()
	case "review":
		return mgr.ReviewEnhanced()
	default:
		fmt.Printf("Unknown commits subcommand: %s\n", subCmd)
		fmt.Println("Usage:")
		fmt.Println("  devtrack commits pending  - List deferred commits")
		fmt.Println("  devtrack commits review   - Review enhanced commits")
		return nil
	}
}

// handleQueueStats shows message queue statistics
func (cli *CLI) handleQueueStats() error {
	db, err := NewDatabase()
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	pending, failed, sent, err := db.GetMessageQueueStats()
	if err != nil {
		return fmt.Errorf("failed to get queue stats: %w", err)
	}

	fmt.Println("Message Queue")
	fmt.Println(strings.Repeat("═", 40))
	fmt.Printf("  Pending:   %d\n", pending)
	fmt.Printf("  Failed:    %d\n", failed)
	fmt.Printf("  Sent:      %d\n", sent)
	fmt.Println()

	if pending > 0 {
		messages, err := db.GetPendingMessages(10)
		if err == nil && len(messages) > 0 {
			fmt.Println("Pending Messages:")
			fmt.Println(strings.Repeat("─", 40))
			for _, m := range messages {
				fmt.Printf("  [%s] %s (queued: %s, retries: %d)\n",
					m.MessageType, m.MessageID,
					m.CreatedAt.Format("15:04:05"),
					m.RetryCount)
			}
			fmt.Println()
		}
	}

	if failed > 0 {
		fmt.Println("Note: Failed messages will be retried automatically when Python bridge reconnects.")
		fmt.Println()
	}

	return nil
}

// handleAzureCheck verifies Azure DevOps config and connectivity
func (cli *CLI) handleAzureCheck() error {
	config, _ := LoadEnvConfig()
	projectRoot := ""
	if config != nil {
		projectRoot = config.ProjectRoot
	}
	if projectRoot == "" {
		projectRoot = os.Getenv("PROJECT_ROOT")
	}

	scriptPath := filepath.Join(projectRoot, "backend", "azure", "check.py")

	args := []string{"run", "--directory", projectRoot, "python", scriptPath}
	cmd := exec.Command("uv", args...)
	if projectRoot != "" {
		cmd.Dir = projectRoot
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return err
	}
	return nil
}


// handleAzureList lists work items assigned to the user
func (cli *CLI) handleAzureList() error {
	config, _ := LoadEnvConfig()
	projectRoot := ""
	if config != nil {
		projectRoot = config.ProjectRoot
	}
	if projectRoot == "" {
		projectRoot = os.Getenv("PROJECT_ROOT")
	}

	scriptPath := filepath.Join(projectRoot, "backend", "azure", "list_items.py")
	args := []string{"run", "--directory", projectRoot, "python", scriptPath}
	args = append(args, os.Args[2:]...) // forward --all, --state flags
	cmd := exec.Command("uv", args...)
	if projectRoot != "" {
		cmd.Dir = projectRoot
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return err
	}
	return nil
}

// handleAzureSync runs a manual full bidirectional sync with Azure DevOps
func (cli *CLI) handleAzureSync() error {
	config, _ := LoadEnvConfig()
	projectRoot := ""
	if config != nil {
		projectRoot = config.ProjectRoot
	}
	if projectRoot == "" {
		projectRoot = os.Getenv("PROJECT_ROOT")
	}

	scriptPath := filepath.Join(projectRoot, "backend", "azure", "run_sync.py")
	args := []string{"run", "--directory", projectRoot, "python", scriptPath}
	cmd := exec.Command("uv", args...)
	if projectRoot != "" {
		cmd.Dir = projectRoot
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return err
	}
	return nil
}

// handleAzureView shows details for a specific Azure DevOps work item
func (cli *CLI) handleAzureView() error {
	if len(os.Args) < 3 {
		fmt.Println("Usage: devtrack azure-view <work-item-id>")
		return fmt.Errorf("missing work item ID")
	}

	config, _ := LoadEnvConfig()
	projectRoot := ""
	if config != nil {
		projectRoot = config.ProjectRoot
	}
	if projectRoot == "" {
		projectRoot = os.Getenv("PROJECT_ROOT")
	}

	scriptPath := filepath.Join(projectRoot, "backend", "azure", "view_item.py")
	args := []string{"run", "--directory", projectRoot, "python", scriptPath, os.Args[2]}
	cmd := exec.Command("uv", args...)
	if projectRoot != "" {
		cmd.Dir = projectRoot
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return err
	}
	return nil
}

// handleSettings shows all configuration paths and key env settings
func (cli *CLI) handleSettings() error {
	LoadEnvConfig()

	fmt.Println("DevTrack Settings")
	fmt.Println(strings.Repeat("=", 40))
	fmt.Println()

	fmt.Println("Files & Paths:")
	fmt.Printf("  Config:      %s\n", GetConfigPath())
	fmt.Printf("  Log file:    %s\n", GetLogFilePath())
	fmt.Printf("  PID file:    %s\n", GetPIDFilePath())
	fmt.Printf("  Database:    %s\n", GetDatabasePath())
	fmt.Println()

	fmt.Println("IPC:")
	fmt.Printf("  Host:        %s\n", getEnvOrDefault("IPC_HOST", "127.0.0.1"))
	fmt.Printf("  Port:        %s\n", getEnvOrDefault("IPC_PORT", "35893"))
	fmt.Println()

	fmt.Println("Azure DevOps:")
	fmt.Printf("  Org:         %s\n", maskEmpty(os.Getenv("AZURE_ORGANIZATION")))
	fmt.Printf("  Project:     %s\n", maskEmpty(os.Getenv("AZURE_PROJECT")))
	pat := os.Getenv("AZURE_DEVOPS_PAT")
	if pat == "" {
		pat = os.Getenv("AZURE_API_KEY")
	}
	fmt.Printf("  PAT:         %s\n", maskSecret(pat))
	fmt.Printf("  Sync:        %s\n", getEnvOrDefault("AZURE_SYNC_ENABLED", "false"))
	fmt.Println()

	fmt.Println("LLM:")
	fmt.Printf("  Provider:    %s\n", getEnvOrDefault("LLM_PROVIDER", "ollama"))
	fmt.Printf("  Ollama host: %s\n", getEnvOrDefault("OLLAMA_HOST", "(not set)"))
	fmt.Printf("  Sage model:  %s\n", getEnvOrDefault("GIT_SAGE_DEFAULT_MODEL", "(not set)"))
	fmt.Println()

	fmt.Println("Telegram:")
	enabled := os.Getenv("TELEGRAM_ENABLED")
	if enabled == "" {
		enabled = "false"
	}
	fmt.Printf("  Enabled:     %s\n", enabled)
	if enabled == "true" {
		fmt.Printf("  Bot token:   %s\n", maskSecret(os.Getenv("TELEGRAM_BOT_TOKEN")))
		fmt.Printf("  Chat ID:     %s\n", maskEmpty(os.Getenv("TELEGRAM_CHAT_ID")))
	}
	fmt.Println()

	fmt.Println("Webhook:")
	webhookEnabled := getEnvOrDefault("WEBHOOK_ENABLED", "false")
	fmt.Printf("  Enabled:     %s\n", webhookEnabled)
	if webhookEnabled == "true" {
		fmt.Printf("  Listen:      %s:%s\n",
			getEnvOrDefault("WEBHOOK_HOST", "0.0.0.0"),
			getEnvOrDefault("WEBHOOK_PORT", "8089"))
	}
	fmt.Println()

	return nil
}

func getEnvOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func maskEmpty(v string) string {
	if v == "" {
		return "(not set)"
	}
	return v
}

func maskSecret(v string) string {
	if v == "" {
		return "(not set)"
	}
	if len(v) <= 8 {
		return "****"
	}
	return v[:4] + strings.Repeat("*", len(v)-8) + v[len(v)-4:]
}

// handleTelegramStatus shows Telegram bot status
func (cli *CLI) handleTelegramStatus() error {
	// Ensure .env is loaded (this command skips NewDaemon)
	LoadEnvConfig() // ignore error — IsTelegramEnabled will just read os.Getenv
	if !IsTelegramEnabled() {
		fmt.Println("Telegram bot is disabled (TELEGRAM_ENABLED is not true)")
		return nil
	}
	fmt.Println("Telegram Bot Status")
	fmt.Println("===================")
	fmt.Println("Enabled: true")

	// Check health from DB
	db, err := NewDatabase()
	if err != nil {
		fmt.Println("Status: unknown (database unavailable)")
		return nil
	}
	defer db.Close()

	snapshots, err := db.GetLatestHealthSnapshots()
	if err != nil {
		fmt.Println("Status: unknown")
		return nil
	}

	for _, snap := range snapshots {
		if snap.Service == "telegram_bot" {
			fmt.Printf("Status: %s\n", snap.Status)
			if snap.Details != "" {
				fmt.Printf("Details: %s\n", snap.Details)
			}
			fmt.Printf("Last checked: %s\n", snap.CheckedAt.Format(time.RFC3339))
			return nil
		}
	}

	fmt.Println("Status: no health data yet")
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
	fmt.Println("GIT COMMANDS:")
	fmt.Println("  devtrack git commit -m 'msg'   AI-enhanced commit (iterative refinement)")
	fmt.Println("  uv run python -m backend.git_sage ask '<question>'  Ask git-sage a question")
	fmt.Println("  uv run python -m backend.git_sage do  '<task>'      Let git-sage execute a task")
	fmt.Println("  uv run python -m backend.git_sage interactive        Interactive git-sage session")
	fmt.Println()
	fmt.Println("AZURE DEVOPS:")
	fmt.Println("  devtrack azure-check                  Check config and connectivity")
	fmt.Println("  devtrack azure-list                   List work items assigned to you")
	fmt.Println("  devtrack azure-list --all             List all work items (no state filter)")
	fmt.Println("  devtrack azure-list --state <states>  Filter by state (e.g. 'Active,New')")
	fmt.Println("  devtrack azure-view <id>              Show full details for a work item")
	fmt.Println("  devtrack azure-sync                   Fetch work items and save local snapshot")
	fmt.Println()
	fmt.Println("OFFLINE RESILIENCE:")
	fmt.Println("  devtrack queue             Show message queue stats")
	fmt.Println("  devtrack commits pending   List deferred commits and status")
	fmt.Println("  devtrack commits review    Review enhanced deferred commits")
	fmt.Println()
	fmt.Println("EMAIL REPORTS:")
	fmt.Println("  devtrack preview-report [date]   Preview today's report (or YYYY-MM-DD)")
	fmt.Println("  devtrack send-report <email>     Send daily report to email address")
	fmt.Println("  devtrack save-report [date]      Save report to file")
	fmt.Println()
	fmt.Println("PERSONALIZED AI LEARNING:")
	fmt.Println("  devtrack enable-learning [days]  Enable learning from communications (default 30 days)")
	fmt.Println("  devtrack learning-sync           Run delta sync (only new messages since last run)")
	fmt.Println("  devtrack learning-sync --full    Force full re-sync (ignore delta state)")
	fmt.Println("  devtrack learning-status         Show learning status and statistics")
	fmt.Println("  devtrack learning-reset          Wipe all learning data and start fresh")
	fmt.Println("  devtrack show-profile            Show learned communication profile")
	fmt.Println("  devtrack test-response <text>    Test generating a personalized response")
	fmt.Println("  devtrack revoke-consent          Revoke learning consent and delete data")
	fmt.Println()
	fmt.Println("LEARNING CRON (configure LEARNING_CRON_SCHEDULE in .env):")
	fmt.Println("  devtrack learning-setup-cron     Install/update daily cron entry from .env")
	fmt.Println("  devtrack learning-cron-status    Show cron entry and .env schedule settings")
	fmt.Println("  devtrack learning-remove-cron    Remove the cron entry")
	fmt.Println()
	fmt.Println("TELEGRAM:")
	fmt.Println("  devtrack telegram-status  Show Telegram bot status")
	fmt.Println()
	fmt.Println("INFO COMMANDS:")
	fmt.Println("  devtrack logs          Show recent log entries")
	fmt.Println("  devtrack db-stats      Show database statistics")
	fmt.Println("  devtrack stats         Alias for db-stats (with analytics)")
	fmt.Println("  devtrack version       Show version information")
	fmt.Println("  devtrack help          Show this help message")
	fmt.Println("  devtrack settings      Show configuration paths and key env settings")
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
