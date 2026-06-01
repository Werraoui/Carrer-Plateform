import argparse
import os
import random
import numpy as np
from requests import get
import torch
from torch.utils.data import Dataset, DataLoader, random_split
from torch.optim import AdamW
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    get_linear_schedule_with_warmup,
)
from seqeval.metrics import classification_report, f1_score
from tqdm import tqdm

# Local imports
import sys
sys.path.insert(0, os.path.dirname(__file__))
from data.sample_data import get_dataset
from data.real_jd_examples import REAL_JD_EXAMPLES
from data.skillspan_data import  get_skillspan_dataset
from data.aijobs_skills import get_aijobs_skills
from data.other_jobs import get_data_analyst_dataset
from preprocess import convert_phrase_format
from preprocess import (
    prepare_examples,
    tokenize_and_align_labels,
    LABEL_LIST, LABEL2ID, ID2LABEL, IGNORE_INDEX,
)

# ── Optional: load SkillSpan dataset if available ────────────────────────────
def _load_all_data():
    data = get_dataset()
    skillspan = get_skillspan_dataset()
    DATA_ANALYST_JD_EXAMPLES = get_data_analyst_dataset()
    raw = get_aijobs_skills()          
    raw = convert_phrase_format(raw)   
    aijobs = prepare_examples(raw)
    try:
        
        all_data = data + REAL_JD_EXAMPLES + aijobs + DATA_ANALYST_JD_EXAMPLES + skillspan
        print(f"   Using combined dataset: {len(get_dataset())} manual + {len(REAL_JD_EXAMPLES)} real JD examples + {len(aijobs)} AIJobs skills + {len(DATA_ANALYST_JD_EXAMPLES)} Data Analyst JD examples + {len(skillspan)} SkillSpan examples = {len(all_data)} total")
    except ImportError:
        print(f"   Using manual dataset only: {len(data)} examples")
        
    return all_data


# ── Reproducibility ──────────────────────────────────────────────────────────

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ── Dataset wrapper ──────────────────────────────────────────────────────────

class NERDataset(Dataset):
    """Wraps tokenized examples for PyTorch DataLoader."""

    def __init__(self, tokenized: dict):
        self.input_ids      = torch.tensor(tokenized["input_ids"],      dtype=torch.long)
        self.attention_mask = torch.tensor(tokenized["attention_mask"],  dtype=torch.long)
        self.labels         = torch.tensor(tokenized["labels"],          dtype=torch.long)

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, idx):
        return {
            "input_ids":      self.input_ids[idx],
            "attention_mask": self.attention_mask[idx],
            "labels":         self.labels[idx],
        }


# ── Metric computation ───────────────────────────────────────────────────────

def compute_metrics(predictions, labels):
    """
    Convert raw logits + label IDs → seqeval-compatible string lists,
    then compute precision / recall / F1.
    """
    # predictions: (batch, seq_len, num_labels)  →  argmax
    preds = np.argmax(predictions, axis=2)

    true_labels, true_preds = [], []
    for pred_seq, label_seq in zip(preds, labels):
        row_labels, row_preds = [], []
        for p, l in zip(pred_seq, label_seq):
            if l != IGNORE_INDEX:          # skip padding / special tokens
                row_labels.append(ID2LABEL[l])
                row_preds.append(ID2LABEL[p])
        true_labels.append(row_labels)
        true_preds.append(row_preds)

    report = classification_report(true_labels, true_preds, zero_division=0)
    f1     = f1_score(true_labels, true_preds, zero_division=0)
    return {"f1": f1, "report": report}


# ── Training loop ────────────────────────────────────────────────────────────

def train(args):
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n{'='*60}")
    print(f"  Device   : {device}")
    print(f"  Model    : {args.model_name}")
    print(f"  Epochs   : {args.epochs}")
    print(f"  Batch    : {args.batch_size}")
    print(f"{'='*60}\n")

    # ── 1. Load & preprocess data ─────────────────────────────────────────
    print("▶  Loading data ...")
    raw      = _load_all_data()
    prepared = prepare_examples(raw)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    tokenized = tokenize_and_align_labels(prepared, tokenizer, max_length=args.max_length)

    dataset = NERDataset(tokenized)

    # 80 / 20 train-validation split
    val_size   = max(1, int(0.2 * len(dataset)))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False)

    print(f"   Train samples : {train_size}")
    print(f"   Val   samples : {val_size}\n")

    # ── 2. Load model ─────────────────────────────────────────────────────
    print("▶  Loading model ...")
    model = AutoModelForTokenClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABEL_LIST),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,   # handles classifier head resize
    )
    model.to(device)

    # ── 3. Optimizer & scheduler ──────────────────────────────────────────
    optimizer = AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * args.epochs
    scheduler   = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps,
    )

    # ── 4. Epoch loop ─────────────────────────────────────────────────────
    best_f1 = 0.0

    for epoch in range(1, args.epochs + 1):
        # — Training —
        model.train()
        total_loss = 0.0
        progress   = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs} [train]")

        for batch in progress:
            input_ids      = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels         = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss
            total_loss += loss.item()

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            progress.set_postfix({"loss": f"{loss.item():.4f}"})

        avg_loss = total_loss / len(train_loader)

        # — Validation —
        model.eval()
        all_logits, all_labels = [], []

        with torch.no_grad():
            for batch in val_loader:
                input_ids      = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels         = batch["labels"].to(device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                all_logits.append(outputs.logits.cpu().numpy())
                all_labels.append(labels.cpu().numpy())

        all_logits = np.concatenate(all_logits, axis=0)
        all_labels = np.concatenate(all_labels, axis=0)
        metrics    = compute_metrics(all_logits, all_labels)

        print(f"\nEpoch {epoch} | avg_loss: {avg_loss:.4f} | val_f1: {metrics['f1']:.4f}")
        print(metrics["report"])

        # — Save best model —
        if metrics["f1"] >= best_f1:
            best_f1 = metrics["f1"]
            os.makedirs(args.output_dir, exist_ok=True)
            model.save_pretrained(args.output_dir)
            tokenizer.save_pretrained(args.output_dir)
            print(f"   ✅  New best model saved to '{args.output_dir}' (F1={best_f1:.4f})")

    print(f"\n{'='*60}")
    print(f"  Training complete.  Best val F1 : {best_f1:.4f}")
    print(f"  Model saved to     : {args.output_dir}")
    print(f"{'='*60}\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Fine-tune BERT for Skill NER")
    p.add_argument("--model_name",    default="bert-base-uncased",
                   help="HuggingFace model ID (e.g. jjzha/jobbert-base-cased)")
    p.add_argument("--output_dir",    default="./saved_model")
    p.add_argument("--epochs",        type=int,   default=10)
    p.add_argument("--batch_size",    type=int,   default=4)
    p.add_argument("--max_length",    type=int,   default=128)
    p.add_argument("--learning_rate", type=float, default=2e-5)
    p.add_argument("--seed",          type=int,   default=42)
    return p.parse_args()


if __name__ == "__main__":
    train(parse_args())