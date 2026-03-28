package main

import (
	"fmt"
	"os"
)

// ServerMode defines how the Python backend is managed
type ServerMode string

const (
	// ServerModeManaged — daemon spawns Python backend as subprocess (default for local use)
	ServerModeManaged ServerMode = "managed"
	// ServerModeExternal — Python backend runs independently; daemon does not spawn it
	ServerModeExternal ServerMode = "external"
)

// GetServerMode returns the configured server mode.
// Defaults to "managed" (spawn subprocess) if DEVTRACK_SERVER_MODE is unset.
func GetServerMode() ServerMode {
	if os.Getenv("DEVTRACK_SERVER_MODE") == "external" {
		return ServerModeExternal
	}
	return ServerModeManaged
}

// GetServerURL returns the URL of the Python backend server.
// Used when DEVTRACK_SERVER_MODE=external to log where the daemon expects the server.
func GetServerURL() string {
	return os.Getenv("DEVTRACK_SERVER_URL")
}

// IsExternalServer returns true when the Python backend is managed externally
// (i.e. the daemon should NOT spawn it as a subprocess).
func IsExternalServer() bool {
	return GetServerMode() == ServerModeExternal
}

// RunInstall is called by `devtrack install`. It explains the client-server setup.
func RunInstall() error {
	fmt.Println("DevTrack uses a client-server architecture:")
	fmt.Println()
	fmt.Println("  Go binary (devtrack)  — client/daemon: git monitoring, scheduling, CLI")
	fmt.Println("  Python backend server — AI processing, integrations, reports")
	fmt.Println()
	fmt.Println("Setup options:")
	fmt.Println()
	fmt.Println("  LOCAL — managed (default)")
	fmt.Println("    DEVTRACK_SERVER_MODE=managed in .env")
	fmt.Println("    devtrack start           (daemon spawns Python automatically)")
	fmt.Println()
	fmt.Println("  LOCAL — external (separate process)")
	fmt.Println("    DEVTRACK_SERVER_MODE=external in .env")
	fmt.Println("    python python_bridge.py  (start Python server manually)")
	fmt.Println("    devtrack start           (then start the Go daemon)")
	fmt.Println()
	fmt.Println("  DOCKER")
	fmt.Println("    docker compose up        (starts Python server + infra)")
	fmt.Println()
	fmt.Println("  CLOUD")
	fmt.Println("    DEVTRACK_SERVER_URL=https://your-server.com in .env")
	fmt.Println("    DEVTRACK_SERVER_MODE=external")
	fmt.Println("    devtrack start")
	fmt.Println()
	fmt.Println("See docs/INSTALLATION.md for full setup instructions.")
	return nil
}
