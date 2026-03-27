from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
import auth
from openai import OpenAI
import time

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

def get_openai_client(user: models.User):
    if not user.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="No OpenAI API key found. Please add your API key in settings."
        )
    return OpenAI(api_key=user.openai_api_key)

def run_chat(client, assistant_id, message, thread_id=None):
    if thread_id:
        thread = client.beta.threads.retrieve(thread_id)
    else:
        thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=message
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    while run.status in ["queued", "in_progress"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

    if run.status == "failed":
        raise HTTPException(status_code=500, detail="Assistant run failed")

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    reply = messages.data[0].content[0].text.value

    return {"reply": reply, "thread_id": thread.id}

@router.post("/agents/{agent_id}/chat")
def studio_chat(
    agent_id: int,
    request: ChatRequest,
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

    result = run_chat(
        client,
        agent.openai_assistant_id,
        request.message,
        request.thread_id
    )

    conversation = db.query(models.Conversation).filter(
        models.Conversation.openai_thread_id == result["thread_id"]
    ).first()

    if not conversation:
        conversation = models.Conversation(
            agent_id=agent.id,
            openai_thread_id=result["thread_id"]
        )
        db.add(conversation)
        db.commit()

    return result

@router.post("/widget/{widget_token}/chat")
def widget_chat(
    widget_token: str,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter(
        models.Agent.widget_token == widget_token,
        models.Agent.is_published == True
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    owner = db.query(models.User).filter(
        models.User.id == agent.owner_id
    ).first()

    client = get_openai_client(owner)

    result = run_chat(
        client,
        agent.openai_assistant_id,
        request.message,
        request.thread_id
    )

    conversation = db.query(models.Conversation).filter(
        models.Conversation.openai_thread_id == result["thread_id"]
    ).first()

    if not conversation:
        conversation = models.Conversation(
            agent_id=agent.id,
            openai_thread_id=result["thread_id"]
        )
        db.add(conversation)
        db.commit()

    return result