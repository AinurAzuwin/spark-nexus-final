# nlp/full_analysis.py
import string
from collections import Counter
import spacy
from sentence_transformers import SentenceTransformer, util
import boto3
from boto3.dynamodb.conditions import Key
from typing import List, Dict, Any

# -------- CONFIG (no hardcoded AWS keys) ----------
dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
table_msgs = dynamodb.Table("messages")
table_sess = dynamodb.Table("sessions")
table_focus = dynamodb.Table("FocusSummaries")
table_emot = dynamodb.Table("Emotion")

# -------- MODELS (load once) ----------
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    raise RuntimeError("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm") from e

try:
    semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    raise RuntimeError("sentence-transformers model load error. Install 'sentence-transformers'") from e

# -------- HELPERS: DB retrieval ----------
def get_messages_ordered(session_id: str) -> List[Dict[str, Any]]:
    """Query messages table and return items ordered by sort-key (timestamp)."""
    try:
        resp = table_msgs.query(
            KeyConditionExpression=Key('session_id').eq(session_id),
            ScanIndexForward=True  # ascending by timestamp
        )
    except Exception as e:
        # bubble up a clear exception
        raise RuntimeError(f"Error querying messages table: {e}") from e
    return resp.get("Items", [])

def get_session_metadata(session_id: str):
    """Return child_name and child_age from sessions table (fallbacks if missing)."""
    try:
        resp = table_sess.get_item(Key={'session_id': session_id})
        item = resp.get('Item') or {}
    except Exception:
        item = {}
    # field names per your schema
    child_name = item.get("child_name") or item.get("childId") or "Unknown"
    # metadata may be nested
    metadata = item.get("child_metadata") or item.get("metadata") or {}
    # Dynamo returns numbers as strings sometimes; handle that
    age = None
    try:
        # metadata may have nested structure like {"child_age": {"N": "6"}} or direct number
        ca = metadata.get("child_age") if isinstance(metadata, dict) else None
        if isinstance(ca, dict) and "N" in ca:
            age = int(ca["N"])
        elif isinstance(ca, (int, float, str)):
            age = int(ca)
        else:
            age = int(item.get("child_age") or item.get("age") or 6)
    except Exception:
        age = 6
    return child_name, age

def get_focus_summary(session_id: str) -> float:
    """Return focus percent normalized 0..1. If not found, return 0.0"""
    try:
        resp = table_focus.get_item(Key={'session_id': session_id})
        itm = resp.get("Item")
        if not itm:
            return 0.0
        # tolerate different field names
        pct = itm.get("percent_focused") or itm.get("percentFocus") or itm.get("average_focus") or itm.get("focus") or itm.get("percent")
        if pct is None:
            return 0.0
        # If value is like '42.5' or 42.5 interpret accordingly
        try:
            pct = float(pct)
        except Exception:
            # maybe stored as dict {'N': '42.5'}
            if isinstance(pct, dict) and "N" in pct:
                pct = float(pct["N"])
            else:
                pct = 0.0
        # accept either 0..1 or 0..100
        if 0 <= pct <= 1:
            return round(pct, 2)
        else:
            return round(min(max(pct / 100.0, 0.0), 1.0), 2)
    except Exception:
        return 0.0

def get_emotion_profile(session_id: str):
    """
    Query Emotion table and return dominant emotion, consistency (0..1),
    and counts dict + avg confidence if available.
    """
    try:
        resp = table_emot.query(KeyConditionExpression=Key('session_id').eq(session_id), ScanIndexForward=True)
        items = resp.get("Items", [])
    except Exception:
        items = []
    if not items:
        return {"dominant": "Unknown", "consistency": 0.0, "counts": {}, "avg_confidence": 0.0}

    # try common field names for label & confidence
    labels = []
    confs = []
    for it in items:
        label = it.get("predicted_emotion") or it.get("emotion") or it.get("label") or None
        if label:
            labels.append(label)
        c = it.get("confidence") or it.get("score") or it.get("conf") or None
        if c is not None:
            try:
                confs.append(float(c))
            except Exception:
                if isinstance(c, dict) and "N" in c:
                    confs.append(float(c["N"]))
    if not labels:
        return {"dominant": "Unknown", "consistency": 0.0, "counts": {}, "avg_confidence": round(sum(confs)/len(confs),2) if confs else 0.0}
    counts = Counter(labels)
    dominant, cnt = counts.most_common(1)[0]
    consistency = round(cnt / len(labels), 2)
    avg_conf = round(sum(confs)/len(confs), 2) if confs else 0.0
    return {"dominant": dominant, "consistency": consistency, "counts": dict(counts), "avg_confidence": avg_conf}

# -------- NLP metric helpers ----------
def clean_and_tokenize_simple(text: str) -> List[str]:
    text = (text or "").lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = text.replace("\n", " ")
    tokens = [t for t in text.split() if t]
    return tokens

def calculate_ttr_from_tokens(tokens: List[str]):
    if not tokens:
        return 0.0, 0, 0
    total = len(tokens)
    unique = len(set(tokens))
    return round(unique / total, 2), total, unique

def syntactic_metrics_text(text: str):
    doc = nlp(text or "")
    sents = list(doc.sents)
    num_sent = len(sents)
    if num_sent > 0:
        avg_len = round(sum(len(s) for s in sents) / num_sent, 2)
    else:
        avg_len = 0.0
    complete = sum(1 for s in sents if any(tok.dep_ == "nsubj" for tok in s))
    incomplete = num_sent - complete
    return {"num_sentences": num_sent, "avg_sentence_len_words": avg_len, "complete_sentences": complete, "incomplete_sentences": incomplete}

