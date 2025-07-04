import os
import sys

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# === LOAD ENVIRONMENT VARIABLES ===
if os.path.exists("../../.env"):
    print("✅ .env file found. Loading environment variables.")
    load_dotenv("../../.env")
else:
    print("❌ .env file not found. Please ensure it exists in the correct directory.")
    sys.exit()

# === CONFIGURATION ===
org = os.getenv("ORGANIZATION")
project = os.getenv("PROJECT")
pat = os.getenv("AZURE_API_KEY")
api_version = os.getenv("API_VERSION", "7.1")
assigned_to = os.getenv("EMAIL")

query_url = f"https://dev.azure.com/{org}/{project}/_apis/wit/wiql?api-version={api_version}"
work_item_url = f"https://dev.azure.com/{org}/_apis/wit/workitems"
headers = {"Content-Type": "application/json"}
auth = HTTPBasicAuth('', pat)

# === WIQL QUERY TO FETCH USER STORIES ===
wiql_query = {
    "query": f"""
    SELECT [System.Id],[System.WorkItemType], [System.Title], [System.State], [System.AssignedTo]
    FROM WorkItems
    WHERE [System.TeamProject] = '{project}'
    AND [System.AssignedTo] = '{assigned_to}'
    AND [System.WorkItemType] = 'Product Backlog Item'
    ORDER BY [System.ChangedDate] DESC"""
}

# === EXECUTE QUERY ===
response = requests.post(query_url, json=wiql_query, headers=headers, auth=auth)
if response.status_code != 200:
    print(f"❌ Failed to fetch work items: {response.status_code} - {response.text}")
    sys.exit()

work_item_ids = [item["id"] for item in response.json()["workItems"]]
print(f"🔍 Found {len(work_item_ids)} user stories.")


# === FETCH DETAILS FOR EACH WORK ITEM ===
if work_item_ids:
    ids_str = ",".join(map(str, work_item_ids[:200]))
    details_url = f"{work_item_url}?ids={ids_str}&api-version={api_version}"
    details_response = requests.get(details_url, headers=headers, auth=auth)

    if details_response.status_code == 200:
        items = details_response.json()["value"]
        # print(items)
        data = [{
            "ID": item["id"],
            "WorkItem Type": item["fields"].get("System.WorkItemType",""),
            "Title": item["fields"].get("System.Title", ""),
            "State": item["fields"].get("System.State", ""),
            "Assigned To": item["fields"].get("System.AssignedTo", {}).get("displayName", "Unassigned")
        } for item in items]

        df = pd.DataFrame(data)
        print(df)
    else:
        print(f"❌ Failed to fetch item details: {details_response.status_code} - {details_response.text}")
else:
    print("⚠️ No user stories found.")
