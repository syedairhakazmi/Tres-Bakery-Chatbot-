"""
Tres Bakery Chatbot - Stress Test & Latency Benchmark
======================================================
Tests:
  1. Sequential latency benchmark  - measures avg/min/max response time
  2. Concurrent user stress test   - N users chatting simultaneously
  3. Session lifecycle stress test - rapid create/reset/end cycles
  4. WebSocket streaming test      - TTFT and total latency via WS

Run:
    pip install requests websocket-client --break-system-packages
    python stress_test.py

Requirements:
    - Backend running at http://localhost:8000
    - Ollama running with qwen3 model loaded
"""

import time
import json
import threading
import statistics
import requests
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8000"
WS_URL  = "ws://localhost:8000/ws/chat"

# ── Colour helpers ───────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg): print(f"  {RED}✗{RESET} {msg}")
def info(msg): print(f"  {CYAN}→{RESET} {msg}")

# ── Helpers ──────────────────────────────────────────────────────────────────
def check_health():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        return data.get("status") == "ok" and data.get("ollama") is True
    except Exception:
        return False

def new_session():
    r = requests.post(f"{BASE_URL}/session/new", timeout=10)
    return r.json()["session_id"]

def chat(session_id, message):
    """Non-streaming REST chat. Returns (response_text, latency_seconds)."""
    start = time.time()
    r = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": session_id, "message": message},
        timeout=120
    )
    elapsed = time.time() - start
    data = r.json()
    return data.get("response", ""), elapsed

# ── Test 1: Health Check ─────────────────────────────────────────────────────
def test_health():
    print(f"\n{BOLD}[1] Health Check{RESET}")
    healthy = check_health()
    if healthy:
        ok("Backend and Ollama are reachable")
    else:
        fail("Backend or Ollama not reachable. Make sure both are running.")
        sys.exit(1)

# ── Test 2: Sequential Latency Benchmark ─────────────────────────────────────
BENCHMARK_MESSAGES = [
    "Hi, what cakes do you have?",
    "How much is the red velvet cake?",
    "Do you have any vegan options?",
    "What time do you open?",
    "Can you deliver to my area?",
]

def test_sequential_latency(n_runs=5):
    print(f"\n{BOLD}[2] Sequential Latency Benchmark  ({n_runs} messages){RESET}")
    latencies = []
    session_id = new_session()

    for i, msg in enumerate(BENCHMARK_MESSAGES[:n_runs]):
        _, latency = chat(session_id, msg)
        latencies.append(latency)
        info(f"Turn {i+1}: {latency:.2f}s  |  \"{msg[:45]}\"")

    avg = statistics.mean(latencies)
    mn  = min(latencies)
    mx  = max(latencies)
    sd  = statistics.stdev(latencies) if len(latencies) > 1 else 0

    print(f"\n  {'Metric':<20} {'Value':>10}")
    print(f"  {'-'*32}")
    print(f"  {'Average latency':<20} {avg:>9.2f}s")
    print(f"  {'Min latency':<20} {mn:>9.2f}s")
    print(f"  {'Max latency':<20} {mx:>9.2f}s")
    print(f"  {'Std deviation':<20} {sd:>9.2f}s")

    if avg < 5:
        ok(f"Average latency {avg:.2f}s is within acceptable range (<5s)")
    else:
        fail(f"Average latency {avg:.2f}s exceeds 5s threshold")

    return latencies

# ── Test 3: Concurrent User Stress Test ──────────────────────────────────────
def _single_user_chat(user_id, messages):
    """Simulate one user chatting through a list of messages."""
    results = []
    try:
        session_id = new_session()
        for msg in messages:
            _, latency = chat(session_id, msg)
            results.append({"user": user_id, "latency": latency, "ok": True})
    except Exception as e:
        results.append({"user": user_id, "latency": None, "ok": False, "error": str(e)})
    return results

def test_concurrent_users(n_users=5):
    print(f"\n{BOLD}[3] Concurrent User Stress Test  ({n_users} simultaneous users){RESET}")

    user_messages = [
        ["What's on the menu?", "I'd like a chocolate cake"],
        ["Do you have croissants?", "How much is a latte?"],
        ["Can I order a custom cake?", "What's the delivery fee?"],
        ["Do you have gluten-free options?", "What are your hours?"],
        ["I want 2 almond croissants", "Nothing else, thanks!"],
    ]

    all_results = []
    start_all = time.time()

    with ThreadPoolExecutor(max_workers=n_users) as executor:
        futures = {
            executor.submit(_single_user_chat, i, user_messages[i % len(user_messages)]): i
            for i in range(n_users)
        }
        for future in as_completed(futures):
            results = future.result()
            all_results.extend(results)

    total_time = time.time() - start_all
    successful = [r for r in all_results if r["ok"]]
    failed_req = [r for r in all_results if not r["ok"]]
    latencies  = [r["latency"] for r in successful if r["latency"]]

    print(f"\n  Total wall-clock time : {total_time:.2f}s")
    print(f"  Total requests        : {len(all_results)}")
    print(f"  Successful            : {len(successful)}")
    print(f"  Failed                : {len(failed_req)}")
    if latencies:
        print(f"  Avg latency (all)     : {statistics.mean(latencies):.2f}s")
        print(f"  Max latency (all)     : {max(latencies):.2f}s")

    if len(failed_req) == 0:
        ok(f"All {n_users} concurrent users handled successfully")
    else:
        fail(f"{len(failed_req)} request(s) failed under concurrent load")
        for r in failed_req:
            info(f"  User {r['user']} error: {r.get('error', 'unknown')}")

    return all_results

# ── Test 4: Session Lifecycle Stress Test ─────────────────────────────────────
def test_session_lifecycle(n=20):
    print(f"\n{BOLD}[4] Session Lifecycle Stress Test  ({n} rapid cycles){RESET}")
    errors = 0
    start = time.time()

    for i in range(n):
        try:
            sid = new_session()

            # Reset
            r = requests.post(f"{BASE_URL}/session/reset",
                              json={"session_id": sid}, timeout=5)
            assert r.status_code == 200

            # Get info
            r = requests.get(f"{BASE_URL}/session/info/{sid}", timeout=5)
            assert r.status_code == 200
            data = r.json()
            assert data["turn_count"] == 0

            # End
            r = requests.post(f"{BASE_URL}/session/end",
                              json={"session_id": sid}, timeout=5)
            assert r.status_code == 200

        except Exception as e:
            errors += 1
            info(f"Cycle {i+1} error: {e}")

    elapsed = time.time() - start
    throughput = n / elapsed

    print(f"\n  Cycles completed : {n}")
    print(f"  Errors           : {errors}")
    print(f"  Total time       : {elapsed:.2f}s")
    print(f"  Throughput       : {throughput:.1f} cycles/sec")

    if errors == 0:
        ok(f"All {n} session lifecycle cycles completed without error")
    else:
        fail(f"{errors} session lifecycle cycle(s) failed")

# ── Test 5: WebSocket Streaming Test ─────────────────────────────────────────
def test_websocket_streaming():
    print(f"\n{BOLD}[5] WebSocket Streaming Test{RESET}")
    try:
        import websocket  # websocket-client
    except ImportError:
        info("websocket-client not installed. Skipping WS test.")
        info("Install with: pip install websocket-client --break-system-packages")
        return

    tokens_received = []
    ttft = None
    total_latency = None
    errors = []

    def on_message(ws, message):
        nonlocal ttft, total_latency
        try:
            data = json.loads(message)
            if "token" in data:
                if ttft is None:
                    ttft = time.time() - start_time
                tokens_received.append(data["token"])
            elif data.get("done"):
                total_latency = data.get("latency")
                ws.close()
        except Exception as e:
            errors.append(str(e))

    def on_error(ws, error):
        errors.append(str(error))

    def on_open(ws):
        sid = ""
        try:
            r = requests.post(f"{BASE_URL}/session/new", timeout=5)
            sid = r.json()["session_id"]
        except Exception:
            pass
        ws.send(json.dumps({
            "session_id": sid,
            "message": "What pastries do you have today?"
        }))

    start_time = time.time()
    ws_app = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error
    )

    thread = threading.Thread(target=ws_app.run_forever)
    thread.daemon = True
    thread.start()
    thread.join(timeout=60)

    if errors:
        fail(f"WebSocket errors: {errors}")
    elif tokens_received:
        full_response = "".join(tokens_received)
        ok(f"Streaming received {len(tokens_received)} tokens")
        ok(f"Time to first token : {ttft:.3f}s" if ttft else "TTFT not measured")
        ok(f"Total latency       : {total_latency:.3f}s" if total_latency else "Total latency not reported")
        info(f"Response preview    : {full_response[:80]}...")
    else:
        fail("No tokens received from WebSocket")

# ── Test 6: Policy Enforcement Verification ──────────────────────────────────
POLICY_TESTS = [
    ("I want to complain about food poisoning",  "escalation",   ["555", "tresbakery.com", "sorry", "empathy", "staff"]),
    ("What's the weather like today?",           "out-of-scope", ["bakery", "sorry", "help", "tres"]),
    ("Can I get a brownie?",                     "off-menu",     ["don't", "sorry", "we offer", "we have"]),
    ("That's all, bye!",                         "end",          ["thank", "goodbye", "visit", "day"]),
]

def test_policy_enforcement():
    print(f"\n{BOLD}[6] Policy Enforcement Smoke Test{RESET}")
    session_id = new_session()
    passed = 0

    for message, policy_type, expected_keywords in POLICY_TESTS:
        response, latency = chat(session_id, message)
        response_lower = response.lower()
        hit = any(kw.lower() in response_lower for kw in expected_keywords)

        if hit:
            ok(f"{policy_type:<15} | response contains expected content  ({latency:.2f}s)")
            passed += 1
        else:
            fail(f"{policy_type:<15} | expected one of {expected_keywords[:2]}")
            info(f"  Got: {response[:100]}")

        # New session after end-of-conversation test
        if policy_type == "end":
            session_id = new_session()

    print(f"\n  {passed}/{len(POLICY_TESTS)} policy checks passed")

# ── Summary Report ────────────────────────────────────────────────────────────
def print_summary(latency_results, concurrent_results):
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  STRESS TEST SUMMARY REPORT{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")

    if latency_results:
        avg = statistics.mean(latency_results)
        print(f"\n  Sequential Benchmark:")
        print(f"    Avg response time : {avg:.2f}s")
        print(f"    Min               : {min(latency_results):.2f}s")
        print(f"    Max               : {max(latency_results):.2f}s")

    if concurrent_results:
        ok_results = [r for r in concurrent_results if r["ok"] and r["latency"]]
        if ok_results:
            lats = [r["latency"] for r in ok_results]
            print(f"\n  Concurrent Load:")
            print(f"    Success rate      : {len(ok_results)}/{len(concurrent_results)}")
            print(f"    Avg latency       : {statistics.mean(lats):.2f}s")
            print(f"    Max latency       : {max(lats):.2f}s")

    print(f"\n  Model     : qwen3 (via Ollama)")
    print(f"  Backend   : FastAPI + Uvicorn")
    print(f"  Timestamp : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{BOLD}{'='*55}{RESET}\n")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{BOLD}{CYAN}Tres Bakery Chatbot - Stress Test & Benchmark Suite{RESET}")
    print("=" * 55)

    test_health()

    lat_results  = test_sequential_latency(n_runs=5)
    conc_results = test_concurrent_users(n_users=5)
    test_session_lifecycle(n=20)
    test_websocket_streaming()
    test_policy_enforcement()

    print_summary(lat_results, conc_results)
