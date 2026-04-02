from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    openai_api_key = Column(String, nullable=True)
    plan = Column(String, default="free")
    message_count = Column(Integer, default=0)
    message_count_reset_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    agents = relationship("Agent", back_populates="owner")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    system_prompt = Column(Text, nullable=True)
    model = Column(String, default="gpt-4o-mini")
    openai_assistant_id = Column(String, nullable=True)
    openai_vector_store_id = Column(String, nullable=True)
    is_published = Column(Boolean, default=False)
    widget_token = Column(String, unique=True, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="agents")
    knowledge_files = relationship("KnowledgeFile", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")


class KnowledgeFile(Base):
    __tablename__ = "knowledge_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    openai_file_id = Column(String, nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="knowledge_files")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    openai_thread_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="conversations")


class WhatsappDeployment(Base):
    __tablename__ = "whatsapp_deployments"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    phone_number_id = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    whatsapp_token = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent")
