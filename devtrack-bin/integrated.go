package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
)

// WorkspaceMonitor pairs a GitMonitor with its workspace routing metadata
type WorkspaceMonitor struct {
	gitMonitor      *GitMonitor
	workspaceName   string
	pmPlatform      string
	pmProject       string
	// Per-workspace PM settings
	pmAssignee      string
	pmIterationPath string
	pmAreaPath      string
	pmMilestone     int
}

// IntegratedMonitor combines Git monitoring and time-based scheduling
type IntegratedMonitor struct {
	workspaceMonitors    []*WorkspaceMonitor // one per repo (single-repo has exactly one)
	scheduler            *Scheduler
	config               *Config
	ipcServer            *IPCServer
	database             *Database
	messageQueue         *MessageQueue
	lastActiveWorkspace  *WorkspaceMonitor
	lastActiveWorkspaceMu sync.Mutex
}

// NewIntegratedMonitor creates a new integrated monitoring system.
// repoPath is used as the single workspace when workspaces.yaml is absent.
func NewIntegratedMonitor(repoPath string) (*IntegratedMonitor, error) {
	// Load configuration
	config, err := LoadConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load config: %w", err)
	}

	// Create IPC server
	ipcServer, err := NewIPCServer()
	if err != nil {
		return nil, fmt.Errorf("failed to create IPC server: %w", err)
	}

	// Create database connection
	database, err := NewDatabase()
	if err != nil {
		return nil, fmt.Errorf("failed to create database: %w", err)
	}

	// Build workspace monitors: prefer workspaces.yaml when present
	var workspaceMonitors []*WorkspaceMonitor
	wsCfg, err := LoadWorkspacesConfig()
	if err != nil {
		log.Printf("Warning: failed to load workspaces.yaml: %v (falling back to single-repo mode)", err)
	}

	if wsCfg != nil && len(wsCfg.GetEnabledWorkspaces()) > 0 {
		log.Printf("Multi-repo mode: loading %d workspace(s) from workspaces.yaml", len(wsCfg.GetEnabledWorkspaces()))
		for _, ws := range wsCfg.GetEnabledWorkspaces() {
			gm, err := NewGitMonitor(ws.Path)
			if err != nil {
				log.Printf("Warning: skipping workspace %q (%s): %v", ws.Name, ws.Path, err)
				continue
			}
			workspaceMonitors = append(workspaceMonitors, &WorkspaceMonitor{
				gitMonitor:      gm,
				workspaceName:   ws.Name,
				pmPlatform:      ws.PMPlatform,
				pmProject:       ws.PMProject,
				pmAssignee:      ws.PMAssignee,
				pmIterationPath: ws.PMIterationPath,
				pmAreaPath:      ws.PMAreaPath,
				pmMilestone:     ws.PMMilestone,
			})
			log.Printf("  ✓ Workspace %q → %s (platform: %q)", ws.Name, ws.Path, ws.PMPlatform)
		}
		if len(workspaceMonitors) == 0 {
			return nil, fmt.Errorf("workspaces.yaml found but no valid workspaces could be loaded")
		}
	} else {
		// Single-repo backward-compat mode
		log.Printf("Single-repo mode: monitoring %s", repoPath)
		gm, err := NewGitMonitor(repoPath)
		if err != nil {
			return nil, fmt.Errorf("failed to create git monitor: %w", err)
		}
		workspaceMonitors = []*WorkspaceMonitor{{gitMonitor: gm}}
	}

	// Create integrated monitor
	monitor := &IntegratedMonitor{
		workspaceMonitors: workspaceMonitors,
		config:            config,
		ipcServer:         ipcServer,
		database:          database,
	}

	// Register IPC handlers
	monitor.registerIPCHandlers()

	// Create message queue for offline resilience
	monitor.messageQueue = NewMessageQueue(database, ipcServer)

	// Create scheduler with shared trigger handler
	scheduler := NewScheduler(config, monitor.handleTrigger)
	monitor.scheduler = scheduler

	return monitor, nil
}

