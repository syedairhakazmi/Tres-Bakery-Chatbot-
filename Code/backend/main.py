import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import conversation_manager as cm
import llm

app = FastAPI (title = "Tres Bakery Chatbot")

app.add_middleware (
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"],
)

class SessionRequest (BaseModel):
    session_id: str

class ChatRequest (BaseModel):
    session_id: str
    message: str

@app.get ("/health")
def health ():
    return {
        "status": "ok",
        "ollama": llm.check_health (),
        "active_sessions": cm.active_session_count ()
    }

@app.post ("/session/new")
def new_session ():
    session_id = cm.create_session ()
    return {"session_id": session_id}

@app.post ("/session/reset")
def reset_session (body: SessionRequest):
    cm.reset_session (body.session_id)
    return {"session_id": body.session_id, "message": "Session reset."}

@app.post ("/session/end")
def end_session (body: SessionRequest):
    cm.end_session (body.session_id)
    return {"session_id": body.session_id, "message": "Session ended."}

@app.get ("/session/info/{session_id}")
def session_info (session_id: str):
    info = cm.get_session_info (session_id)
    if not info:
        return {"error": "Session not found"}
    return info

@app.post ("/chat")
def chat (body: ChatRequest):
    if not cm.get_session (body.session_id):
        body.session_id = cm.create_session ()

    policy = cm.check_policy (body.message)
    cm.add_user_message (body.session_id, body.message)

    # Pass warning into system prompt, not as a fake user message
    messages = cm.get_llm_messages (body.session_id, warning = policy ["warning"])

    full_response = ""
    total_latency = 0

    for token in llm.stream_chat (messages):
        if token.startswith ("__DONE__:"):
            total_latency = float (token.split (":") [1])
        else:
            full_response += token

    cm.add_assistant_message (body.session_id, full_response, total_latency)

    if policy ["is_end"]:
        cm.end_session (body.session_id)

    return {
        "session_id": body.session_id,
        "response": full_response,
        "latency": total_latency,
        "conversation_ended": policy ["is_end"]
    }

@app.websocket ("/ws/chat")
async def websocket_chat (websocket: WebSocket):
    await websocket.accept ()

    try:
        while True:
            raw = await websocket.receive_text ()

            try:
                data = json.loads (raw)
                session_id  = data.get ("session_id", "")
                user_message = data.get ("message", "").strip ()
            except json.JSONDecodeError:
                await websocket.send_text (json.dumps ({"error": "Invalid JSON"}))
                continue

            if not user_message:
                await websocket.send_text (json.dumps ({"error": "Empty message"}))
                continue

            if not cm.get_session (session_id):
                session_id = cm.create_session ()
                await websocket.send_text (json.dumps ({
                    "session_id": session_id,
                    "event": "session_created"
                }))

            policy = cm.check_policy (user_message)

            # Save only the real user message — no fake warning messages
            cm.add_user_message (session_id, user_message)

            # Warning goes into system prompt only
            messages = cm.get_llm_messages (session_id, warning = policy ["warning"])

            full_response = ""
            total_latency = 0
            ttft = 0

            for token in llm.stream_chat (messages):
                if token.startswith ("__DONE__:"):
                    parts = token.split (":")
                    total_latency = float (parts [1])
                    ttft = float (parts [2])
                else:
                    full_response += token
                    await websocket.send_text (json.dumps ({"token": token}))

            cm.add_assistant_message (session_id, full_response, total_latency)

            if policy ["is_end"]:
                cm.end_session (session_id)

            await websocket.send_text (json.dumps ({
                "done": True,
                "latency": total_latency,
                "ttft": ttft,
                "conversation_ended": policy ["is_end"]
            }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text (json.dumps ({"error": str (e)}))
        except Exception:
            pass