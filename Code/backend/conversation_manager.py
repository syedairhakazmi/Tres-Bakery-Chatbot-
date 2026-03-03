import uuid
import time
from memory import compress_history
from prompts import build_messages

SESSION_TIMEOUT = 1800

ORDER_REQUEST_WORDS = [
    "order", "can i get", "could i get", "give", "sell",
    "buy", "purchase", "want to buy", "i want", "i'd like",
    "can you make", "do you have", "how much", "what's the price",
    "whats the price", "pack", "size", "flavor", "flavour",
    "quantity", "how many", "would you", "should i"
]

ESCALATION_WORDS = [
    "complain", "complaint", "refund", "food poisoning",
    "severe allergy", "manager", "lawsuit", "wrong order"
]

OUT_OF_SCOPE_WORDS = [
    "weather", "politics", "sports", "stock",
    "crypto", "code", "programming", "news"
]

END_OF_CONVERSATION_WORDS = [
    "bye", "goodbye", "see you", "thanks bye",
    "that's all", "thats all", "that will be all", "no thanks", 
    "all good thanks", "nothing else", "i'm done", "im done",
    "thank you very much", "thanks very much"
]

sessions = {}

def create_session ():
    session_id = str (uuid.uuid4 ())
    sessions [session_id] = {
        "history": [],
        "turn_count": 0,
        "started_at": time.time (),
        "last_active": time.time (),
        "ended": False,
        "latency_log": []
    }
    return session_id

def get_session (session_id):
    if session_id not in sessions:
        return None
    session = sessions [session_id]
    if time.time () - session ["last_active"] > SESSION_TIMEOUT:
        delete_session (session_id)
        return None
    return session

def delete_session (session_id):
    if session_id in sessions:
        del sessions [session_id]
        return True
    return False

def reset_session (session_id):
    session = get_session (session_id)
    if session:
        session ["history"] = []
        session ["turn_count"] = 0
        session ["ended"] = False
        session ["latency_log"] = []
        session ["last_active"] = time.time ()

def end_session (session_id):
    session = get_session (session_id)
    if session:
        session ["ended"] = True

def add_user_message (session_id, content):
    session = get_session (session_id)
    if not session:
        return False
    content = content.strip ()
    if len (content) > 800:
        content = content [:800]
    session ["history"].append ({"role": "user", "content": content})
    session ["last_active"] = time.time ()
    return True

def add_assistant_message (session_id, content, latency):
    session = get_session (session_id)
    if not session:
        return False
    session ["history"].append ({"role": "assistant", "content": content})
    session ["turn_count"] += 1
    session ["last_active"] = time.time ()
    session ["latency_log"].append (round (latency, 3))
    return True

def get_llm_messages (session_id, warning = None):
    session = get_session (session_id)
    if not session:
        return None
    structured_memory, compressed_history = compress_history (session ["history"])
    # Warning is passed into the system prompt, NOT as a fake user message
    return build_messages (structured_memory, compressed_history, warning)

def check_policy (user_message):
    msg = user_message.lower ().strip ()

    is_end = False
    for word in END_OF_CONVERSATION_WORDS:
        if word in msg:
            is_end = True
            break

    is_order_request = False
    for word in ORDER_REQUEST_WORDS:
        if word in msg:
            is_order_request = True
            break

    is_escalation = False
    for word in ESCALATION_WORDS:
        if word in msg:
            is_escalation = True
            break

    is_out_of_scope = False
    for word in OUT_OF_SCOPE_WORDS:
        if word in msg:
            is_out_of_scope = True
            break

    warning = None
    if is_escalation:
        warning = "Customer may have a complaint or safety concern. Respond with empathy. Provide: (555) 214-8830 or hello@tresbakery.com"
    elif is_out_of_scope:
        warning = "Off-topic message detected. Politely redirect customer to Tres Bakery topics only."

    return {
        "is_end": is_end,
        "is_order_request": is_order_request,
        "is_escalation": is_escalation,
        "is_out_of_scope": is_out_of_scope,
        "warning": warning
    }

def get_session_info (session_id):
    session = get_session (session_id)
    if not session:
        return None
    avg = 0
    if session ["latency_log"]:
        avg = round (sum (session ["latency_log"]) / len (session ["latency_log"]), 3)
    return {
        "session_id": session_id,
        "turn_count": session ["turn_count"],
        "history_length": len (session ["history"]),
        "ended": session ["ended"],
        "latency_log": session ["latency_log"],
        "avg_latency": avg
    }

def active_session_count ():
    cleanup_expired ()
    return len (sessions)

def cleanup_expired ():
    expired = []
    for sid in sessions:
        if time.time () - sessions [sid]["last_active"] > SESSION_TIMEOUT:
            expired.append (sid)
    for sid in expired:
        del sessions [sid]