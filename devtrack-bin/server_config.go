package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
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

// GetServerURL returns the base URL of the Python backend server.
//
// Resolution order:
//  1. DEVTRACK_SERVER_URL env var (explicit override)
//  2. Managed mode default — https://127.0.0.1:<WEBHOOK_PORT>
//
// Both managed and external modes now use HTTP, so this always returns a usable URL.
func GetServerURL() string {
	if v := os.Getenv("DEVTRACK_SERVER_URL"); v != "" {
		return v
	}
	port := os.Getenv("WEBHOOK_PORT")
	if port == "" {
		port = "8089"
	}
	scheme := "https"
	if !IsTLSEnabled() {
		scheme = "http"
	}
	return scheme + "://127.0.0.1:" + port
}

// IsTLSEnabled reports whether TLS is enabled for the Go↔Python HTTP channel.
// Defaults to true; set DEVTRACK_TLS=false to disable (dev / Docker environments).
func IsTLSEnabled() bool {
	v := os.Getenv("DEVTRACK_TLS")
	if v == "" {
		return true // on by default
	}
	b, err := strconv.ParseBool(v)
	if err != nil {
		return true
	}
	return b
}

// GetTLSCertPath returns the path to the TLS server certificate PEM file.
// Uses DEVTRACK_TLS_CERT if set, otherwise Data/tls/server.crt under the database dir.
func GetTLSCertPath() string {
	if v := os.Getenv("DEVTRACK_TLS_CERT"); v != "" {
		return v
	}
	return filepath.Join(filepath.Dir(GetDatabaseDir()), "tls", "server.crt")
}

// GetTLSKeyPath returns the path to the TLS private key PEM file.
// Uses DEVTRACK_TLS_KEY if set, otherwise Data/tls/server.key under the database dir.
func GetTLSKeyPath() string {
	if v := os.Getenv("DEVTRACK_TLS_KEY"); v != "" {
		return v
	}
	return filepath.Join(filepath.Dir(GetDatabaseDir()), "tls", "server.key")
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
