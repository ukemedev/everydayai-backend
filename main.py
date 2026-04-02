from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import auth_routes, agent_routes, knowledge_routes, chat_routes, whatsapp
from database import engine
from dotenv import load_dotenv
from sqlalchemy import text
import os

load_dotenv()

app = FastAPI(
    title="EverydayAI Backend",
    description="Backend API for EverydayAI",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_routes.router)
app.include_router(agent_routes.router)
app.include_router(knowledge_routes.router)
app.include_router(chat_routes.router)
app.include_router(whatsapp.router)


@app.on_event("startup")
def run_safe_migrations():
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR DEFAULT 'free'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS message_count_reset_at TIMESTAMP",
        """
        CREATE TABLE IF NOT EXISTS whatsapp_deployments (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER NOT NULL REFERENCES agents(id),
            phone_number_id VARCHAR NOT NULL,
            phone_number VARCHAR NOT NULL,
            whatsapp_token VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()


@app.get("/")
def root():
    return {"message": "EverydayAI Backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/widget.js")
def serve_widget():
    from fastapi.responses import FileResponse
    return FileResponse("static/widget.js", media_type="application/javascript")
