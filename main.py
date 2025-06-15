from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def home():
    return {"message":"Welcome"}

@app.get("/api/azure_v1/list/projects")
async def list_issues():
    return {"message":"Issues"}