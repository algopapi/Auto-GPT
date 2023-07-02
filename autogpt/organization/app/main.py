import uvicorn
from fastapi import FastAPI

from autogpt.organization.app.api.v1.org_pod import router as org_pod_router

app = FastAPI(debug=True)

print("test 2")

@app.get("/health")
def health():
    return {"message":"Hello POD!"}

# add routers
app.include_router(
    org_pod_router, prefix="/api/v1/org_pod", tags=["org_pod"]
)