import re
from typing import List, Tuple, Dict
from transformers import AutoTokenizer

# ── Label map ────────────────────────────────────────────────────────────────
LABEL_LIST = [
    "O",
    "B-TECH", "I-TECH",
    "B-SOFT", "I-SOFT",
    "B-TOOL", "I-TOOL",
]
LABEL2ID = {lbl: i for i, lbl in enumerate(LABEL_LIST)}
ID2LABEL = {i: lbl for lbl, i in LABEL2ID.items()}

IGNORE_INDEX = -100   # PyTorch CrossEntropy ignores this index



# ── Sample data (text + phrase-level annotations) ───────────────────────────

def convert_phrase_format(raw_examples):
    """
    Converts phrase-based annotations to char-offset format.
    Handles both tuple format and dict format automatically.

    Tuple format (old sample_data.py):
      ("We need Python and SQL.", [("Python", "TECH"), ("SQL", "TECH")])

    Dict format (new style):
      {"text": "We need Python and SQL.", 
       "entities": [("Python", "TECH"), ("SQL", "TECH")]}
    """
    converted = []
    for ex in raw_examples:

        # ── detect format ──────────────────────────────────────────────────
        if isinstance(ex, tuple):
            text, pairs = ex[0], ex[1]
        else:
            text, pairs = ex["text"], ex["entities"]

        # ── resolve phrases → char offsets ─────────────────────────────────
        resolved = []
        for item in pairs:
            # already offset format: (15, 27, "TECH")
            if isinstance(item[0], int):
                resolved.append(item)
            # phrase format: ("Python", "TECH")
            else:
                phrase, label = item[0], item[1]
                m = re.search(re.escape(phrase), text, re.IGNORECASE)
                if m:
                    resolved.append((m.start(), m.end(), label))
                else:
                    print(f"⚠️  Warning: '{phrase}' not found in: {text[:60]}")

        converted.append({"text": text, "entities": resolved})
    return converted

# ── Step 1 : char-span  →  word-level BIO tags ───────────────────────────────

def _tokenize_with_offsets(text: str) -> Tuple[List[str], List[Tuple[int,int]]]:
    """
    Split text into word tokens and record (start, end) char offsets.
    Handles punctuation naively — good enough for job descriptions.
    """
    tokens, offsets = [], []
    for match in re.finditer(r"\S+", text):
        tokens.append(match.group())
        offsets.append((match.start(), match.end()))
    return tokens, offsets


def _assign_bio_labels(
    tokens: List[str],
    offsets: List[Tuple[int,int]],
    entities: List[Tuple[int,int,str]],   # (start, end, type)
) -> List[str]:
    """Map character-level entity spans onto word tokens using BIO scheme."""
    labels = ["O"] * len(tokens)

    for ent_start, ent_end, ent_type in entities:
        first = True
        for idx, (tok_start, tok_end) in enumerate(offsets):
            # Token overlaps with entity span
            if tok_start >= ent_start and tok_end <= ent_end:
                prefix = "B" if first else "I"
                labels[idx] = f"{prefix}-{ent_type}"
                first = False

    return labels


# ── Step 2 : word BIO  →  sub-token BIO  ────────────────────────────────────

def tokenize_and_align_labels(
    examples: List[Dict],
    tokenizer: AutoTokenizer,
    max_length: int = 128,
) -> Dict:
    """
    Takes a list of dicts with keys 'tokens' and 'ner_tags' (word-level),
    returns a HuggingFace-ready dict with input_ids, attention_mask, labels.

    The convention used:
      • first sub-token of each word  →  keeps the word's label
      • subsequent sub-tokens         →  IGNORE_INDEX  (-100)
      • special tokens [CLS]/[SEP]    →  IGNORE_INDEX
    """
    tokenized = tokenizer(
        [ex["tokens"] for ex in examples],
        is_split_into_words=True,
        truncation=True,
        padding="max_length",
        max_length=max_length,
    )

    all_labels = []
    for batch_idx, ex in enumerate(examples):
        word_ids  = tokenized.word_ids(batch_index=batch_idx)
        word_lbls = ex["ner_tags"]

        previous_word_id = None
        label_ids = []
        for word_id in word_ids:
            if word_id is None:
                # [CLS] or [SEP]
                label_ids.append(IGNORE_INDEX)
            elif word_id != previous_word_id:
                # First sub-token of a new word
                label_ids.append(LABEL2ID[word_lbls[word_id]])
            else:
                # Continuation sub-token
                label_ids.append(IGNORE_INDEX)
            previous_word_id = word_id

        all_labels.append(label_ids)

    tokenized["labels"] = all_labels
    return tokenized


# ── Step 3 : High-level conversion ──────────────────────────────────────────

def prepare_examples(raw_examples: List[Dict]) -> List[Dict]:
    """
    Convert raw (text, entities) dicts  →  word-token dicts ready for
    tokenize_and_align_labels().

    Input format:
      {"text": "...", "entities": [(start, end, type), ...]}

    Output format:
      {"tokens": ["...", ...], "ner_tags": ["O", "B-TECH", ...]}
    """
    prepared = []
    for ex in raw_examples:
        tokens, offsets = _tokenize_with_offsets(ex["text"])
        labels = _assign_bio_labels(tokens, offsets, ex["entities"])
        prepared.append({"tokens": tokens, "ner_tags": labels})
    return prepared


# ── Utility: pretty-print token/label pairs ──────────────────────────────────

def display_example(example: Dict, max_tokens: int = 30) -> None:
    """Print a word-token example in a readable table."""
    tokens = example["tokens"][:max_tokens]
    labels = example["ner_tags"][:max_tokens]
    header = f"{'TOKEN':<20} {'LABEL'}"
    print(header)
    print("-" * len(header))
    for tok, lbl in zip(tokens, labels):
        mark = "  ◀" if lbl != "O" else ""
        print(f"{tok:<20} {lbl}{mark}")


