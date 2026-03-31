package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"
)

// HTTPTriggerClient sends trigger events to the Python backend via HTTPS POST.
// Always used — both managed and external modes now communicate over HTTP.
// When TLS is enabled (default) the client pins the self-signed cert generated
// at daemon startup so no InsecureSkipVerify is needed.
type HTTPTriggerClient struct {
	serverURL  string
	apiKey     string
	httpClient *http.Client
}

// NewHTTPTriggerClient builds a client pointing at GetServerURL().
// If TLS is enabled it loads the daemon-generated cert from GetTLSCertPath()
// and uses it as the sole trusted root (cert-pinning).
func NewHTTPTriggerClient() *HTTPTriggerClient {
	transport := &http.Transport{}

	if IsLocalTLS() {
		// Cert-pin the locally generated self-signed cert (managed / external-local mode).
		// In cloud mode we skip pinning and use system CA roots instead.
		pool, err := LoadTLSCertPool(GetTLSCertPath())
		if err != nil {
			log.Printf("Warning: could not load TLS cert for HTTP client (%v) — falling back to system roots", err)
		} else {
			transport.TLSClientConfig = &tls.Config{
				RootCAs:    pool,
				MinVersion: tls.VersionTLS12,
			}
		}
	}

	return &HTTPTriggerClient{
		serverURL: GetServerURL(),
		apiKey:    GetCloudAPIKey(),
		httpClient: &http.Client{
			Timeout:   30 * time.Second,
			Transport: transport,
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

// SendWorkspaceReload POSTs a workspace-reload notification to Python.
func (c *HTTPTriggerClient) SendWorkspaceReload() error {
	return c.post("/trigger/workspace_reload", map[string]string{"source": "cli"})
}

// SendShutdown notifies Python to perform a graceful shutdown.
func (c *HTTPTriggerClient) SendShutdown() error {
	return c.post("/trigger/shutdown", map[string]string{})
}

// SendPing checks liveness via /trigger/ping.
func (c *HTTPTriggerClient) SendPing() error {
	return c.post("/trigger/ping", map[string]string{})
}

// SendWorkSessionStart notifies Python that a work session has started.
func (c *HTTPTriggerClient) SendWorkSessionStart(sessionID int64, ticketRef string) error {
	return c.post("/trigger/work_session_start", map[string]interface{}{
		"session_id": sessionID,
		"ticket_ref": ticketRef,
	})
}

// SendWorkSessionStop notifies Python that a work session has ended.
func (c *HTTPTriggerClient) SendWorkSessionStop(sessionID int64) error {
	return c.post("/trigger/work_session_stop", map[string]interface{}{
		"session_id": sessionID,
	})
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
