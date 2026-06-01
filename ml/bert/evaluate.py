import argparse
import json
import os
import sys
import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, AutoModelForTokenClassification
from seqeval.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)

sys.path.insert(0, os.path.dirname(__file__))
from data.sample_data import get_dataset
from preprocess import (
    prepare_examples,
    tokenize_and_align_labels,
    LABEL_LIST, LABEL2ID, ID2LABEL, IGNORE_INDEX,
)
from train import NERDataset


# ── Evaluation helper ────────────────────────────────────────────────────────

def evaluate_model(model, tokenizer, dataset, device, batch_size=4):
    """
    Run full evaluation loop.
    Returns (all_true_labels, all_pred_labels) as seqeval-format lists.
    """
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    model.eval()
    all_logits, all_labels = [], []

    with torch.no_grad():
        for batch in loader:
            ids   = batch["input_ids"].to(device)
            mask  = batch["attention_mask"].to(device)
            lbls  = batch["labels"].to(device)
            out   = model(input_ids=ids, attention_mask=mask)
            all_logits.append(out.logits.cpu().numpy())
            all_labels.append(lbls.cpu().numpy())

    all_logits = np.concatenate(all_logits, axis=0)
    all_labels = np.concatenate(all_labels, axis=0)
    preds      = np.argmax(all_logits, axis=2)

    true_seqs, pred_seqs = [], []
    for pred_row, label_row in zip(preds, all_labels):
        true_seq, pred_seq = [], []
        for p, l in zip(pred_row, label_row):
            if l != IGNORE_INDEX:
                true_seq.append(ID2LABEL[l])
                pred_seq.append(ID2LABEL[p])
        true_seqs.append(true_seq)
        pred_seqs.append(pred_seq)

    return true_seqs, pred_seqs


# ── Error analysis ───────────────────────────────────────────────────────────

def analyse_errors(true_seqs, pred_seqs, prepared_examples):
    """
    Identify false positives and false negatives at the span level.
    """
    false_positives = []   # predicted skill that isn't in ground truth
    false_negatives = []   # ground-truth skill that wasn't predicted

    def extract_spans(seq):
        """Extract (start, end, type) spans from a BIO sequence."""
        spans = []
        start, current_type = None, None
        for i, lbl in enumerate(seq):
            if lbl.startswith("B-"):
                if current_type:
                    spans.append((start, i - 1, current_type))
                start = i
                current_type = lbl[2:]
            elif lbl == "O" and current_type:
                spans.append((start, i - 1, current_type))
                current_type = None
                start = None        
        if current_type:
            spans.append((start, len(seq) - 1, current_type))
        return set(spans)

    for idx, (true_seq, pred_seq, ex) in enumerate(
        zip(true_seqs, pred_seqs, prepared_examples)
    ):
        tokens     = ex["tokens"]
        true_spans = extract_spans(true_seq)
        pred_spans = extract_spans(pred_seq)

        for span in pred_spans - true_spans:
            phrase = " ".join(tokens[span[0]: span[1] + 1])
            false_positives.append({"span": phrase, "predicted": span[2], "example_idx": idx})

        for span in true_spans - pred_spans:
            phrase = " ".join(tokens[span[0]: span[1] + 1])
            false_negatives.append({"span": phrase, "true_label": span[2], "example_idx": idx})

    return false_positives, false_negatives


# ── Main ─────────────────────────────────────────────────────────────────────

def main(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n▶  Loading model from '{args.model_dir}' ...")

    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model     = AutoModelForTokenClassification.from_pretrained(args.model_dir)
    model.to(device)

    # Prepare full dataset (use all 20 examples for eval in this demo)
    raw      = get_dataset()
    prepared = prepare_examples(raw)
    tokenized = tokenize_and_align_labels(prepared, tokenizer)
    dataset   = NERDataset(tokenized)

    print(f"   Evaluating on {len(dataset)} examples ...\n")
    true_seqs, pred_seqs = evaluate_model(model, tokenizer, dataset, device)

    # ── Metrics ───────────────────────────────────────────────────────────
    print("=" * 65)
    print("  CLASSIFICATION REPORT  (entity-level, seqeval)")
    print("=" * 65)
    print(classification_report(true_seqs, pred_seqs, zero_division=0))

    overall_f1  = f1_score(true_seqs, pred_seqs, zero_division=0)
    overall_p   = precision_score(true_seqs, pred_seqs, zero_division=0)
    overall_r   = recall_score(true_seqs, pred_seqs, zero_division=0)

    print(f"  Overall  Precision : {overall_p:.4f}")
    print(f"  Overall  Recall    : {overall_r:.4f}")
    print(f"  Overall  F1        : {overall_f1:.4f}\n")

    # ── Error analysis ────────────────────────────────────────────────────
    fp, fn = analyse_errors(true_seqs, pred_seqs, prepared)

    print("=" * 65)
    print("  FALSE POSITIVES  (model predicted skill, ground truth = O)")
    print("=" * 65)
    if fp:
        for item in fp[:10]:
            print(f"  [{item['predicted']}]  '{item['span']}'  (ex #{item['example_idx']})")
    else:
        print("  None — perfect precision!")

    print()
    print("=" * 65)
    print("  FALSE NEGATIVES  (ground truth = skill, model predicted O)")
    print("=" * 65)
    if fn:
        for item in fn[:10]:
            print(f"  [{item['true_label']}]  '{item['span']}'  (ex #{item['example_idx']})")
    else:
        print("  None — perfect recall!")

    # ── Save results ──────────────────────────────────────────────────────
    if args.save_results:
        results = {
            "precision": overall_p,
            "recall":    overall_r,
            "f1":        overall_f1,
            "false_positives": fp,
            "false_negatives": fn,
        }
        with open(args.save_results, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅  Results saved to '{args.save_results}'")


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Evaluate Skill NER model")
    p.add_argument("--model_dir",    default="./saved_model")
    p.add_argument("--save_results", default=None, help="Path to save JSON results")
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
