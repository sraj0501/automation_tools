import os
import sys

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

if os.path.exists("../../.env"):
    print("✅ .env file found. Loading environment variables.")
    load_dotenv("../../.env")
else:
    print("❌ .env file not found. Please ensure it exists in the correct directory.")
    sys.exit()


organization = os.getenv("ORGANIZATION")
print(f"Organization: {organization}")

selected_project = ""
pat = os.getenv("AZURE_API_KEY")
user_email = os.getenv("EMAIL")
work_item_id=""
BASE_URI=f"https://dev.azure.com/{organization}/_apis/projects?api-version=7.1"
PROJECT_URI=f"https://dev.azure.com/{organization}/{selected_project}/_apis/wit/wiql?api-version=7.1"
ADD_COMMENT=f"https://dev.azure.com/{organization}/{selected_project}/_apis/wit/workItems/{work_item_id}/comments?api-version=7.1"

# List Projects
# ==========================================================================

# Make the request
response = requests.get(
    BASE_URI,
    auth=HTTPBasicAuth('', pat)
)

project_list = []

if response.status_code == 200:
    projects = response.json()["value"]
    print(f"✅ Found {len(projects)} projects:")
    for i, project in enumerate(projects):
        print(f"{i+1} - {project['name']} (ID: {project['id']})")
        project_list.append(project['name'])
else:
    print("❌ Failed to retrieve projects:", response.status_code)


ch = int(input("Enter a Project index: "))
selected_project = project_list[ch-1]
print(project_list[ch-1])



# List Work Items
# ==========================================================================

# WIQL query to get work items assigned to you
query = {
    "query": f"""
    SELECT [System.Id], [System.Title], [System.State]
    FROM WorkItems
    WHERE [System.AssignedTo] = '{user_email}'
    ORDER BY [System.ChangedDate] DESC
    """
}

# Make the request
response = requests.post(
    PROJECT_URI,
    json=query,
    auth=HTTPBasicAuth('', pat)
)

print(response.json())

if response.status_code == 200:
    work_items = response.json()["workItems"]
    print(f"Found {len(work_items)} work items assigned to you.")
    for item in work_items:
        print(f"- ID [{item['id']}] ")
else:
    print("Error:", response.status_code)