// Start begins monitoring both Git commits and time-based triggers
func (im *IntegratedMonitor) Start() error {
	log.Println("Starting integrated monitoring system...")

	// Start IPC server
	if err := im.ipcServer.Start(); err != nil {
		return fmt.Errorf("failed to start IPC server: %w", err)
	}
	log.Println("✓ IPC server started")

	// Start Git monitor(s) — one per workspace
	for _, ws := range im.workspaceMonitors {
		wsCopy := ws // capture for closure
		if err := wsCopy.gitMonitor.Start(func(commit CommitInfo) {
			im.handleCommitForWorkspace(commit, wsCopy)
		}); err != nil {
			return fmt.Errorf("failed to start git monitor for %q: %w", wsCopy.workspaceName, err)
		}
		label := wsCopy.workspaceName
		if label == "" {
			label = wsCopy.gitMonitor.repoPath
		}
		log.Printf("✓ Git monitor started for %s", label)
	}

	// Start scheduler
	if err := im.scheduler.Start(); err != nil {
		return fmt.Errorf("failed to start scheduler: %w", err)
	}
	log.Println("✓ Scheduler started")

	// Start message queue drain goroutine
	if im.messageQueue != nil {
		im.messageQueue.Start()
		log.Println("✓ Message queue started")
	}

	return nil
}

// Stop stops all monitoring
func (im *IntegratedMonitor) Stop() {
	log.Println("Stopping integrated monitoring system...")

	// Stop message queue
	if im.messageQueue != nil {
		im.messageQueue.Stop()
	}

	// Send shutdown message to Python
	if im.ipcServer != nil {
		shutdownMsg := IPCMessage{
			Type:      MsgTypeShutdown,
			Timestamp: time.Now(),
			ID:        "shutdown",
			Data:      make(map[string]interface{}),
		}
		im.ipcServer.SendMessage(shutdownMsg)
		time.Sleep(500 * time.Millisecond) // Give Python time to process
		im.ipcServer.Stop()
	}

	for _, ws := range im.workspaceMonitors {
		if ws.gitMonitor != nil {
			ws.gitMonitor.Stop()
		}
	}

	if im.scheduler != nil {
		im.scheduler.Stop()
	}

	if im.database != nil {
		im.database.Close()
	}

	log.Println("✓ Monitoring stopped")
}

// registerIPCHandlers registers handlers for IPC messages from Python
func (im *IntegratedMonitor) registerIPCHandlers() {
	// Handle task update responses from Python
	im.ipcServer.RegisterHandler(MsgTypeTaskUpdate, func(msg IPCMessage) error {
		log.Printf("Received task update from Python: %+v", msg.Data)

		// Log to database
		if im.database != nil {
			record := TaskUpdateRecord{
				Timestamp:  time.Now(),
				Project:    getStringFromMap(msg.Data, "project"),
				TicketID:   getStringFromMap(msg.Data, "ticket_id"),
				UpdateText: getStringFromMap(msg.Data, "description"),
				Status:     getStringFromMap(msg.Data, "status"),
				Synced:     getBoolFromMap(msg.Data, "synced"),
				Platform:   getStringFromMap(msg.Data, "synced_platform"),
			}

			// Use "python" as default platform if not specified
			if record.Platform == "" {
				record.Platform = "python"
			}

			if _, err := im.database.InsertTaskUpdate(record); err != nil {
				log.Printf("Failed to log task update to database: %v", err)
			}
		}

		return nil
	})

	// Handle responses from Python
	im.ipcServer.RegisterHandler(MsgTypeResponse, func(msg IPCMessage) error {
		log.Printf("Received response from Python: %+v", msg.Data)
		return nil
	})

	// Handle errors from Python
	im.ipcServer.RegisterHandler(MsgTypeError, func(msg IPCMessage) error {
		log.Printf("Received error from Python: %s", msg.Error)

		// Log error to database
		if im.database != nil {
			logRecord := LogRecord{
				Timestamp: time.Now(),
				Level:     "error",
				Component: "python_ipc",
				Message:   msg.Error,
			}
			im.database.InsertLog(logRecord)
		}

		return nil
	})

	// Handle acknowledgments from Python
	im.ipcServer.RegisterHandler(MsgTypeAck, func(msg IPCMessage) error {
		log.Printf("Received ACK from Python for message: %s", msg.ID)
		return nil
	})

	// Handle webhook events (from webhook server via Python)
	im.ipcServer.RegisterHandler(MsgTypeWebhookEvent, func(msg IPCMessage) error {
		log.Printf("Webhook event received: %+v", msg.Data)

		// Log webhook event to database
		if im.database != nil {
			logRecord := LogRecord{
				Timestamp: time.Now(),
				Level:     "info",
				Component: "webhook",
				Message:   fmt.Sprintf("Webhook event: %v", msg.Data),
			}
			im.database.InsertLog(logRecord)
		}

		return nil
	})

	// Handle external updates (from bidirectional sync)
	im.ipcServer.RegisterHandler(MsgTypeExternalUpdate, func(msg IPCMessage) error {
		log.Printf("External update received: %+v", msg.Data)

		// Log external update to database
		if im.database != nil {
			logRecord := LogRecord{
				Timestamp: time.Now(),
				Level:     "info",
				Component: "external_sync",
				Message:   fmt.Sprintf("External update: %v", msg.Data),
			}
			im.database.InsertLog(logRecord)
		}

		return nil
	})

	// Handle workspace reload requests
	im.ipcServer.RegisterHandler(MsgTypeWorkspaceReload, func(msg IPCMessage) error {
		log.Println("Workspace reload requested")

		newCfg, err := LoadWorkspacesConfig()
		if err != nil {
			log.Printf("Failed to reload workspaces.yaml: %v", err)
			return nil
		}

		if newCfg == nil {
			log.Println("workspaces.yaml removed — single-repo mode will be active on restart")
			return nil
		}

		for _, ws := range im.workspaceMonitors {
			if ws.gitMonitor != nil {
				ws.gitMonitor.Stop()
			}
		}

		var newMonitors []*WorkspaceMonitor
		for _, ws := range newCfg.GetEnabledWorkspaces() {
			gm, err := NewGitMonitor(ws.Path)
			if err != nil {
				log.Printf("Warning: skipping workspace %q (%s) on reload: %v", ws.Name, ws.Path, err)
				continue
			}
			wsMon := &WorkspaceMonitor{
				gitMonitor:      gm,
				workspaceName:   ws.Name,
				pmPlatform:      ws.PMPlatform,
				pmProject:       ws.PMProject,
				pmAssignee:      ws.PMAssignee,
				pmIterationPath: ws.PMIterationPath,
				pmAreaPath:      ws.PMAreaPath,
				pmMilestone:     ws.PMMilestone,
			}
			newMonitors = append(newMonitors, wsMon)
		}

		im.workspaceMonitors = newMonitors

		for _, wsMon := range im.workspaceMonitors {
			wsCopy := wsMon
			if err := wsCopy.gitMonitor.Start(func(commit CommitInfo) {
				im.handleCommitForWorkspace(commit, wsCopy)
			}); err != nil {
				log.Printf("Warning: failed to start git monitor for %q on reload: %v", wsCopy.workspaceName, err)
			}
		}

		log.Printf("Workspace reload complete: %d workspace(s) active", len(im.workspaceMonitors))
		return nil
	})
}

