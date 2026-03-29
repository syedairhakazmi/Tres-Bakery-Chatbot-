# Tres Bakery Chatbot

An AI-powered chatbot for Tres Bakery that helps customers with inquiries about menu items, pricing, delivery, custom orders, and general bakery information. Built with FastAPI (backend) and vanilla JavaScript (frontend), powered by Ollama's local LLM.

## Features

### Core Functionality
- **Real-time Chat**: WebSocket-based streaming responses for smooth conversational experience
- **Smart Memory Management**:
  - Short-term memory for recent conversation context
  - Structured memory extraction for key customer facts (allergies, occasions, delivery needs)
  - Context compression to reduce token usage while retaining important information
- **Policy Enforcement**:
  - Escalation detection for complaints or safety concerns
  - Out-of-scope detection to keep conversations on-topic
  - End-of-conversation detection for graceful chat closures
- **Session Management**: Multi-session support with automatic timeout cleanup
- **Latency Tracking**: Response time logging for performance monitoring

### User Experience
- Clean, bakery-themed UI with warm aesthetics
- Multiple conversation history support
- Real-time typing indicators
- Connection status display
- Conversation ended notifications

## Architecture

```
Web UI (index.html)
      ↕  WebSocket / HTTP
FastAPI Backend (main.py)
      ↕
Conversation Manager (conversation_manager.py)
  ├── Memory & Compression (memory.py)
  └── Prompt Orchestration (prompts.py)
      ↕
Local LLM Engine (llm.py)
      ↕
Ollama → qwen3:1.7b (quantized, CPU inference)
```

### Backend (Python/FastAPI)
```
backend/
├── main.py                    # FastAPI app, WebSocket & REST endpoints
├── conversation_manager.py    # Session lifecycle, policy checks
├── memory.py                  # Signal/noise filtering, fact extraction
├── prompts.py                 # System prompts and message building
├── llm.py                     # Ollama integration for AI responses
├── asr.py                     # Speech-to-text (voice input)
├── tts.py                     # Text-to-speech (voice output)
├── test_system.py             # Unit test suite (no LLM required)
├── stress_test.py             # Latency benchmarks & stress tests
└── requirements.txt           # Python dependencies
```

### Frontend (HTML/CSS/JavaScript)
```
frontend/
└── index.html                 # Single-page chat interface
```

## Voice Interface

This system extends the Tres Bakery chatbot with a real-time voice interaction pipeline while maintaining fully local deployment and CPU-only inference. The voice interface enables natural spoken conversations using locally hosted ASR, LLM, and TTS models connected through a streaming architecture.

The design focuses on low latency, concurrency handling, and stateful conversations while preserving the existing memory management and policy enforcement mechanisms.

### Voice Pipeline Architecture

```
Microphone Input
      ↓
ASR (Speech → Text)
      ↓
Conversation Manager
      ↓
Local LLM (qwen3:1.7b via Ollama)
      ↓
TTS (Text → Speech)
      ↓
Streaming Audio Output
```

### Design Constraints

The voice system follows the same architectural principles as the text chatbot:

- Fully local deployment (no cloud APIs)
- CPU-only inference
- Real-time streaming interaction
- Prompt orchestration (no tools)
- Memory/state-based dialogue management
- No retrieval-based augmentation
- Multi-session support
- Concurrent user handling (up to 4 users)

### Capabilities

- Real-time voice conversation
- Streaming speech-to-text
- Streaming text-to-speech
- Stateful multi-turn dialogue
- Concurrent session handling
- Fully offline operation
- Chat + voice web interface
- Low-latency streaming pipeline

This voice layer integrates directly with the existing conversation manager, allowing both text and voice interactions to share memory, policies, and session state.

## Prerequisites

- **Python 3.8+**
- **Ollama** (for local LLM)
- Modern web browser

## Installation

### 1. Install Ollama

