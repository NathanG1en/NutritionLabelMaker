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
# Define the data folder where images are saved
data_dir = Path(__file__).resolve().parent.parent / "data"
data_dir.mkdir(parents=True, exist_ok=True)

# Mount static route so /files/... works
app.mount("/files", StaticFiles(directory=data_dir), name="files")

print(f"[DEBUG] Serving static files from: {data_dir}")

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

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Nutrition Agent API",
        "version": "1.0.0"
    }

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        response = agent.run(request.message, thread_id=request.thread_id)

        image_filename = None
        message_text = response

        # Try parsing structured JSON from the tool
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                image_filename = parsed.get("filename")
                message_text = parsed.get("message", response)
                print(f"[DEBUG] Parsed response: {parsed}")
                print(f"[DEBUG] Extracted image_filename: {image_filename}")

        except json.JSONDecodeError:
            print("OH HELL NAWAWAW JSON was invalid")
            # print(f"[DEBUG] JSON  decode error: {str(e)}")
            print(f"[DEBUG] Offending response: {response}")

        # Build the public URL for the frontend
        image_url = None
        if image_filename:
            image_url = f"http://localhost:8000/files/{image_filename}"
            print(f"[DEBUG] Serving image via URL: {image_url}")

        # ✅ Always include image_path in response if available
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