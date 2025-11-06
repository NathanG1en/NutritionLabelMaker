"""
FastAPI backend for Nutrition Agent
Run with: uvicorn backend.api.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
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


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the nutrition agent.

    Example:
    ```
    POST /api/chat
    {
        "message": "Find avocado and create a nutrition label",
        "thread_id": "user-123"
    }
    ```
    """
    try:
        response = agent.run(request.message, thread_id=request.thread_id)

        # Extract image path if present - try multiple patterns
        image_path = None
        
        # Pattern 1: "file nutrition_labels/Something.png"
        # Pattern 2: "nutrition_labels/Something.png"
        # Pattern 3: Just "Something.png"
        patterns = [
            r'(?:file\s+)?(?:nutrition_labels[/\\])?([A-Za-z0-9_]+_\d{8}_\d{6}\.png)',
            r'(nutrition_labels[/\\][A-Za-z0-9_]+\.png)',
            r'saved to (?:file )?([^\s]+\.png)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                potential_path = match.group(1)
                # Clean up the path - ensure it's just the filename
                if '/' in potential_path or '\\' in potential_path:
                    image_path = Path(potential_path).name
                else:
                    image_path = potential_path
                break

        return ChatResponse(
            response=response,
            thread_id=request.thread_id,
            image_path=image_path
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


@app.get("/api/images/{filename}")
async def get_image(filename: str):
    """
    Serve generated nutrition label images.

    Example: GET /api/images/Avocado_20250205_143022.png
    """
    # Look in the nutrition_labels directory
    image_path = Path("nutrition_labels") / filename

    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")

    if not image_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
        raise HTTPException(status_code=400, detail="Invalid image format")

    return FileResponse(image_path, media_type="image/png")


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