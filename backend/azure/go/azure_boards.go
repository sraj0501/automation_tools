package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/joho/godotenv"
)

type Project struct {
	Name string `json:"name"`
	ID   string `json:"id"`
}

type ProjectsResponse struct {
	Value []Project `json:"value"`
}

type WorkItemRef struct {
	ID int `json:"id"`
}

type WorkItemsResponse struct {
	WorkItems []WorkItemRef `json:"workItems"`
}

func main() {
	// Load .env
	err := godotenv.Load(".env")
	if err != nil {
		log.Fatal("Error loading .env file")
	}

	organization := os.Getenv("ORGANIZATION")
	pat := os.Getenv("AZURE_API_KEY")
	userEmail := os.Getenv("EMAIL")

	baseURI := fmt.Sprintf("https://dev.azure.com/%s/_apis/projects?api-version=7.1", organization)

	// List Projects
	req, _ := http.NewRequest("GET", baseURI, nil)
	req.SetBasicAuth("", pat)
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		log.Fatal(err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		log.Fatalf("❌ Failed to retrieve projects: %d", resp.StatusCode)
	}

	var projectsResp ProjectsResponse
	json.NewDecoder(resp.Body).Decode(&projectsResp)

	fmt.Printf("✅ Found %d projects:\n", len(projectsResp.Value))
	for i, project := range projectsResp.Value {
		fmt.Printf("%d - %s (ID: %s)\n", i+1, project.Name, project.ID)
	}

	// Prompt user for project selection
	fmt.Print("Enter a Project index: ")
	reader := bufio.NewReader(os.Stdin)
	var ch int
	fmt.Fscanf(reader, "%d\n", &ch)
	selectedProject := projectsResp.Value[ch-1].Name
	fmt.Println(selectedProject)

	// List Work Items
	projectURI := fmt.Sprintf(
		"https://dev.azure.com/%s/%s/_apis/wit/wiql?api-version=7.1",
		organization, selectedProject,
	)

	wiql := fmt.Sprintf(`
    SELECT [System.Id], [System.Title], [System.State]
    FROM WorkItems
    WHERE [System.AssignedTo] = '%s'
    ORDER BY [System.ChangedDate] DESC
    `, userEmail)

	query := fmt.Sprintf(`{"query": %q}`, wiql)
	req2, _ := http.NewRequest("POST", projectURI, strings.NewReader(query))
	req2.Header.Set("Content-Type", "application/json")
	req2.SetBasicAuth("", pat)
	resp2, err := client.Do(req2)
	if err != nil {
		log.Fatal(err)
	}
	defer resp2.Body.Close()

	if resp2.StatusCode != 200 {
		log.Fatalf("Error: %d", resp2.StatusCode)
	}

	var workItemsResp WorkItemsResponse
	json.NewDecoder(resp2.Body).Decode(&workItemsResp)
	fmt.Printf("Found %d work items assigned to you.\n", len(workItemsResp.WorkItems))
	for _, item := range workItemsResp.WorkItems {
		fmt.Printf("- ID: %d\n", item.ID)
	}
}