Download and install Ollama from [ollama.ai](https://ollama.ai)

Start Ollama service:
```bash
ollama serve
```

Pull the required model:
```bash
ollama pull qwen3:1.7b
```

### 2. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- `fastapi==0.111.0`
- `uvicorn[standard]==0.30.1`
- `requests==2.31.0`
- `pydantic==2.7.1`
- `websockets==12.0`

## Running the Application

### Start the Backend

```bash
cd backend
uvicorn main:app --reload 
```

The backend will be available at `http://localhost:8000/docs`

### Open the Frontend

Simply open `frontend/index.html` in your web browser, or:

**Windows:**
```powershell
Start-Process "frontend/index.html"
```

**macOS/Linux:**
```bash
open frontend/index.html      # macOS
xdg-open frontend/index.html  # Linux
```

## Testing

### Unit Tests (no LLM required)

```bash
cd backend
python test_system.py
```

Expected output: `46 passed, 0 failed out of 46 tests`

**Coverage:** Session lifecycle, memory management, signal/noise separation, fact extraction, policy enforcement, latency logging, multi-turn conversation flow.

### Stress Tests & Benchmarks

```bash
cd backend
python stress_test.py
```

Requires the backend and Ollama to be running. Runs 6 test suites: sequential latency, concurrent users, session lifecycle cycles, WebSocket streaming, and policy enforcement smoke tests.

## API Endpoints

### REST Endpoints

#### Health Check
```http
GET /health
```

#### Create New Session
```http
POST /session/new
```

#### Reset Session
```http
POST /session/reset
Body: {"session_id": "string"}
```

#### End Session
```http
POST /session/end
Body: {"session_id": "string"}
```

#### Get Session Info
```http
GET /session/info/{session_id}
```

#### Chat (Non-streaming)
```http
POST /chat
Body: {"session_id": "string", "message": "string"}
```

### WebSocket Endpoint

```
WS /ws/chat
```

**Send:**
```json
{"session_id": "optional-uuid", "message": "Can I see the menu?"}
```

**Receive (streaming tokens):**
```json
{"token": "Hello"}
{"token": "! Here's"}
{"done": true, "latency": 8.1, "ttft": 6.97, "conversation_ended": false}
```

## Docker Deployment

```bash
docker compose up -d
```

This starts:
- Ollama service (port 11434) with model auto-pulled
- Backend API (port 8000)
- Frontend server (port 3000)

## Model Selection

**Model:** `qwen3:1.7b` (quantized GGUF via Ollama)

Selected for:
- Small memory footprint suitable for CPU-only inference
- Instruction-following quality sufficient for constrained domain chatbot
- Fast enough for interactive use without a GPU
- No cloud dependency — fully local inference

**Configuration** (`llm.py`):
| Parameter | Value | Reason |
|-----------|-------|--------|
| temperature | 0.3 | Low variance for consistent, policy-compliant responses |
| num_predict | 600 | Caps response length to control latency |
| num_ctx | 4096 | Full context window for multi-turn history |
| stop tokens | `User:`, `Customer:` | Prevents hallucinated turn continuations |

## Performance Benchmarks

Benchmarks measured on a standard laptop CPU running `qwen3:1.7b` via Ollama (no GPU). Results from `stress_test.py` run on 2026-03-03.

### Sequential Latency (5 turns, single user)

| Metric | Value |
|--------|-------|
| Average response time | 19.86s |
| Min response time | 9.22s |
| Max response time | 46.88s |
| Std deviation | 15.34s |

> The first turn (46.88s) is an outlier caused by model warm-up / cold cache. Subsequent turns stabilise between 9–17s.

### WebSocket Streaming

| Metric | Value |
|--------|-------|
| Time to First Token (TTFT) | 6.97s |
| Total streaming latency | 8.10s |
| Tokens received | 61 |

> Streaming significantly improves perceived responsiveness — the user sees the first token at ~7s even though the full response takes ~8s.

### Concurrent Users (5 simultaneous users)

| Metric | Value |
|--------|-------|
| Total wall-clock time | 94.73s |
| Total requests | 10 |
| Successful | 10 (100%) |
| Failed | 0 |
| Avg latency under load | 42.14s |
| Max latency under load | 65.75s |

> Latency increases under concurrency because the single Ollama instance processes requests sequentially. All requests succeeded with no errors.

### Session Lifecycle Throughput

| Metric | Value |
|--------|-------|
| Cycles completed | 20/20 |
| Errors | 0 |
| Total time | 165.18s |
| Throughput | 0.1 cycles/sec |

> Session management (create/reset/end/info) is entirely in-memory and error-free. The throughput figure reflects the full cycle including LLM calls within each cycle.

### Policy Enforcement (Smoke Test)

| Policy Type | Result | Latency |
|-------------|--------|---------|
| Escalation (complaint) | ✓ Pass | 10.01s |
| Out-of-scope redirect | ✓ Pass | 10.44s |
| Off-menu item rejection | ✓ Pass | 10.74s |
| End-of-conversation | ✓ Pass | 5.98s |

All 4/4 policy checks passed.

## Context Memory Management

The memory module (`memory.py`) implements a three-tier strategy:

1. **Structured Memory** — facts extracted from the full conversation history (customer name, occasion, dietary needs, allergies, delivery interest) and injected into the system prompt as a compact summary.
2. **Short-term Memory** — the last 6 full turns (12 messages) are always passed verbatim to preserve recent context.
3. **Compressed Older History** — turns older than the short-term window are filtered: only high-signal user messages (containing keywords like `birthday`, `allergy`, `deliver`, etc.) are retained; filler messages (`ok`, `thanks`, `sure`) are dropped.

This keeps token usage bounded while preserving all information the LLM needs to stay consistent.

## Known Limitations

- **High latency on CPU**: Average response time of ~10–20s on a standard laptop is above ideal for production. A GPU or a smaller model (qwen3:1.7b) would reduce this significantly.
- **Concurrency bottleneck**: Ollama processes one request at a time on CPU. Under concurrent load, all users queue behind each other, causing latency to multiply linearly with user count.
- **In-memory sessions**: Sessions are stored in a Python dict and are lost on backend restart. A production system would use Redis or a database.
- **No order persistence**: Orders are simulated within the conversation only. There is no real database integration.
- **English only**: The system prompt enforces English responses, but the underlying model may occasionally produce non-English output if the user writes in another language.
- **Model warm-up**: The first request after a cold start takes significantly longer (observed: 46.88s) as the model loads into memory.

## Technologies Used

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI + Uvicorn |
| Real-time communication | WebSockets |
| LLM inference | Ollama |
| Language model | qwen3:1.7b (quantized) |
| Frontend | Vanilla HTML/CSS/JavaScript |
| Containerisation | Docker + Docker Compose |
| Testing | Python unittest (custom), stress_test.py |

## Troubleshooting

**Backend won't start** — ensure Python 3.8+ is installed and run `pip install -r requirements.txt`.

**Frontend "Something went wrong"** — ensure Ollama is running (`ollama serve`) and the model is pulled (`ollama list`). Verify backend is up: `curl http://localhost:8000/health`.

**Slow responses** — expected on CPU. The qwen3:1.7b model averages 10–20s per response without a GPU. Check system RAM; the model requires ~1–2GB free.

**Chinese characters in response** — the model occasionally ignores the English-only instruction. This is a known limitation of small quantized models. The system prompt includes explicit instructions to prevent this.
