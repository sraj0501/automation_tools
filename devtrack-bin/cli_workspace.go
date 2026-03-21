package main

import (
	"encoding/json"
	"fmt"
	"net"
	"strings"
	"time"
)

// WorkspaceCommands handles workspace management commands
type WorkspaceCommands struct{}

// NewWorkspaceCommands creates a new WorkspaceCommands handler
func NewWorkspaceCommands() *WorkspaceCommands {
	return &WorkspaceCommands{}
}

// List prints all configured workspaces from workspaces.yaml
func (wc *WorkspaceCommands) List() error {
	cfg, err := LoadWorkspacesConfig()
	if err != nil {
		fmt.Printf("Failed to load workspaces.yaml: %v\n", err)
		return err
	}

	if cfg == nil || len(cfg.Workspaces) == 0 {
		fmt.Println("No workspaces.yaml found. Running in single-repo mode.")
		return nil
	}

	fmt.Printf("%-20s %-40s %-12s %s\n", "NAME", "PATH", "PLATFORM", "ENABLED")
	fmt.Println(strings.Repeat("-", 80))
	for _, ws := range cfg.Workspaces {
		enabled := "no"
		if ws.Enabled {
			enabled = "yes"
		}
		platform := ws.PMPlatform
		if platform == "" {
			platform = "(none)"
		}
		fmt.Printf("%-20s %-40s %-12s %s\n", ws.Name, ws.Path, platform, enabled)
	}

	return nil
}

// Add adds a new workspace entry to workspaces.yaml (creating it if needed)
func (wc *WorkspaceCommands) Add(name, path, pmPlatform string) error {
	path = expandWorkspacePath(path)

	if !IsGitRepository(path) {
		return fmt.Errorf("not a git repository: %s", path)
	}

	cfg, err := LoadWorkspacesConfig()
	if err != nil {
		return fmt.Errorf("failed to load workspaces.yaml: %w", err)
	}

	if cfg == nil {
		cfg = &WorkspacesConfig{
			Version:    "1",
			Workspaces: []WorkspaceConfig{},
		}
	}

	for _, ws := range cfg.Workspaces {
		if ws.Name == name {
			return fmt.Errorf("workspace %q already exists", name)
		}
	}

	cfg.Workspaces = append(cfg.Workspaces, WorkspaceConfig{
		Name:       name,
		Path:       path,
		PMPlatform: pmPlatform,
		Enabled:    true,
	})

	if err := cfg.Save(); err != nil {
		return fmt.Errorf("failed to save workspaces.yaml: %w", err)
	}

	fmt.Printf("Added workspace %q (%s)\n", name, path)
	fmt.Println("Run 'devtrack workspace reload' to apply changes to the running daemon.")
	return nil
}

// Remove removes a workspace by name from workspaces.yaml
func (wc *WorkspaceCommands) Remove(name string) error {
	cfg, err := LoadWorkspacesConfig()
	if err != nil {
		return fmt.Errorf("failed to load workspaces.yaml: %w", err)
	}

	if cfg == nil {
		return fmt.Errorf("workspaces.yaml not found")
	}

	found := false
	updated := cfg.Workspaces[:0]
	for _, ws := range cfg.Workspaces {
		if ws.Name == name {
			found = true
			continue
		}
		updated = append(updated, ws)
	}

	if !found {
		return fmt.Errorf("workspace %q not found", name)
	}

	cfg.Workspaces = updated

	if err := cfg.Save(); err != nil {
		return fmt.Errorf("failed to save workspaces.yaml: %w", err)
	}

	fmt.Printf("Removed workspace %q\n", name)
	fmt.Println("Run 'devtrack workspace reload' to apply changes to the running daemon.")
	return nil
}

// Enable sets enabled=true for a workspace by name
func (wc *WorkspaceCommands) Enable(name string) error {
	return wc.setEnabled(name, true)
}

// Disable sets enabled=false for a workspace by name
func (wc *WorkspaceCommands) Disable(name string) error {
	return wc.setEnabled(name, false)
}

func (wc *WorkspaceCommands) setEnabled(name string, enabled bool) error {
	cfg, err := LoadWorkspacesConfig()
	if err != nil {
		return fmt.Errorf("failed to load workspaces.yaml: %w", err)
	}

	if cfg == nil {
		return fmt.Errorf("workspaces.yaml not found")
	}

	found := false
	for i := range cfg.Workspaces {
		if cfg.Workspaces[i].Name == name {
			cfg.Workspaces[i].Enabled = enabled
			found = true
			break
		}
	}

	if !found {
		return fmt.Errorf("workspace %q not found", name)
	}

	if err := cfg.Save(); err != nil {
		return fmt.Errorf("failed to save workspaces.yaml: %w", err)
	}

	state := "enabled"
	if !enabled {
		state = "disabled"
	}
	fmt.Printf("Workspace %q %s\n", name, state)
	fmt.Println("Run 'devtrack workspace reload' to apply changes to the running daemon.")
	return nil
}

// Reload sends MsgTypeWorkspaceReload to the running daemon via IPC
func (wc *WorkspaceCommands) Reload() error {
	addr := GetIPCAddress()

	conn, err := net.DialTimeout("tcp", addr, 5*time.Second)
	if err != nil {
		return fmt.Errorf("failed to connect to daemon IPC at %s: %w", addr, err)
	}
	defer conn.Close()

	msg := IPCMessage{
		Type:      MsgTypeWorkspaceReload,
		Timestamp: time.Now(),
		ID:        fmt.Sprintf("reload_%d", time.Now().UnixNano()),
		Data:      make(map[string]interface{}),
	}

	data, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("failed to marshal reload message: %w", err)
	}
	data = append(data, '\n')

	if _, err := conn.Write(data); err != nil {
		return fmt.Errorf("failed to send reload message: %w", err)
	}

	fmt.Println("Workspace reload signal sent to daemon.")
	return nil
}
