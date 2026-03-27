from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
import models
import auth
from openai import OpenAI

router = APIRouter(prefix="/agents", tags=["knowledge"])

def get_openai_client(user: models.User):
    if not user.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="No OpenAI API key found. Please add your API key in settings."
        )
    return OpenAI(api_key=user.openai_api_key)

@router.post("/{agent_id}/files")
async def upload_file(
    agent_id: int,
    file: UploadFile = File(...),
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

    file_content = await file.read()

    openai_file = client.files.create(
        file=(file.filename, file_content, file.content_type),
        purpose="assistants"
    )

    client.beta.vector_stores.files.create(
        vector_store_id=agent.openai_vector_store_id,
        file_id=openai_file.id
    )

    knowledge_file = models.KnowledgeFile(
        filename=file.filename,
        openai_file_id=openai_file.id,
        agent_id=agent.id
    )
    db.add(knowledge_file)
    db.commit()
    db.refresh(knowledge_file)
    return knowledge_file

@router.get("/{agent_id}/files")
def list_files(
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

    files = db.query(models.KnowledgeFile).filter(
        models.KnowledgeFile.agent_id == agent_id
    ).all()
    return files

@router.delete("/{agent_id}/files/{file_id}")
def delete_file(
    agent_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    agent = db.query(models.Agent).filter(
        models.Agent.id == agent_id,
        models.Agent.owner_id == current_user.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    knowledge_file = db.query(models.KnowledgeFile).filter(
        models.KnowledgeFile.id == file_id,
        models.KnowledgeFile.agent_id == agent_id
    ).first()
    if not knowledge_file:
        raise HTTPException(status_code=404, detail="File not found")

    client = get_openai_client(current_user)

    if knowledge_file.openai_file_id:
        client.files.delete(knowledge_file.openai_file_id)

    db.delete(knowledge_file)
    db.commit()
    return {"message": "File deleted successfully"}