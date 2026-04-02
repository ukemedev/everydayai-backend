from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
import models
import auth
from openai import OpenAI
import time
import httpx

router = APIRouter(tags=["whatsapp"])


class WhatsappConnectRequest(BaseModel):
    phone_number_id: str
    phone_number: str
    whatsapp_token: str


def get_openai_client(user: models.User):
    if not user.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="No OpenAI API key found. Please add your API key in settings."
        )
    return OpenAI(api_key=user.openai_api_key)


def run_chat(client, assistant_id: str, message: str, thread_id: str = None):
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


@router.get("/webhook/whatsapp", response_class=PlainTextResponse)
def verify_webhook(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    import os
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "everydayai_verify")

    if mode == "subscribe" and token == verify_token:
        return PlainTextResponse(content=challenge, status_code=200)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def receive_whatsapp_message(request: Request, db: Session = Depends(get_db)):
    body = await request.json()

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        phone_number_id = value["metadata"]["phone_number_id"]
        messages_list = value.get("messages")
        if not messages_list:
            return {"status": "no_message"}

        msg = messages_list[0]
        from_number = msg["from"]
        incoming_text = msg.get("text", {}).get("body", "")
    except (KeyError, IndexError):
        return {"status": "ignored"}

    deployment = db.query(models.WhatsappDeployment).filter(
        models.WhatsappDeployment.phone_number_id == phone_number_id
    ).first()

    if not deployment:
        return {"status": "no_deployment"}

    agent = db.query(models.Agent).filter(
        models.Agent.id == deployment.agent_id
    ).first()

    if not agent or not agent.openai_assistant_id:
        return {"status": "no_agent"}

    owner = db.query(models.User).filter(
        models.User.id == agent.owner_id
    ).first()

    if not owner:
        return {"status": "no_owner"}

    client = get_openai_client(owner)

    existing_conversation = db.query(models.Conversation).filter(
        models.Conversation.agent_id == agent.id,
        models.Conversation.openai_thread_id.isnot(None)
    ).order_by(models.Conversation.created_at.desc()).first()

    thread_id = existing_conversation.openai_thread_id if existing_conversation else None

    result = run_chat(client, agent.openai_assistant_id, incoming_text, thread_id)

    if not existing_conversation or existing_conversation.openai_thread_id != result["thread_id"]:
        conversation = models.Conversation(
            agent_id=agent.id,
            openai_thread_id=result["thread_id"]
        )
        db.add(conversation)
        db.commit()

    wa_url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {deployment.whatsapp_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": from_number,
        "type": "text",
        "text": {"body": result["reply"]}
    }

    async with httpx.AsyncClient() as client_http:
        await client_http.post(wa_url, json=payload, headers=headers)

    return {"status": "ok"}


@router.post("/agents/{agent_id}/whatsapp/connect")
def connect_whatsapp(
    agent_id: int,
    request: WhatsappConnectRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == agent_id,
        models.Agent.owner_id == current_user.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    existing = db.query(models.WhatsappDeployment).filter(
        models.WhatsappDeployment.agent_id == agent_id
    ).first()

    if existing:
        existing.phone_number_id = request.phone_number_id
        existing.phone_number = request.phone_number
        existing.whatsapp_token = request.whatsapp_token
        db.commit()
        db.refresh(existing)
        return existing

    deployment = models.WhatsappDeployment(
        agent_id=agent_id,
        phone_number_id=request.phone_number_id,
        phone_number=request.phone_number,
        whatsapp_token=request.whatsapp_token
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment


@router.get("/agents/{agent_id}/whatsapp/status")
def whatsapp_status(
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

    deployment = db.query(models.WhatsappDeployment).filter(
        models.WhatsappDeployment.agent_id == agent_id
    ).first()

    if not deployment:
        return {"connected": False}

    return {
        "connected": True,
        "phone_number": deployment.phone_number,
        "phone_number_id": deployment.phone_number_id,
        "created_at": deployment.created_at
    }


@router.delete("/agents/{agent_id}/whatsapp/disconnect")
def disconnect_whatsapp(
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

    deployment = db.query(models.WhatsappDeployment).filter(
        models.WhatsappDeployment.agent_id == agent_id
    ).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="No WhatsApp connection found")

    db.delete(deployment)
    db.commit()
    return {"message": "WhatsApp connection removed"}
