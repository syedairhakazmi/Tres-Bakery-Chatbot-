"""
Handles:
- Short-term memory (full recent history)
- Structured memory (key facts extracted from conversation)
- Context compression (keep signal, drop noise)
- Signal-to-noise separation
"""

# Maximum number of recent turns to keep in full
MAX_RECENT_TURNS = 6

# Words that signal important customer information (high signal)
HIGH_SIGNAL_KEYWORDS = [
    "allergy", "allergic", "gluten", "vegan", "nut", "dairy",
    "birthday", "wedding", "anniversary", "party",
    "deliver", "delivery", "pickup", "collect",
    "how many", "people", "guests", "serving",
    "custom", "order", "want", "need", "looking for",
    "my name is", "i am", "i'm", "call me",
    "date", "when", "time", "today", "tomorrow", "weekend"
]

# Words that signal casual filler (low signal / noise)
LOW_SIGNAL_KEYWORDS = [
    "ok", "okay", "sure", "thanks", "thank you", "great",
    "awesome", "nice", "cool", "got it", "alright",
    "hmm", "um", "uh", "yes", "no", "maybe"
]

def is_high_signal (text):
    text_lower = text.lower ()
    for keyword in HIGH_SIGNAL_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

def is_noise (text):
    text_lower = text.strip ().lower ()
    # Very short messages with only filler words are noise
    if len (text_lower) > 40:
        return False
    for keyword in LOW_SIGNAL_KEYWORDS:
        if text_lower == keyword or text_lower == keyword + "." or text_lower == keyword + "!":
            return True
    return False

def extract_facts (history):
    """
    Extract key facts from conversation history.
    Returns a short structured string summarising what we know.
    """
    facts = []

    for turn in history:
        if turn ["role"] != "user":
            continue

        text = turn ["content"]
        text_lower = text.lower ()

        # Extract occasion mentions
        if "birthday" in text_lower:
            facts.append ("occasion: birthday")
        if "wedding" in text_lower:
            facts.append ("occasion: wedding")
        if "anniversary" in text_lower:
            facts.append ("occasion: anniversary")
        if "party" in text_lower:
            facts.append ("occasion: party")

        # Extract dietary needs
        if "vegan" in text_lower:
            facts.append ("dietary: vegan")
        if "gluten" in text_lower:
            facts.append ("dietary: gluten-free needed")
        if "nut allergy" in text_lower or "allergic to nuts" in text_lower:
            facts.append ("allergy: nuts (critical)")
        if "dairy" in text_lower and "allergy" in text_lower:
            facts.append ("allergy: dairy (critical)")

        # Extract delivery interest
        if "deliver" in text_lower or "delivery" in text_lower:
            facts.append ("interested in: delivery")

        # Extract custom cake interest
        if "custom" in text_lower and "cake" in text_lower:
            facts.append ("interested in: custom cake")

        # Extract wedding cake interest
        if "wedding" in text_lower and "cake" in text_lower:
            facts.append ("interested in: wedding cake")

        # Extract customer name
        if "my name is" in text_lower:
            name_part = text_lower.split ("my name is")[1].strip ()
            name = name_part.split ()[0].capitalize ()
            if name:
                facts.append (f"customer name: {name}")
        elif "i am " in text_lower and len (text) < 50:
            parts = text_lower.split ("i am ")
            if len (parts) > 1:
                name = parts[1].strip ().split ()[0].capitalize ()
                if name and len (name) > 1:
                    facts.append (f"customer name: {name}")
        elif "i'm " in text_lower and len (text) < 50:
            parts = text_lower.split ("i'm ")
            if len (parts) > 1:
                name = parts[1].strip ().split ()[0].capitalize ()
                if name and len (name) > 1:
                    facts.append (f"customer name: {name}")

    # Deduplicate facts (keep last occurrence of customer name)
    seen = []
    for fact in facts:
        if "customer name:" in fact:
            # Remove old name if exists
            seen = [f for f in seen if "customer name:" not in f]
            seen.append (fact)
        elif fact not in seen:
            seen.append (fact)

    if len (seen) == 0:
        return ""

    return ", ".join (seen)

def compress_history (history):
    """
    Separate signal from noise.
    Keep only recent turns + high-signal older turns.
    Returns (structured_memory_string, compressed_recent_history)
    """
    if len (history) == 0:
        return "", []

    # Extract structured facts from full history
    structured_memory = extract_facts (history)

    # If history is short enough, return as-is
    if len (history) <= MAX_RECENT_TURNS * 2:
        return structured_memory, history

    # Split into older history and recent history
    recent_cutoff = MAX_RECENT_TURNS * 2
    older_history = history [ : -recent_cutoff]
    recent_history = history [-recent_cutoff : ]

    # From older history, keep only high-signal user messages
    compressed_older = []
    for turn in older_history:
        if turn ["role"] == "user" and is_high_signal (turn ["content"]) and not is_noise (turn ["content"]):
            compressed_older.append (turn)

    # Combine compressed older with full recent
    final_history = compressed_older + recent_history

    return structured_memory, final_history