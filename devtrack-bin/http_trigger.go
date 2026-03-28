package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

// HTTPTriggerClient sends trigger events to the Python backend via HTTP POST.
// Used when DEVTRACK_SERVER_MODE=external and DEVTRACK_SERVER_URL is configured.
// In managed mode this is never instantiated — IPC is used instead.
type HTTPTriggerClient struct {
	serverURL  string
	apiKey     string
	httpClient *http.Client
}

// NewHTTPTriggerClient builds a client aimed at DEVTRACK_SERVER_URL.
func NewHTTPTriggerClient() *HTTPTriggerClient {
	return &HTTPTriggerClient{
		serverURL: GetServerURL(),
		apiKey:    os.Getenv("DEVTRACK_API_KEY"),
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Ping checks whether the Python server is reachable and healthy.
func (c *HTTPTriggerClient) Ping() bool {
	if c.serverURL == "" {
		return false
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, "GET", c.serverURL+"/health", nil)
	if err != nil {
		return false
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return false
	}
	resp.Body.Close()
	return resp.StatusCode == 200
}

// SendCommitTrigger POSTs a commit trigger payload to POST /trigger/commit.
func (c *HTTPTriggerClient) SendCommitTrigger(data CommitTriggerData) error {
	return c.post("/trigger/commit", data)
}

// SendTimerTrigger POSTs a timer trigger payload to POST /trigger/timer.
func (c *HTTPTriggerClient) SendTimerTrigger(data TimerTriggerData) error {
	return c.post("/trigger/timer", data)
}

func (c *HTTPTriggerClient) post(path string, payload interface{}) error {
	if c.serverURL == "" {
		return fmt.Errorf("DEVTRACK_SERVER_URL is not set")
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal payload: %w", err)
	}

	req, err := http.NewRequest("POST", c.serverURL+path, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if c.apiKey != "" {
		req.Header.Set("X-DevTrack-API-Key", c.apiKey)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("POST %s%s: %w", c.serverURL, path, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("server returned HTTP %d for %s", resp.StatusCode, path)
	}

	log.Printf("✓ Trigger sent via HTTP → %s%s (%d)", c.serverURL, path, resp.StatusCode)
	return nil
}
