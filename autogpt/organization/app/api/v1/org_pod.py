from fastapi import APIRouter

from autogpt.organization.app.schemas.organization_schema import Organization

router = APIRouter()

@router.post("/start")
async def start(organization: Organization):
    print(f"starting organization script here: {organization}")
    return {"message": "Organization script started"}
            
@router.post("/stop")
async def stop():
    return {"message": "Organization script stopped"}

@router.post("/pause")
async def pause():
    return {"message": "Organization script paused"}

@router.post("/resume")
async def resume():
    return {"message": "Organization script resumed"}

