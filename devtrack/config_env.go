package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	
	"github.com/joho/godotenv"
)

// EnvConfig holds all environment configuration
// All fields are REQUIRED - no fallbacks
type EnvConfig struct {
	// Paths
	ProjectRoot    string
	DevTrackHome   string
	Workspace      string
	
	// IPC Configuration
	IPCHost        string
	IPCPort        string
	
	// File names
	PythonBridgeScript string
	CLIBinaryName      string
	ConfigFileName     string
	DatabaseFileName   string
	PIDFileName        string
	LogFileName        string
	
	// Directory names
	LearningDirName    string
	ConfigDirName      string
	
	// CLI identifiers
	CLIAppName         string
	CLIDaemonName      string
	
	// External services
	OllamaHost         string
}

var envConfig *EnvConfig

// requiredEnvVars lists all required environment variables
var requiredEnvVars = []string{
	"PROJECT_ROOT",
	"DEVTRACK_HOME",
	"IPC_HOST",
	"IPC_PORT",
	"PYTHON_BRIDGE_SCRIPT",
	"CLI_BINARY_NAME",
	"CONFIG_FILE_NAME",
	"DATABASE_FILE_NAME",
	"PID_FILE_NAME",
	"LOG_FILE_NAME",
	"LEARNING_DIR_NAME",
	"CONFIG_DIR_NAME",
	"CLI_APP_NAME",
	"CLI_DAEMON_NAME",
	"DEVTRACK_WORKSPACE",
	"OLLAMA_HOST",
}

// LoadEnvConfig loads configuration from .env files and environment variables
// Returns error if any required variable is missing
func LoadEnvConfig() (*EnvConfig, error) {
	if envConfig != nil {
		return envConfig, nil
	}
	
	// Try multiple locations for .env file
	homeDir, _ := os.UserHomeDir()
	envPaths := []string{
		os.Getenv("DEVTRACK_ENV_FILE"),                                     // Custom env var
		filepath.Join(homeDir, ".config", "devtrack", ".env"),              // XDG config
		filepath.Join(homeDir, ".devtrack", ".env"),                        // Home config
		filepath.Join(homeDir, "Documents", "GitHub", "automation_tools", ".env"), // Project dir
		"../.env",                                                          // Relative (when run from devtrack/)
		".env",                                                             // Current dir
	}
	
	envLoaded := false
	for _, envPath := range envPaths {
		if envPath != "" && fileExists(envPath) {
			if err := godotenv.Load(envPath); err == nil {
				envLoaded = true
				break
			}
		}
	}
	
	if !envLoaded {
		return nil, fmt.Errorf("no .env file found. Checked:\n%s", strings.Join(envPaths, "\n"))
	}
	
	// Check all required variables
	missing := []string{}
	for _, key := range requiredEnvVars {
		if os.Getenv(key) == "" {
			missing = append(missing, key)
		}
	}
	
	if len(missing) > 0 {
		return nil, fmt.Errorf("missing required environment variables:\n%s", strings.Join(missing, "\n"))
	}
	
	// Build config from environment
	config := &EnvConfig{
		ProjectRoot:        expandPath(os.Getenv("PROJECT_ROOT")),
		DevTrackHome:       expandPath(os.Getenv("DEVTRACK_HOME")),
		IPCHost:            os.Getenv("IPC_HOST"),
		IPCPort:            os.Getenv("IPC_PORT"),
		PythonBridgeScript: os.Getenv("PYTHON_BRIDGE_SCRIPT"),
		CLIBinaryName:      os.Getenv("CLI_BINARY_NAME"),
		ConfigFileName:     os.Getenv("CONFIG_FILE_NAME"),
		DatabaseFileName:   os.Getenv("DATABASE_FILE_NAME"),
		PIDFileName:        os.Getenv("PID_FILE_NAME"),
		LogFileName:        os.Getenv("LOG_FILE_NAME"),
		LearningDirName:    os.Getenv("LEARNING_DIR_NAME"),
		ConfigDirName:      os.Getenv("CONFIG_DIR_NAME"),
		CLIAppName:         os.Getenv("CLI_APP_NAME"),
		CLIDaemonName:      os.Getenv("CLI_DAEMON_NAME"),
		Workspace:          expandPath(os.Getenv("DEVTRACK_WORKSPACE")),
		OllamaHost:         os.Getenv("OLLAMA_HOST"),
	}
	
	envConfig = config
	return config, nil
}

// expandPath expands ~ to home directory
func expandPath(path string) string {
	if strings.HasPrefix(path, "~/") {
		homeDir, _ := os.UserHomeDir()
		return filepath.Join(homeDir, path[2:])
	}
	return path
}

// fileExists checks if a file exists
func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// GetDevTrackDir returns the DevTrack home directory
func GetDevTrackDir() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	return config.DevTrackHome
}

// GetIPCAddress returns the full IPC address (host:port)
func GetIPCAddress() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	return config.IPCHost + ":" + config.IPCPort
}

// GetPythonBridgePath returns the path to python_bridge.py
func GetPythonBridgePath() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	
	path := filepath.Join(config.ProjectRoot, config.PythonBridgeScript)
	if !fileExists(path) {
		fmt.Fprintf(os.Stderr, "ERROR: Python bridge script not found at: %s\n", path)
		fmt.Fprintf(os.Stderr, "Check PROJECT_ROOT and PYTHON_BRIDGE_SCRIPT in .env file\n")
		os.Exit(1)
	}
	
	return path
}

// GetConfigFileName returns the config file name
func GetConfigFileName() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	return config.ConfigFileName
}

// GetDatabaseFileName returns the database file name
func GetDatabaseFileName() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	return config.DatabaseFileName
}

// GetPIDFileName returns the PID file name
func GetPIDFileName() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	return config.PIDFileName
}

// GetLogFileName returns the log file name
func GetLogFileName() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	return config.LogFileName
}

// GetLearningDirName returns the learning directory name
func GetLearningDirName() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	return config.LearningDirName
}

// GetCLIAppName returns the CLI application name
func GetCLIAppName() string {
	config, err := LoadEnvConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	return config.CLIAppName
}
