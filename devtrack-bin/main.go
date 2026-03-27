package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func main() {
	// Check if CLI command is provided
	if len(os.Args) > 1 {
		cmd := os.Args[1]

		// Delegate "git" to devtrack-git-wrapper.sh for AI-enhanced commits
		if cmd == "git" {
			runGitWrapper()
			return
		}

		// Delegate "sage" to the Python git-sage module
		if cmd == "sage" {
			runGitSage()
			return
		}

		// Handle test commands (but not CLI commands that start with "test-")
		if strings.HasPrefix(cmd, "test-") && cmd != "test-response" {
			RunDemo()
			return
		}

		// Handle daemon commands
		if cmd == "start" || cmd == "stop" || cmd == "restart" ||
			cmd == "status" || cmd == "pause" || cmd == "resume" ||
			cmd == "logs" || cmd == "version" || cmd == "help" ||
			cmd == "db-stats" || cmd == "stats" || cmd == "enable-learning" || cmd == "show-profile" ||
			cmd == "test-response" || cmd == "revoke-consent" || cmd == "learning-status" ||
			cmd == "preview-report" || cmd == "send-report" || cmd == "save-report" ||
			cmd == "force-trigger" || cmd == "send-summary" || cmd == "skip-next" ||
			cmd == "learning-sync" || cmd == "learning-setup-cron" ||
			cmd == "learning-remove-cron" || cmd == "learning-cron-status" ||
			cmd == "learning-reset" ||
			cmd == "commit-queue" || cmd == "commits" || cmd == "queue" ||
			cmd == "telegram-status" || cmd == "azure-check" || cmd == "azure-list" || cmd == "azure-sync" || cmd == "azure-view" || cmd == "settings" ||
			cmd == "workspace" ||
			cmd == "shell-init" || cmd == "is-workspace" || cmd == "enable-git" || cmd == "disable-git" ||
			cmd == "launchd-install" || cmd == "launchd-uninstall" ||
		cmd == "alerts" {
			cli, err := NewCLI()
			if err != nil {
				fmt.Printf("Error initializing CLI: %v\n", err)
				os.Exit(1)
			}

			if err := cli.Execute(); err != nil {
				os.Exit(1)
			}
			return
		}

		// Unknown command - show help
		fmt.Printf("Unknown command: %s\n\n", cmd)
	}

	// No command or unknown command: show help
	printBasicUsage()
}

// printBasicUsage prints help without requiring config (for no-arg or unknown command)
func printBasicUsage() {
	fmt.Println("DevTrack - Developer Automation Tools")
	fmt.Println("======================================")
	fmt.Println()
	fmt.Println("Usage: devtrack <command> [options]")
	fmt.Println()
	fmt.Println("DAEMON:    start | stop | restart | status")
	fmt.Println("SCHEDULER: pause | resume | force-trigger | skip-next | send-summary")
	fmt.Println("INFO:      logs | db-stats | stats | version | help")
	fmt.Println("GIT:       git add | git commit -m 'message'   (AI-enhanced; shell-init required for bare 'git' commands)")
	fmt.Println("SAGE:      sage ask '<question>' | sage do '<task>' | sage interactive")
	fmt.Println("COMMITS:   commits pending | commits review")
	fmt.Println("ALERTS:    alerts | alerts --all | alerts --clear")
	fmt.Println("REPORTS:   preview-report | send-report | save-report")
	fmt.Println()
	fmt.Println("Run 'devtrack help' for full usage.")
	fmt.Println()
}

// runGitSage delegates to the Python git-sage module, forwarding all args after "sage"
func runGitSage() {
	projectRoot := os.Getenv("PROJECT_ROOT")
	if projectRoot == "" {
		execPath, err := os.Executable()
		if err != nil {
			execPath = os.Args[0]
		}
		execPath, _ = filepath.Abs(execPath)
		searchDir := filepath.Dir(execPath)
		for i := 0; i < 6; i++ {
			if _, err := os.Stat(filepath.Join(searchDir, "backend", "git_sage")); err == nil {
				projectRoot = searchDir
				break
			}
			parent := filepath.Dir(searchDir)
			if parent == searchDir {
				break
			}
			searchDir = parent
		}
	}

	if projectRoot == "" {
		fmt.Println("Error: Could not find backend/git_sage directory")
		fmt.Println("Set PROJECT_ROOT to the automation_tools path")
		os.Exit(1)
	}

	// Forward all args after "sage" to the Python module
	sageArgs := append([]string{"run", "python", "-m", "backend.git_sage"}, os.Args[2:]...)

	env := os.Environ()
	env = append(env, "PROJECT_ROOT="+projectRoot)
	env = append(env, "DEVTRACK_ENV_FILE="+filepath.Join(projectRoot, ".env"))

	cmd := exec.Command("uv", sageArgs...)
	cmd.Dir = projectRoot
	cmd.Env = env
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			os.Exit(exitErr.ExitCode())
		}
		os.Exit(1)
	}
}

// runGitWrapper execs devtrack-git-wrapper.sh for AI-enhanced git commits
func runGitWrapper() {
	projectRoot := os.Getenv("PROJECT_ROOT")
	// Validate PROJECT_ROOT has the wrapper; if not, search from binary
	if projectRoot != "" {
		if _, err := os.Stat(filepath.Join(projectRoot, "devtrack-git-wrapper.sh")); err != nil {
			projectRoot = ""
		}
	}
	if projectRoot == "" {
		// Find project root by walking up from binary, looking for devtrack-git-wrapper.sh
		execPath, err := os.Executable()
		if err != nil {
			execPath = os.Args[0]
		}
		execPath, _ = filepath.Abs(execPath)
		searchDir := filepath.Dir(execPath)
		for i := 0; i < 6; i++ {
			wrapperPath := filepath.Join(searchDir, "devtrack-git-wrapper.sh")
			if _, err := os.Stat(wrapperPath); err == nil {
				projectRoot = searchDir
				break
			}
			parent := filepath.Dir(searchDir)
			if parent == searchDir {
				break
			}
			searchDir = parent
		}
	}

	if projectRoot == "" {
		fmt.Println("Error: Could not find devtrack-git-wrapper.sh")
		fmt.Println("Set PROJECT_ROOT to automation_tools path, or run: ./devtrack-bin/devtrack git commit -m 'message'")
		os.Exit(1)
	}

	wrapperPath := filepath.Join(projectRoot, "devtrack-git-wrapper.sh")

	// Set PROJECT_ROOT and DEVTRACK_ENV_FILE so wrapper finds .env
	env := os.Environ()
	env = append(env, "PROJECT_ROOT="+projectRoot)
	env = append(env, "DEVTRACK_ENV_FILE="+filepath.Join(projectRoot, ".env"))

	cmd := exec.Command("bash", append([]string{wrapperPath}, os.Args[1:]...)...)
	cmd.Env = env
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			os.Exit(exitErr.ExitCode())
		}
		os.Exit(1)
	}
}
