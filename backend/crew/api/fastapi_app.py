from fastapi import FastAPI, Form, UploadFile, File
from typing import Optional
from src.main import run

app = FastAPI()

@app.post("/chat")
async def chat(
    user_query: str = Form(...),
    language: str = Form("en"),
    context_data: Optional[str] = Form(None),
    device_data: Optional[str] = Form(None)
):
    # The frontend sends context_data and device_data as JSON strings within FormData
    response_text = run(
        query=user_query,
        language=language,
        device_data=device_data or "",
        context_data=context_data or ""
    )

    # The agent might return a JSON string for charts
    import json
    try:
        # Check if it's a JSON block
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)

        # Try parsing as pure JSON if no markdown blocks
        parsed = json.loads(response_text)
        return parsed
    except Exception:
        # Return as text response
        return {
            "answer": response_text
        }
