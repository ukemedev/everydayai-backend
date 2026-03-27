from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
import auth
from openai import OpenAI
import secrets

router = APIRouter(prefix="/agents", tags=["agents"])

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = "gpt-4o-mini"

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None

def get_openai_client(user: models.User):
    if not user.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="No OpenAI API key found. Please add your API key in settings."
        )
    return OpenAI(api_key=user.openai_api_key)

@router.post("/")
def create_agent(
    request: AgentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    client = get_openai_client(current_user)

    assistant = client.beta.assistants.create(
        name=request.name,
        instructions=request.system_prompt or "You are a helpful assistant.",
        model=request.model,
        tools=[{"type": "file_search"}]
    )

    vector_store = client.beta.vector_stores.create(
        name=f"{request.name} Knowledge Base"
    )

    client.beta.assistants.update(
        assistant.id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
    )

    agent = models.Agent(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        model=request.model,
        openai_assistant_id=assistant.id,
        openai_vector_store_id=vector_store.id,
        owner_id=current_user.id
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent

@router.get("/")
def list_agents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    agents = db.query(models.Agent).filter(
        models.Agent.owner_id == current_user.id
    ).all()
    return agents

@router.get("/{agent_id}")
def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == agent_id,
        models.Agent.owner_id == current_user.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/{agent_id}")
def update_agent(
    agent_id: int,
    request: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == agent_id,
        models.Agent.owner_id == current_user.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if request.name:
        agent.name = request.name
    if request.description:
        agent.description = request.description
    if request.system_prompt:
        agent.system_prompt = request.system_prompt
    if request.model:
        agent.model = request.model

    db.commit()
    db.refresh(agent)
    return agent

@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == agent_id,
        models.Agent.owner_id == current_user.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    client = get_openai_client(current_user)

    if agent.openai_assistant_id:
        client.beta.assistants.delete(agent.openai_assistant_id)

    if agent.openai_vector_store_id:
        client.beta.vector_stores.delete(agent.openai_vector_store_id)

    db.delete(agent)
    db.commit()
    return {"message": "Agent deleted successfully"}

@router.post("/{agent_id}/publish")
def publish_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == agent_id,
        models.Agent.owner_id == current_user.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_published = True
    agent.widget_token = secrets.token_urlsafe(32)
    db.commit()
    db.refresh(agent)
    return agent