def semantic_similarity_pair(a: str, b: str) -> float:
    """Return cosine similarity between two short texts (0..1)."""
    if not a or not b:
        return 0.0
    try:
        emb_a = semantic_model.encode(a, convert_to_tensor=True)
        emb_b = semantic_model.encode(b, convert_to_tensor=True)
        sim = util.cos_sim(emb_a, emb_b).item()
        # clamp and round
        return round(float(max(min(sim, 1.0), -1.0)), 4)
    except Exception:
        return 0.0

# -------- Main merged runner ----------
def run_full_analysis(session_id: str) -> Dict[str, Any]:
    """
    Returns a dictionary with:
      - session metadata
      - vocabulary/syntactic/conversational metrics
      - per-turn semantic similarity (assistant -> next child reply)
      - emotion & focus summaries
      - simple triage diagnosis list
    """
    # 1) session metadata
    child_name, child_age = get_session_metadata(session_id)
    focus_pct = get_focus_summary(session_id)

    # 2) messages (ordered)
    items = get_messages_ordered(session_id)

    # build ordered lists and per-turn pairing (assistant -> next child)
    kid_msgs = []
    assistant_msgs = []
    # for pairing
    pairs = []
    last_assistant = None

    for it in items:
        role = (it.get("role") or "").lower()
        content = it.get("content") or it.get("text") or ""
        if not content:
            continue
        if role in ("assistant", "ai"):
            assistant_msgs.append(content)
            last_assistant = content
        elif role in ("user", "child"):
            kid_msgs.append(content)
            # pair with previous assistant message (one-to-one match)
            if last_assistant:
                sim = semantic_similarity_pair(last_assistant, content)
                pairs.append({"assistant": last_assistant, "child": content, "similarity": sim})
                last_assistant = None
        else:
            # ignore other roles
            continue

    child_turns = len(kid_msgs)
    assistant_turns = len(assistant_msgs)

    # 3) vocabulary (TTR) computed across all child utterances combined
    all_child_text = " ".join(kid_msgs)
    tokens = clean_and_tokenize_simple(all_child_text)
    ttr_score, total_words, unique_words = calculate_ttr_from_tokens(tokens)

    # 4) syntactic metrics on combined child text
    syntax = syntactic_metrics_text(all_child_text)

    # 5) MLU (Mean Length of Utterance) - average tokens per child message
    mlu = round((total_words / child_turns), 2) if child_turns > 0 else 0.0

    # 6) conversational metrics
    total_turns = child_turns + assistant_turns
    turn_ratio = round(child_turns / total_turns, 2) if total_turns > 0 else 0.0

    # 7) semantic pair summary
    avg_pair_sim = round(sum(p["similarity"] for p in pairs) / len(pairs), 2) if pairs else 0.0

    # 8) emotion summary
    emotion_summary = get_emotion_profile(session_id)

    # 9) DIAGNOSIS (ONLY: Normal, ADHD, Language Delay)
    diagnosis_reasons = []

    # Age-based MLU expectation
    # Simple developmental benchmark
    if child_age <= 3:
        expected_mlu = 3.0
    elif 4 <= child_age <= 6:
        expected_mlu = 4.0
    else:
        expected_mlu = 5.0

    low_mlu = mlu < expected_mlu
    low_focus = focus_pct < 0.5
    high_arousal = emotion_summary["dominant"] in ["Excited", "Stressed", "Angry"]

    # ----------------------------------------
    # RULE SET
    # ----------------------------------------

    # 🔥 ADHD DETECTION
    # High activity, poor focus, but speech is OK or high
    if low_focus and (not low_mlu or high_arousal):
        diagnosis_reasons.append({
            "label": "ADHD",
            "reason": "Low focus with normal/high speech output or high arousal."
        })

    # 🔥 LANGUAGE DELAY
    # Good focus but poor speech
    elif (not low_focus) and low_mlu:
        diagnosis_reasons.append({
            "label": "LANGUAGE_DELAY",
            "reason": "Good focus but low MLU suggests delayed expressive language development."
        })

    # 🔥 MIXED CASE (focus low + speech low)
    # This can resemble both ADHD and language delay — but for your system, you choose language delay as primary.
    elif low_focus and low_mlu:
        diagnosis_reasons.append({
            "label": "LANGUAGE_DELAY",
            "reason": "Both focus and speech low — classified under language delay as primary concern."
        })

    # 🔥 NORMAL
    else:
        diagnosis_reasons.append({
            "label": "NORMAL",
            "reason": "Focus, speech length, and behavior fall within normal range."
        })

    # Final assembled result
    result = {
        "session_id": session_id,
        "child_name": child_name,
        "child_age": child_age,
        "focus_percent": focus_pct,
        "emotion_summary": emotion_summary,
        "vocabulary": {
            "ttr": ttr_score,
            "total_words": total_words,
            "unique_words": unique_words
        },
        "syntax": syntax,
        "mlu": mlu,
        "conversational": {
            "child_turns": child_turns,
            "assistant_turns": assistant_turns,
            "turn_ratio_child_over_total": turn_ratio
        },
        "semantic_pairs": pairs,
        "avg_pair_similarity": avg_pair_sim,
        "diagnosis": diagnosis_reasons
    }

    return result

# If run directly, accept session_id as argument for testing
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        sid = sys.argv[1]
    else:
        sid = "session_35ddb1f00387"  # default for testing
    out = run_full_analysis(sid)
    import json
    print(json.dumps(out, indent=2, ensure_ascii=False))
    # Optionally save to DB
    from database.nlp import save_nlp_result
    try:
        save_nlp_result(sid, out)
        print(f"NLP result saved for session {sid}")
    except Exception as e:
        print(f"Failed to save NLP result: {e}")