// Helper functions to extract values from map[string]interface{}
func getStringFromMap(m map[string]interface{}, key string) string {
	if val, ok := m[key]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return ""
}

func getBoolFromMap(m map[string]interface{}, key string) bool {
	if val, ok := m[key]; ok {
		if b, ok := val.(bool); ok {
			return b
		}
	}
	return false
}

// handleCommitForWorkspace is called when a Git commit is detected on a specific workspace
func (im *IntegratedMonitor) handleCommitForWorkspace(commit CommitInfo, ws *WorkspaceMonitor) {
	im.lastActiveWorkspaceMu.Lock()
	im.lastActiveWorkspace = ws
	im.lastActiveWorkspaceMu.Unlock()

	event := TriggerEvent{
		Type:            TriggerTypeCommit,
		Timestamp:       commit.Timestamp,
		Source:          "git",
		Data:            commit,
		RepoPath:        ws.gitMonitor.repoPath,
		WorkspaceName:   ws.workspaceName,
		PMPlatform:      ws.pmPlatform,
		PMProject:       ws.pmProject,
		PMAssignee:      ws.pmAssignee,
		PMIterationPath: ws.pmIterationPath,
		PMAreaPath:      ws.pmAreaPath,
		PMMilestone:     ws.pmMilestone,
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

	var ipcMsg IPCMessage
	var triggerRecord TriggerRecord

	switch event.Type {
	case TriggerTypeCommit:
		if commit, ok := event.Data.(CommitInfo); ok {
			fmt.Printf("Commit:    %s\n", commit.Hash[:12])
			fmt.Printf("Message:   %s\n", commit.Message)
			fmt.Printf("Author:    %s\n", commit.Author)
			if len(commit.Files) > 0 {
				fmt.Printf("Files:     %d changed\n", len(commit.Files))
			}
			if event.WorkspaceName != "" {
				fmt.Printf("Workspace: %s (%s)\n", event.WorkspaceName, event.PMPlatform)
			}

			// Create IPC message for commit trigger
			ipcMsg = CreateCommitTriggerMessage(CommitTriggerData{
				RepoPath:        event.RepoPath,
				CommitHash:      commit.Hash,
				CommitMessage:   commit.Message,
				Author:          commit.Author,
				Timestamp:       commit.Timestamp.Format(time.RFC3339),
				FilesChanged:    commit.Files,
				Branch:          "", // Branch info not available in CommitInfo
				WorkspaceName:   event.WorkspaceName,
				PMPlatform:      event.PMPlatform,
				PMProject:       event.PMProject,
				PMAssignee:      event.PMAssignee,
				PMIterationPath: event.PMIterationPath,
				PMAreaPath:      event.PMAreaPath,
				PMMilestone:     event.PMMilestone,
			})

			// Prepare database record
			triggerRecord = TriggerRecord{
				TriggerType:   "commit",
				Timestamp:     event.Timestamp,
				Source:        "git",
				RepoPath:      event.RepoPath,
				CommitHash:    commit.Hash,
				CommitMessage: commit.Message,
				Author:        commit.Author,
				Processed:     false,
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

			// Create IPC message for timer trigger
			triggerCount := 0
			intervalMins := im.config.Settings.PromptInterval
			if count, ok := data["trigger_count"].(int); ok {
				triggerCount = count
			}

			timerData := TimerTriggerData{
				Timestamp:    event.Timestamp.Format(time.RFC3339),
				IntervalMins: intervalMins,
				TriggerCount: triggerCount,
			}

			im.lastActiveWorkspaceMu.Lock()
			lastWS := im.lastActiveWorkspace
			im.lastActiveWorkspaceMu.Unlock()
			if lastWS != nil {
				timerData.WorkspaceName   = lastWS.workspaceName
				timerData.PMPlatform      = lastWS.pmPlatform
				timerData.PMProject       = lastWS.pmProject
				timerData.PMAssignee      = lastWS.pmAssignee
				timerData.PMIterationPath = lastWS.pmIterationPath
				timerData.PMAreaPath      = lastWS.pmAreaPath
				timerData.PMMilestone     = lastWS.pmMilestone
			}

			ipcMsg = CreateTimerTriggerMessage(timerData)

			// Prepare database record
			triggerRecord = TriggerRecord{
				TriggerType: "timer",
				Timestamp:   event.Timestamp,
				Source:      "scheduler",
				Processed:   false,
			}
		}
	}

	// Log trigger to database
	if im.database != nil {
		triggerID, err := im.database.InsertTrigger(triggerRecord)
		if err != nil {
			log.Printf("Failed to log trigger to database: %v", err)
		} else {
			log.Printf("✓ Logged trigger to database (ID: %d)", triggerID)
		}
	}

	// Send IPC message to Python (with store-and-forward)
	if im.messageQueue != nil {
		if err := im.messageQueue.SendOrQueue(ipcMsg); err != nil {
			log.Printf("Failed to send/queue IPC message: %v", err)
		} else if im.ipcServer.HasClients() {
			log.Println("✓ Sent trigger to Python via IPC")
		} else {
			log.Println("✓ Trigger queued for delivery when Python reconnects")
		}
	} else if im.ipcServer != nil {
		if err := im.ipcServer.SendMessage(ipcMsg); err != nil {
			log.Printf("Failed to send IPC message: %v", err)
		} else {
			log.Println("✓ Sent trigger to Python via IPC")
		}
	}

	fmt.Println()
	fmt.Println("📝 What happens next:")
	fmt.Println("   1. Python receives trigger via IPC")
	fmt.Println("   2. Prompt user: 'What did you work on?'")
	fmt.Println("   3. Parse text with NLP (spaCy)")
	fmt.Println("   4. Match to existing tasks (semantic matching)")
	fmt.Println("   5. Update Azure DevOps / GitHub / JIRA")
	fmt.Println("   6. Logged to SQLite database ✓")
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
	status["workspace_count"] = len(im.workspaceMonitors)
	if len(im.workspaceMonitors) > 0 {
		status["repo_path"] = im.workspaceMonitors[0].gitMonitor.repoPath
	}
	if len(im.workspaceMonitors) > 1 {
		paths := make([]string, len(im.workspaceMonitors))
		for i, ws := range im.workspaceMonitors {
			paths[i] = ws.gitMonitor.repoPath
		}
		status["all_repo_paths"] = paths
	}

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
				fmt.Printf("  Workspaces: %v\n", status["workspace_count"])
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
