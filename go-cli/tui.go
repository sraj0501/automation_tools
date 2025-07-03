package main

import (
	"fmt"
	"os/exec"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textarea"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/common-nighthawk/go-figure"
)

type model struct {
	choices       []string
	cursor        int
	textarea      textarea.Model
	showInput     bool
	loading       bool
	statusMessage string
	spinner       spinner.Model
}

func initialModel() model {
	ti := textarea.New()
	ti.Placeholder = "Enter your daily update here..."
	ti.Focus()

	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))

	return model{
		choices: []string{
			"Parse daily update from text",
			"Update MS Lists",
			"Generate Email",
			"Create Subtasks",
			"Exit",
		},
		textarea:  ti,
		showInput: false,
		loading:   false,
		spinner:   s,
	}
}

func (m model) Init() tea.Cmd {
	return tea.Batch(textarea.Blink, m.spinner.Tick)
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd
	var cmds []tea.Cmd

	if m.showInput {
		m.textarea, cmd = m.textarea.Update(msg)
		cmds = append(cmds, cmd)

		switch msg := msg.(type) {
		case tea.KeyMsg:
			switch msg.Type {
			case tea.KeyEsc:
				m.showInput = false
			case tea.KeyCtrlC:
				return m, tea.Quit
			case tea.KeyEnter:
				m.showInput = false
				m.loading = true
				m.statusMessage = "Parsing daily update..."
				return m, tea.Batch(
					m.spinner.Tick,
					runPythonScript("../backend/ai/create_tasks.py", m.textarea.Value()),
				)
			}
		}
		return m, tea.Batch(cmds...)
	}

	if m.loading {
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	}

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "down", "j":
			if m.cursor < len(m.choices)-1 {
				m.cursor++
			}
		case "enter", " ":
			switch m.choices[m.cursor] {
			case "Parse daily update from text":
				m.showInput = true
			case "Update MS Lists":
				m.loading = true
				m.statusMessage = "Updating MS Lists..."
				return m, tea.Batch(
					m.spinner.Tick,
					runPythonScript("../backend/azure/azure_updator.py", ""),
				)
			case "Generate Email":
				m.loading = true
				m.statusMessage = "Generating Email..."
				return m, tea.Batch(
					m.spinner.Tick,
					runPythonScript("../backend/msgraph_python/main.py", ""),
				)
			case "Create Subtasks":
				m.loading = true
				m.statusMessage = "Creating Subtasks..."
				return m, tea.Batch(
					m.spinner.Tick,
					runPythonScript("../backend/azure/fetch_stories.py", ""),
				)


			case "Exit":
				return m, tea.Quit
			}
		}
	case scriptFinishedMsg:
		m.loading = false
		m.statusMessage = msg.message
	}

	return m, nil
}

func (m model) View() string {
	if m.showInput {
		return lipgloss.JoinVertical(lipgloss.Left,
			titleStyle.Render("Enter your daily update"),
			textAreaStyle.Render(m.textarea.View()),
			helpStyle.Render("Press Enter to submit, Esc to go back"),
		)
	}

	if m.loading {
		return lipgloss.JoinHorizontal(lipgloss.Left,
			m.spinner.View(),
			statusStyle.Render(m.statusMessage),
		)
	}

	var s strings.Builder
	myFigure := figure.NewFigure("AI Task Manager", "", true)
	s.WriteString(myFigure.String())
	s.WriteString("\n")

	for i, choice := range m.choices {
		cursor := " "
		if m.cursor == i {
			cursor = ">"
		}
		s.WriteString(fmt.Sprintf("%s %s\n", cursor, choice))
	}

	s.WriteString("\n")
	s.WriteString(helpStyle.Render("Use the arrow keys to navigate, and press Enter to select."))
	s.WriteString("\n")
	s.WriteString(helpStyle.Render("Press 'q' to quit."))
	s.WriteString("\n\n")
	s.WriteString(statusStyle.Render(m.statusMessage))

	return s.String()
}

type scriptFinishedMsg struct{ message string }

func runPythonScript(scriptPath, inputText string) tea.Cmd {
	return func() tea.Msg {
		var cmd *exec.Cmd
		if inputText != "" {
			cmd = exec.Command("python", scriptPath, inputText)
		} else {
			cmd = exec.Command("python", scriptPath)
		}

		output, err := cmd.CombinedOutput()
		if err != nil {
			return scriptFinishedMsg{message: fmt.Sprintf("Error: %s", err)}
		}
		return scriptFinishedMsg{message: string(output)}
	}
}
