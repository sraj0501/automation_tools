import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv(".env")

def convert_to_ist(date_val, date_format):
    utc_timestamp = date_val
    utc_time = datetime.strptime(utc_timestamp, date_format)
    # utc_time = datetime.strptime(utc_timestamp, "%Y-%m-%dT%H:%M:%SZ")
    ist_offset = timedelta(hours=5, minutes=30)
    ist_time = utc_time + ist_offset
    return ist_time.date()

def get_top_commits(owner, repo, branch, token, end_date, filename="commits.log"):
  url = f"https://api.github.com/repos/{owner}/{repo}/commits?sha={branch}"
  headers = {"Authorization": f"Bearer {token}"}

  response = requests.get(url, headers=headers)
  commits = response.json()
  for i in commits:
      print(i)


if __name__ == "__main__":
    auth_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("OWNER_NAME")
    repo_name = os.getenv("REPO")
    repo_branch = os.getenv("BRANCH_NAME")
    get_top_commits(owner=repo_owner, repo=repo_name, branch=repo_branch, token=auth_token, end_date=60)