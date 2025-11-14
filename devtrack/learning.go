package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// LearningCommands handles personalized AI learning commands
type LearningCommands struct {
	pythonPath string
	scriptPath string
}

// NewLearningCommands creates a new learning commands handler
func NewLearningCommands() *LearningCommands {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		homeDir = "."
	}

	return &LearningCommands{
		pythonPath: "python3",
		scriptPath: filepath.Join(homeDir, "git_apps/personal/automation_tools/backend/learning_integration.py"),
	}
}

// EnableLearning starts collecting communication data and enables learning
func (lc *LearningCommands) EnableLearning(days int) error {
	fmt.Println("🧠 Enabling personalized AI learning...")
	fmt.Println()

	if days <= 0 {
		days = 30
	}

	cmd := exec.Command(lc.pythonPath, lc.scriptPath, "enable-learning", fmt.Sprintf("%d", days))
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to enable learning: %w", err)
	}

	return nil
}

// ShowProfile displays the current learning profile
func (lc *LearningCommands) ShowProfile() error {
	cmd := exec.Command(lc.pythonPath, lc.scriptPath, "show-profile")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to show profile: %w", err)
	}

	return nil
}

// TestResponse tests generating a personalized response
func (lc *LearningCommands) TestResponse(text string) error {
	fmt.Println("🤖 Testing response generation...")
	fmt.Println()

	args := []string{lc.scriptPath, "test-response"}
	args = append(args, strings.Split(text, " ")...)

	cmd := exec.Command(lc.pythonPath, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to test response: %w", err)
	}

	return nil
}

// RevokeConsent revokes learning consent
func (lc *LearningCommands) RevokeConsent() error {
	fmt.Println("⚠️  Revoking personalized learning consent...")
	fmt.Println()

	cmd := exec.Command(lc.pythonPath, lc.scriptPath, "revoke-consent")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to revoke consent: %w", err)
	}

	return nil
}

// GetLearningStatus gets the status of personalized learning
func (lc *LearningCommands) GetLearningStatus() (*LearningStatus, error) {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return nil, err
	}

	learningDir := filepath.Join(homeDir, ".devtrack", "learning")
	consentFile := filepath.Join(learningDir, "consent.json")
	profileFile := filepath.Join(learningDir, "profile.json")
	samplesFile := filepath.Join(learningDir, "samples.json")

	status := &LearningStatus{
		Enabled:      false,
		SampleCount:  0,
		LastUpdated:  "",
		ConsentGiven: false,
	}

	// Check consent
	if _, err := os.Stat(consentFile); err == nil {
		data, err := os.ReadFile(consentFile)
		if err == nil {
			var consent map[string]interface{}
			if err := json.Unmarshal(data, &consent); err == nil {
				if given, ok := consent["consent_given"].(bool); ok {
					status.ConsentGiven = given
					status.Enabled = given
				}
			}
		}
	}

	// Count samples
	if _, err := os.Stat(samplesFile); err == nil {
		data, err := os.ReadFile(samplesFile)
		if err == nil {
			var samples []interface{}
			if err := json.Unmarshal(data, &samples); err == nil {
				status.SampleCount = len(samples)
			}
		}
	}

	// Get profile update time
	if info, err := os.Stat(profileFile); err == nil {
		status.LastUpdated = info.ModTime().Format("2006-01-02 15:04:05")
	}

	return status, nil
}

// LearningStatus represents the status of personalized learning
type LearningStatus struct {
	Enabled      bool   `json:"enabled"`
	ConsentGiven bool   `json:"consent_given"`
	SampleCount  int    `json:"sample_count"`
	LastUpdated  string `json:"last_updated"`
}

// PrintStatus prints the learning status in a formatted way
func (ls *LearningStatus) PrintStatus() {
	fmt.Println()
	fmt.Println("╔══════════════════════════════════════════════════════════╗")
	fmt.Println("║          PERSONALIZED AI LEARNING STATUS                ║")
	fmt.Println("╚══════════════════════════════════════════════════════════╝")
	fmt.Println()

	if ls.ConsentGiven {
		fmt.Println("  Status:        ✅ Enabled")
	} else {
		fmt.Println("  Status:        ❌ Disabled (consent not given)")
	}

	fmt.Printf("  Samples:       %d\n", ls.SampleCount)

	if ls.LastUpdated != "" {
		fmt.Printf("  Last Updated:  %s\n", ls.LastUpdated)
	} else {
		fmt.Println("  Last Updated:  Never")
	}

	fmt.Println()

	if !ls.ConsentGiven {
		fmt.Println("  ℹ️  To enable learning, run: devtrack enable-learning")
		fmt.Println()
	} else if ls.SampleCount == 0 {
		fmt.Println("  ℹ️  No samples collected yet. Learning in progress...")
		fmt.Println()
	} else {
		fmt.Println("  ℹ️  AI is learning from your communication patterns")
		fmt.Println()
	}
}
