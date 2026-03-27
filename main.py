from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import auth_routes, agent_routes, knowledge_routes, chat_routes
from dotenv import load_dotenv
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