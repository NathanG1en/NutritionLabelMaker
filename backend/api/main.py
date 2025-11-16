"""
FastAPI backend for Nutrition Agent
Run with: uvicorn backend.api.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import json
import re
from pathlib import Path
from backend.utils.s3_client import get_s3
import uuid
import os

# Import your existing agent
from backend.agents.nutrition_agent import NutritionAgent




# ============================================
# FastAPI Setup
# ============================================

app = FastAPI(
    title="Nutrition Agent API",
    description="AI-powered nutrition label generation API",
    version="1.0.0"
)


# TODO: change this to s3 or supabase or some other image storing service

# Base data directory
base_data_dir = Path(__file__).resolve().parent.parent / "data"
base_data_dir.mkdir(parents=True, exist_ok=True)

# Dedicated labels directory
labels_dir = base_data_dir / "labels"
labels_dir.mkdir(parents=True, exist_ok=True)

# Mount /labels for public access
app.mount("/labels", StaticFiles(directory=str(labels_dir)), name="labels")


# CORS for frontend (React, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your agent
agent = NutritionAgent()


# ============================================
# Request/Response Models
# ============================================

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    image_path: Optional[str] = None


# ============================================
# API Endpoints
# ============================================

# s3 buckets n stuff
s3 = get_s3()

def upload_label_to_s3(user_id: str, filename: str, file_bytes: bytes):
    key = f"{user_id}/labels/{filename}"
    s3.put_object(
        Bucket=os.getenv("AWS_BUCKET_NAME"),
        Key=key,
        Body=file_bytes,
        ContentType="image/png"
    )
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": os.getenv("AWS_BUCKET_NAME"),
            "Key": key
        },
        ExpiresIn=60 * 60 * 24  # 24 hours
    )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Nutrition Agent API",
        "version": "1.0.0"
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        print("\n========== /api/chat ==========")
        print(f"Incoming message: {request.message}")
        print(f"Thread ID: {request.thread_id}")

        response_data = agent.run(request.message, thread_id=request.thread_id)

        print("---------- Raw agent response ----------")
        print(response_data)
        print("---------------------------------------")

        message_text = response_data.get("message", "")
        filename = response_data.get("filename")

        print(">>> response_data keys:", response_data.keys())
        print(">>> filename:", response_data.get("filename"))
        print(">>> has file_bytes:", "file_bytes" in response_data)
        print(">>> file_bytes len:", len(response_data["file_bytes"]) if "file_bytes" in response_data else 0)

        # S3 upload
        if filename and "file_bytes" in response_data:
            image_url = upload_label_to_s3(
                user_id=request.thread_id,
                filename=filename,
                file_bytes=response_data["file_bytes"]
            )
        else:
            image_url = None

        return ChatResponse(
            response=message_text,
            thread_id=request.thread_id,
            image_path=image_url
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream agent responses in real-time using Server-Sent Events.

    Example:
    ```javascript
    const eventSource = new EventSource('/api/chat/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data);
    };
    ```
    """

    async def event_generator():
        try:
            for event in agent.stream(request.message, thread_id=request.thread_id):
                # Convert LangGraph event to JSON
                event_data = {
                    "type": "event",
                    "data": str(event)
                }
                yield f"data: {json.dumps(event_data)}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/history/{thread_id}")
async def get_history(thread_id: str):
    """
    Get conversation history for a specific thread.
    """
    try:
        messages = agent.get_state_history(thread_id)
        history = []

        for msg in messages:
            history.append({
                "type": msg.__class__.__name__,
                "content": getattr(msg, 'content', str(msg))[:500],  # Limit length
                "timestamp": getattr(msg, 'timestamp', None)
            })

        return {
            "thread_id": thread_id,
            "message_count": len(history),
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @app.get("/api/images/{filename}")
# async def get_image(filename: str):
#     """
#     Serve generated nutrition label images.
#
#     Example: GET /api/images/Avocado_20250205_143022.png
#     """
#     # Look in the nutrition_labels directory
#     image_path = Path("nutrition_labels") / filename
#
#     if not image_path.exists():
#         raise HTTPException(status_code=404, detail=f"Image not found: {filename}")
#
#     if not image_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
#         raise HTTPException(status_code=400, detail="Invalid image format")
#
#     return FileResponse(image_path, media_type="image/png")


@app.get("/api/tools")
async def get_tools():
    """
    Get list of available agent tools.
    """
    tools_info = []

    for tool in agent.tools:
        tools_info.append({
            "name": tool.name,
            "description": tool.description,
            "args": str(tool.args) if hasattr(tool, 'args') else None
        })

    return {
        "count": len(tools_info),
        "tools": tools_info
    }


@app.get("/api/health")
async def health_check():
    """
    Detailed health check with agent status.
    """
    try:
        # Test agent initialization
        agent_status = "healthy" if agent else "unavailable"

        return {
            "status": "healthy",
            "agent": agent_status,
            "tools_count": len(agent.tools),
            "api_version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# ============================================
# Run with: uvicorn backend.api.main:app --reload --port 8000
# ============================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )