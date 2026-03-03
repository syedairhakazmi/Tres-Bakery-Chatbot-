"""
Tests: memory, compression, signal/noise, session lifecycle, policy, latency logging
Run: python test_system.py
No LLM needed for these tests.
"""

import time
import conversation_manager as cm
from memory import is_high_signal, is_noise, extract_facts, compress_history

passed = 0
failed = 0

def test (name, condition):
    global passed, failed
    if condition:
        print ("  PASS:", name)
        passed += 1
    else:
        print ("  FAIL:", name)
        failed += 1

print ()
print ("Tres Bakery Chatbot - System Test Suite")
print ("=" * 55)

# Test 1: Session Start 
print ()
print (" [1] Conversation Start")

sid = cm.create_session ()
test ("Session is created with unique ID", sid is not None and len (sid) > 10)

session = cm.get_session (sid)
test ("Session starts with empty history", session ["history"] == [])
test ("Session starts with turn count 0", session ["turn_count"] == 0)
test ("Session starts as not ended", session ["ended"] is False)

# Test 2: Conversation End 
print ()
print (" [2] Conversation End")

cm.end_session (sid)
session = cm.get_session (sid)
test ("Session is marked as ended", session ["ended"] is True)

policy = cm.check_policy ("bye, thanks!")
test ("End-of-conversation detected from 'bye'", policy ["is_end"] is True)

policy2 = cm.check_policy ("nothing else, goodbye")
test ("End-of-conversation detected from 'nothing else'", policy2 ["is_end"] is True)

policy3 = cm.check_policy ("How much is a croissant?")
test ("Normal message is not marked as end", policy3 ["is_end"] is False)

# Test 3: Short-Term Memory 
print ()
print (" [3] Short-Term Memory")

sid = cm.create_session ()
cm.add_user_message (sid, "I need a vegan birthday cake")
cm.add_assistant_message (sid, "We have a great vegan option!", 1.2)
cm.add_user_message (sid, "Can you deliver it?")
cm.add_assistant_message (sid, "Yes, we deliver within 10km for $5.", 0.9)

session = cm.get_session (sid)
test ("History retains all 4 messages", len (session ["history"]) == 4)
test ("First user message is preserved", "vegan" in session ["history"][0]["content"])
test ("Second user message is preserved", "deliver" in session ["history"][2]["content"])
test ("Turn count is 2", session ["turn_count"] == 2)

# Test 4: Signal Detection 
print ()
print (" [4] Signal-to-Noise Separation")

test ("'birthday cake' is high signal", is_high_signal ("I need a birthday cake"))
test ("'vegan option' is high signal", is_high_signal ("Do you have a vegan option?"))
test ("'nut allergy' is high signal", is_high_signal ("I have a nut allergy"))
test ("'deliver' is high signal", is_high_signal ("Can you deliver?"))
test ("'ok' is noise", is_noise ("ok"))
test ("'thanks' is noise", is_noise ("thanks"))
test ("'great!' is noise", is_noise ("great!"))
test ("Long sentence is not noise", is_noise ("I was wondering if you could help me with something") is False)

# Test 5: Fact Extraction 
print ()
print (" [5] Structured Memory / Fact Extraction")

history = [
    {"role": "user", "content": "I need a birthday cake"},
    {"role": "assistant", "content": "Sure, what kind?"},
    {"role": "user", "content": "I am vegan so no dairy please"},
    {"role": "assistant", "content": "We have vegan options!"},
    {"role": "user", "content": "Can you deliver to my address?"},
]

facts = extract_facts (history)
test ("Birthday occasion extracted", "birthday" in facts)
test ("Vegan dietary need extracted", "vegan" in facts)
test ("Delivery interest extracted", "delivery" in facts)
test ("Facts returned as string", isinstance (facts, str))

# Test 6: Context Compression 
print ()
print (" [6] Context Compression")

