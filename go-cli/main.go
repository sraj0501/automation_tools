package main

import (
	"fmt"
	"os"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	// Check if CLI command is provided
	if len(os.Args) > 1 {
		cmd := os.Args[1]

		// Handle test commands
		if strings.HasPrefix(cmd, "test-") {
			RunDemo()
			return
		}

		// Handle daemon commands
		if cmd == "start" || cmd == "stop" || cmd == "restart" ||
			cmd == "status" || cmd == "pause" || cmd == "resume" ||
			cmd == "logs" || cmd == "version" || cmd == "help" {
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
	}

	// Default: Run TUI
	p := tea.NewProgram(initialModel())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Alas, there's been an error: %v", err)
		os.Exit(1)
	}
}
