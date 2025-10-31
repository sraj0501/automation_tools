package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

// IntegratedMonitor combines Git monitoring and time-based scheduling
type IntegratedMonitor struct {
	gitMonitor *GitMonitor
	scheduler  *Scheduler
	config     *Config
}

// NewIntegratedMonitor creates a new integrated monitoring system
func NewIntegratedMonitor(repoPath string) (*IntegratedMonitor, error) {
	// Load configuration
	config, err := LoadConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load config: %w", err)
	}

	// Create Git monitor
	gitMonitor, err := NewGitMonitor(repoPath)
	if err != nil {
		return nil, fmt.Errorf("failed to create git monitor: %w", err)
	}

	// Create integrated monitor
	monitor := &IntegratedMonitor{
		gitMonitor: gitMonitor,
		config:     config,
	}

	// Create scheduler with shared trigger handler
	scheduler := NewScheduler(config, monitor.handleTrigger)
	monitor.scheduler = scheduler

	return monitor, nil
}

// Start begins monitoring both Git commits and time-based triggers
func (im *IntegratedMonitor) Start() error {
	log.Println("Starting integrated monitoring system...")

	// Start Git monitor
	if err := im.gitMonitor.Start(im.handleCommit); err != nil {
		return fmt.Errorf("failed to start git monitor: %w", err)
	}
	log.Println("✓ Git monitor started")

	// Start scheduler
	if err := im.scheduler.Start(); err != nil {
		return fmt.Errorf("failed to start scheduler: %w", err)
	}
	log.Println("✓ Scheduler started")

	return nil
}

// Stop stops all monitoring
func (im *IntegratedMonitor) Stop() {
	log.Println("Stopping integrated monitoring system...")

	if im.gitMonitor != nil {
		im.gitMonitor.Stop()
	}

	if im.scheduler != nil {
		im.scheduler.Stop()
	}

	log.Println("✓ Monitoring stopped")
}

// handleCommit is called when a Git commit is detected
func (im *IntegratedMonitor) handleCommit(commit CommitInfo) {
	event := TriggerEvent{
		Type:      TriggerTypeCommit,
		Timestamp: commit.Timestamp,
		Source:    "git",
		Data:      commit,
	}

	im.handleTrigger(event)
}

// handleTrigger is the unified trigger handler for both Git and timer events
func (im *IntegratedMonitor) handleTrigger(event TriggerEvent) {
	fmt.Println("\n" + string('═') + strings.Repeat("═", 60))
	fmt.Printf("🎯 TRIGGER EVENT: %s\n", event.Type)
	fmt.Println(string('═') + strings.Repeat("═", 60))
	fmt.Printf("Timestamp: %s\n", event.Timestamp.Format(time.RFC1123))
	fmt.Printf("Source:    %s\n", event.Source)

	switch event.Type {
	case TriggerTypeCommit:
		if commit, ok := event.Data.(CommitInfo); ok {
			fmt.Printf("Commit:    %s\n", commit.Hash[:12])
			fmt.Printf("Message:   %s\n", commit.Message)
			fmt.Printf("Author:    %s\n", commit.Author)
			if len(commit.Files) > 0 {
				fmt.Printf("Files:     %d changed\n", len(commit.Files))
			}
		}

	case TriggerTypeTimer:
		if data, ok := event.Data.(map[string]interface{}); ok {
			if count, ok := data["trigger_count"].(int); ok {
				fmt.Printf("Trigger #:  %d\n", count)
			}
			if interval, ok := data["interval_minutes"].(int); ok {
				fmt.Printf("Interval:   %d minutes\n", interval)
			}
		}
	}

	fmt.Println()
	fmt.Println("📝 What happens next:")
	fmt.Println("   1. Prompt user: 'What did you work on?'")
	fmt.Println("   2. Send response to Python via IPC")
	fmt.Println("   3. Parse text with NLP (spaCy)")
	fmt.Println("   4. Match to existing tasks (semantic matching)")
	fmt.Println("   5. Update Azure DevOps / GitHub / JIRA")
	fmt.Println("   6. Log to SQLite database")
	fmt.Println("   7. Generate email report at EOD")
	fmt.Println()
	fmt.Println("⏳ Waiting for next event...")
	fmt.Println()
}

// GetStatus returns the current monitoring status
func (im *IntegratedMonitor) GetStatus() map[string]interface{} {
	status := make(map[string]interface{})

	// Scheduler status
	if im.scheduler != nil {
		status["scheduler"] = im.scheduler.GetStats()
		status["work_hours"] = im.scheduler.GetWorkHoursStatus()
	}

	// Git monitor status
	status["git_monitoring"] = true
	status["repo_path"] = im.gitMonitor.repoPath

	return status
}

// TestIntegrated demonstrates the complete integrated system
func TestIntegrated() {
	fmt.Println("🚀 Integrated Monitoring System Test")
	fmt.Println("====================================")
	fmt.Println()

	// Get current directory as repository path
	repoPath, err := os.Getwd()
	if err != nil {
		log.Fatalf("Failed to get current directory: %v", err)
	}

	// Go up one directory to the project root
	repoPath = filepath.Dir(repoPath)
	fmt.Printf("Repository: %s\n", repoPath)

	// Create integrated monitor
	monitor, err := NewIntegratedMonitor(repoPath)
	if err != nil {
		log.Fatalf("Failed to create integrated monitor: %v", err)
	}
	defer monitor.Stop()

	// Set short interval for testing
	fmt.Println("Setting scheduler interval to 2 minutes for testing...")
	monitor.scheduler.SetInterval(2)
	fmt.Println()

	// Start monitoring
	if err := monitor.Start(); err != nil {
		log.Fatalf("Failed to start monitoring: %v", err)
	}

	fmt.Println()
	fmt.Println("✅ SYSTEM ACTIVE")
	fmt.Println("================")
	fmt.Println()
	fmt.Println("The system will now trigger on:")
	fmt.Println("  • Git commits (make a commit to test)")
	fmt.Println("  • Every 2 minutes (timer)")
	fmt.Println()
	fmt.Println("Commands:")
	fmt.Println("  p - Pause scheduler")
	fmt.Println("  r - Resume scheduler")
	fmt.Println("  f - Force trigger now")
	fmt.Println("  s - Show status")
	fmt.Println("  q - Quit")
	fmt.Println()

	// Command handler
	go func() {
		reader := make([]byte, 1)
		for {
			os.Stdin.Read(reader)
			cmd := string(reader[0])

			switch cmd {
			case "p", "P":
				monitor.scheduler.Pause()
			case "r", "R":
				monitor.scheduler.Resume()
			case "f", "F":
				monitor.scheduler.ForceImmediate()
			case "s", "S":
				status := monitor.GetStatus()
				fmt.Println("\n📊 System Status:")
				fmt.Println("─────────────────")

				if schedStats, ok := status["scheduler"].(map[string]interface{}); ok {
					fmt.Printf("Scheduler:\n")
					fmt.Printf("  Paused: %v\n", schedStats["is_paused"])
					fmt.Printf("  Triggers: %v\n", schedStats["trigger_count"])
					fmt.Printf("  Interval: %v min\n", schedStats["interval_minutes"])
					fmt.Printf("  Next: %v\n", schedStats["time_until_next"])
				}

				fmt.Printf("\nGit Monitoring:\n")
				fmt.Printf("  Active: %v\n", status["git_monitoring"])
				fmt.Printf("  Repo: %v\n", status["repo_path"])
				fmt.Println()
			case "q", "Q":
				return
			}
		}
	}()

	// Wait for interrupt
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	fmt.Println("\n\n✓ Shutting down...")
}