long_history = []
for i in range (15):
    long_history.append ({"role": "user", "content": "ok" if i % 3 == 0 else "I want a custom birthday cake"})
    long_history.append ({"role": "assistant", "content": "Sure, let me help with that."})

structured_mem, compressed = compress_history (long_history)
test ("Compression reduces history length", len (compressed) < len (long_history))
test ("Structured memory is extracted", len (structured_mem) > 0)
test ("Birthday fact is in structured memory", "birthday" in structured_mem)

# Test 7: Policy Checks 
print ()
print (" [7] Policy Enforcement")

policy = cm.check_policy ("I want to complain about my order")
test ("Escalation detected for complaint", policy ["is_escalation"] is True)
test ("Warning included for escalation", policy ["warning"] is not None)

policy2 = cm.check_policy ("What is the weather today?")
test ("Out-of-scope detected for weather", policy2 ["is_out_of_scope"] is True)

policy3 = cm.check_policy ("How much is a croissant?")
test ("No flags for normal question", policy3 ["is_escalation"] is False and policy3 ["is_out_of_scope"] is False)

# Test 8: Latency Logging 
print ()
print (" [8] Latency Logging")

sid = cm.create_session ()
cm.add_user_message (sid, "What cakes do you have?")
cm.add_assistant_message (sid, "We have chocolate, vanilla, and red velvet.", 2.3)
cm.add_user_message (sid, "How much is the chocolate one?")
cm.add_assistant_message (sid, "The chocolate cake is $28.", 1.8)

info = cm.get_session_info (sid)
test ("Latency log has 2 entries", len (info ["latency_log"]) == 2)
test ("First latency is logged correctly", info ["latency_log"][0] == 2.3)
test ("Second latency is logged correctly", info ["latency_log"][1] == 1.8)
test ("Average latency is calculated", info ["avg_latency"] == 2.05)

# Test 9: Session Reset 
print ()
print (" [9] Session Reset")

cm.reset_session (sid)
session = cm.get_session (sid)
test ("History cleared after reset", session ["history"] == [])
test ("Turn count reset to 0", session ["turn_count"] == 0)
test ("Ended flag reset to False", session ["ended"] is False)
test ("Latency log cleared", session ["latency_log"] == [])

# Test 10: Multi-Turn Memory Retention 
print ()
print (" [10] Multi-Turn Conversation Flow")

sid = cm.create_session ()

# Turn 1
cm.add_user_message (sid, "Hi, I am looking for a wedding cake")
cm.add_assistant_message (sid, "Wonderful! Wedding cakes start from $150 with 1 week notice.", 2.1)

# Turn 2
cm.add_user_message (sid, "I have a severe nut allergy")
cm.add_assistant_message (sid, "Please speak with our staff directly about allergies.", 1.5)

# Turn 3
cm.add_user_message (sid, "Can you deliver it?")
cm.add_assistant_message (sid, "Yes, within 10km for $5.", 1.3)

# Turn 4 - end
policy = cm.check_policy ("ok thanks bye")
cm.add_user_message (sid, "ok thanks bye")
cm.add_assistant_message (sid, "Thanks for visiting Tres Bakery! Have a great day!", 0.8)

session = cm.get_session (sid)
facts = extract_facts (session ["history"])

test ("All 4 turns stored", session ["turn_count"] == 4)
test ("Wedding occasion remembered", "wedding" in facts)
test ("Allergy flag remembered", "allergy" in facts or "nuts" in facts)
test ("Delivery interest remembered", "delivery" in facts)
test ("End-of-conversation detected", policy ["is_end"] is True)

messages = cm.get_llm_messages (sid)
test ("LLM messages start with system prompt", messages [0]["role"] == "system")
test ("Tres Bakery in system prompt", "Tres Bakery" in messages [0]["content"])

# Summary 
total = passed + failed
print ("\n" + "=" * 55)
print ("Results:", passed, "passed,", failed, "failed out of", total, "tests")
if failed == 0:
    print ("All tests passed!")
else:
    print (str (failed), "test (s) need attention.")