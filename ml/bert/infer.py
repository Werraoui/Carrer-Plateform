import argparse
import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification


# ══════════════════════════════════════════════════════════════════════════════
# TEXT CLEANER
# Strips job posting noise BEFORE skill extraction:
#   - Security clearances (TS/SCI, Polygraph)
#   - Job codes / requisition numbers
#   - Salary / benefits / legal boilerplate
#   - Location + header lines
#   - HTML artifacts
# ══════════════════════════════════════════════════════════════════════════════

# Acronyms that look like all-caps noise but are real tech skills — never remove
_KEEP_ACRONYMS: Set[str] = {
    "SQL","API","AWS","GCP","ETL","ELT","NLP","ML","AI","CI","CD",
    "TDD","BDD","REST","CLI","SDK","UI","UX","ORM","RPC","DNS","SSL",
    "TLS","SSH","JWT","OAuth","GDPR","CCPA","PII","SLA","KPI","DAG",
    "DBT","DVC","ELK","YAML","JSON","XML","CSV","HTML","CSS","HTTP",
    "HTTPS","TCP","UDP","GPU","CPU","RAM","JVM","OOP","SWE","SRE",
    "MLOps","DevOps","DataOps","BI","ETL","ELT","RLHF",
}

# Regex patterns for lines/phrases to strip entirely
_NOISE_PATTERNS = [
    r'TS/SCI[\s\-–—]*[\w/]*',           # TS/SCI clearance
    r'Polygraph\s*\w*',                   # Polygraph Required
    r'\b\d{2,4}[-–]\d{3,6}[-–]\w+\b', # job codes like 08-6578-SWE
    r'View all jobs',                       # site navigation text
    r'(?:Equal\s+Opportunity|EEO|EOE)[^\n.]*',
    r'\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?', # salary ranges
    r'(?:we\s+are\s+an?\s+equal)[^\n.]*',
    r'(?:race|religion|color|national\s+origin)[^\n.]*',
    r'(?:salary|compensation|benefits?|401k|PTO|vacation|insurance)[^\n]*',
    r'(?:apply|application|submit|resume|cover\s+letter)[^\n]*',
]
_NOISE_RE = re.compile('|'.join(_NOISE_PATTERNS), re.IGNORECASE)


def clean_text(text: str) -> str:
    """
    Remove job posting noise before skill extraction.

    What gets removed:
      TS/SCI, Polygraph, job codes, salary info, benefits,
      EEO disclaimers, location metadata, HTML tags.

    What is preserved:
      All technical and soft skill mentions, tool names,
      programming languages, responsibilities sections.
    """
    # 1. Strip HTML tags if any
    text = re.sub(r'<[^>]+>', ' ', text)

    # 2. Remove known noise patterns
    text = _NOISE_RE.sub(' ', text)

    # 3. Remove all-caps words that are NOT known tech acronyms
    #    e.g. "MARYLAND", "REQUIRED", "SOFTWARETS" — location/header garbage
    def _keep_token(tok):
        alpha = re.sub(r'[^A-Za-z]', '', tok)
        if not alpha:
            return True   # keep punctuation/numbers
        # Only drop PURELY uppercase tokens >3 chars that aren't known acronyms
        # Mixed-case words like Python, JavaScript, Grafana are always kept
        if alpha == alpha.upper() and len(alpha) > 3 and alpha not in _KEEP_ACRONYMS:
            return False
        return True

    tokens = text.split()
    text = ' '.join(t for t in tokens if _keep_token(t))

    # 4. Collapse extra whitespace
    text = re.sub(r'\s{2,}', ' ', text).strip()

    return text


# ══════════════════════════════════════════════════════════════════════════════
# KNOWN MULTI-WORD SKILLS DICTIONARY
# When the model extracts only the first word, this dictionary extends it
# to the full known phrase automatically.
# Add any skill that the model keeps truncating.
# ══════════════════════════════════════════════════════════════════════════════

MULTI_WORD_SKILLS: List[str] = [
    # ML / AI core
    "machine learning", "deep learning", "reinforcement learning",
    "transfer learning", "supervised learning", "unsupervised learning",
    "federated learning", "representation learning",
    "natural language processing", "computer vision",
    "large language models", "generative ai",
    "generative adversarial networks", "convolutional neural networks",
    "recurrent neural networks", "graph neural networks", "neural networks",
    "diffusion models", "gradient boosting", "random forests",
    "decision trees", "linear regression", "logistic regression",
    "feature engineering", "feature selection", "dimensionality reduction",
    "object detection", "image segmentation", "pose estimation",
    "optical flow", "sentiment analysis", "text classification",
    "named entity recognition", "prompt engineering",
    "retrieval-augmented generation", "model interpretability",
    "model monitoring", "data drift", "concept drift", "model degradation",
    "experiment tracking", "model versioning", "production inference",
    "collaborative filtering", "content-based filtering",
    "matrix factorization", "policy gradient", "actor-critic",
    "recommendation systems", "adversarial robustness", "data augmentation",
    "cross-validation", "mixed precision training", "distributed training",
    "custom training loops", "attention visualization",
    "counterfactual explanations", "algorithm development",

    # Data Engineering
    "etl pipelines", "etl workflows", "elt workflows",
    "data pipelines", "data lakes", "data warehousing", "data modeling",
    "dimensional modeling", "schema design", "star schema", "snowflake schema",
    "stream processing", "streaming pipelines", "batch pipelines",
    "change data capture", "data lineage", "data governance",
    "data cataloging", "metadata management", "distributed systems",
    "event-driven architecture", "message queuing", "columnar storage",
    "dependency management", "real-time data ingestion", "real-time processing",
    "data quality", "data architecture", "data products", "data transformation",
    "data validation", "data integrity", "data encryption",
    "data privacy", "data anonymization", "data lifecycle",
    "upstream data collection", "reusable transformations",
    "root cause analysis", "anomaly detection", "observability",

    # Software Engineering
    "object-oriented programming", "functional programming", "design patterns",
    "microservices architecture", "service mesh", "api gateway",
    "restful apis", "rest apis", "restful api", "api integrations",
    "graphql subscriptions", "server-sent events", "data structures",
    "time complexity", "memory management", "state management",
    "ci/cd pipelines", "continuous integration", "automated deployment",
    "caching strategies", "branching strategies", "monorepo management",
    "system design", "cap theorem", "consensus algorithms",
    "eventual consistency", "secure coding", "penetration testing",
    "clean code", "code reviews", "technical documentation",
    "unit testing", "integration testing", "unit tests",
    "software design", "database architecture", "full-stack development",
    "version control", "access controls", "secure data transfer",
    "agile methodologies", "coding standards",

    # Data Analysis
    "data visualization", "data manipulation", "statistical analysis",
    "window functions", "query optimization", "stored procedures",
    "dashboard creation", "a/b testing", "a/b experiments",
    "multivariate testing", "experimental design", "statistical significance",
    "cohort analysis", "funnel analysis", "churn analysis",
    "customer segmentation", "rfm modeling", "descriptive statistics",
    "inferential statistics", "probability distributions",
    "regression analysis", "time series analysis", "bayesian analysis",
    "monte carlo simulation", "causal inference", "data cleaning",
    "outlier detection", "missing value imputation", "web scraping",
    "geospatial analysis", "data storytelling", "pivot tables",
    "power query", "pii handling",

    # Cloud / infra
    "cloud-based data storage", "cloud fundamentals",
    "big data", "stream processing",

    # Soft skills
    "problem solving", "problem-solving skills", "critical thinking",
    "analytical reasoning", "communication skills", "written communication",
    "presentation skills", "time management", "prioritization skills",
    "attention to detail", "growth mindset", "conflict resolution",
    "intellectual curiosity", "research ability", "scientific thinking",
    "ownership mindset", "resilience under ambiguity",
    "continuous learning", "collaborative attitude", "natural curiosity",
    "clear communication",
]

# Build fast first-word lookup
_FIRST_WORD_INDEX: Dict[str, List[str]] = {}
for _phrase in MULTI_WORD_SKILLS:
    _first = _phrase.split()[0].lower()
    _FIRST_WORD_INDEX.setdefault(_first, []).append(_phrase.lower())



CONFIDENCE_THRESHOLD = 0.50



SINGLE_WORD_BLOCKLIST: Set[str] = {
    # too vague
    "data", "collection", "infrastructure", "project", "engineering",
    "reporting", "performance", "pipeline", "pipelines", "batch",
    "streaming", "query", "queries", "indexing", "index",
    "analysis", "analytics", "process", "processing", "service",
    "services", "system", "systems", "tool", "tools", "platform",
    "solution", "solutions", "approach", "method", "methods",
    "technique", "techniques", "framework", "frameworks",
    "architecture", "design", "development", "implementation",
    "management", "monitoring", "testing", "validation", "integration",
    "deployment", "automation", "optimization", "transformation",
    "storage", "security", "governance", "quality", "reliability",
    "accuracy", "consistency", "integrity", "lifecycle", "operations",
    "delivery", "documentation", "review", "reviews", "environment",
    "workflow", "workflows", "component", "database", "databases",
    "model", "models", "network", "networks", "server", "servers",
    "cloud", "stack", "layer", "module", "library", "libraries",
    "interface", "api", "apis",
    # job posting noise
    "algorithm", "algorithms", "real-time", "real", "time",
    "clearance", "polygraph", "required", "mandatory", "preferred",
    "junior", "senior", "lead", "principal", "associate",
    "engineer", "developer", "analyst", "scientist", "specialist",
    "computer", "software", "hardware", "manager", "director",
    "experience", "knowledge", "understanding", "familiarity",
    "ability", "skills", "skill", "background", "expertise",
    "candidate", "candidates", "role", "position", "team",
    "business", "company", "organization", "department",
    "information", "technology", "application", "applications",
}



PHRASE_BLOCKLIST: Set[str] = {
    "novel algorithm", "novel algorithms",
    "business management", "business management information",
    "real-time systems", "real-time system",
    "maryland computer", "information systems",
    "new development", "new technologies",
    "extremely large", "large data",
    "processing-intensive analytics",
    "software components", "system design to",
    "hardware/software trade", "data engineering",
    "software engineering", "data analysis", "ai engineering"
}


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class SkillSpan:
    text:       str
    label:      str
    start_tok:  int
    end_tok:    int
    confidence: float = 0.0


@dataclass
class ExtractionResult:
    text:          str
    cleaned_text:  str = ""
    skills:        List[SkillSpan] = field(default_factory=list)

    @property
    def by_category(self) -> Dict[str, List[str]]:
        result = {"TECH": [], "SOFT": []}
        for s in self.skills:
            result.setdefault(s.label, []).append(s.text)
        return result

    def to_dict(self):
        return {
            "text":        self.text,
            "skills":      [asdict(s) for s in self.skills],
            "by_category": self.by_category,
        }


# ── Predictor ─────────────────────────────────────────────────────────────────

class SkillExtractor:

    def __init__(self, model_dir: str, device: Optional[str] = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        print(f"Loading model from '{model_dir}' on {self.device} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model     = AutoModelForTokenClassification.from_pretrained(model_dir)
        self.model.to(self.device)
        self.model.eval()
        self.id2label = self.model.config.id2label
        print("Model ready.\n")

    # ── Core prediction ───────────────────────────────────────────────────────

    def predict(self, text: str) -> ExtractionResult:

        # Step 1: clean noise from input
        cleaned = clean_text(text)

        # Step 2: tokenize
        encoding = self.tokenizer(
            cleaned,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            return_offsets_mapping=True,
        )
        offset_mapping = encoding.pop("offset_mapping")[0].tolist()
        word_ids       = encoding.word_ids(batch_index=0)
        input_ids      = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        # Step 3: run model
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)

        probs      = torch.softmax(outputs.logits[0], dim=-1).cpu()
        pred_ids   = torch.argmax(probs, dim=-1).tolist()
        pred_probs = probs.max(dim=-1).values.tolist()

        # Step 4: collapse sub-tokens → word level
        word_label    = {}
        word_charspan = {}
        prev_word_id  = None
        for i, word_id in enumerate(word_ids):
            if word_id is None:
                continue
            offsets = offset_mapping[i]
            if word_id not in word_charspan:
                word_charspan[word_id] = [offsets[0], offsets[1]]
            else:
                word_charspan[word_id][1] = offsets[1]
            if word_id != prev_word_id:
                word_label[word_id] = (self.id2label[pred_ids[i]], pred_probs[i])
            prev_word_id = word_id

        # Step 5: BIO span assembly at word level
        skills: List[SkillSpan] = []
        current_span = None
        for word_id in sorted(word_label.keys()):
            label, prob          = word_label[word_id]
            char_start, char_end = word_charspan[word_id]
            if label == "O":
                if current_span:
                    skills.append(self._finalise(current_span, cleaned))
                    current_span = None
            elif label.startswith("B-"):
                if current_span:
                    skills.append(self._finalise(current_span, cleaned))
                current_span = [char_start, char_end, label[2:], [prob]]
            elif label.startswith("I-"):
                if current_span:
                    current_span[1] = char_end
                    current_span[3].append(prob)
                else:
                    current_span = [char_start, char_end, label[2:], [prob]]
        if current_span:
            skills.append(self._finalise(current_span, cleaned))

        # Step 6: expand truncated multi-word skills
        skills = self._expand_multiword(skills, cleaned)

        # Step 7: filter false positives
        skills = self._filter_skills(skills)

        # Step 8: deduplicate
        seen, unique = set(), []
        for s in skills:
            key = (s.text.lower(), s.label)
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return ExtractionResult(text=text, cleaned_text=cleaned, skills=unique)

    # ── Multi-word expansion ──────────────────────────────────────────────────

    def _expand_multiword(self, skills: List[SkillSpan], text: str) -> List[SkillSpan]:
        expanded   = []
        text_lower = text.lower()
        for skill in skills:
            extracted_lower = skill.text.lower().strip()
            first_word      = extracted_lower.split()[0]
            candidates      = _FIRST_WORD_INDEX.get(first_word, [])
            best_match      = None
            for phrase in candidates:
                if phrase == extracted_lower:
                    best_match = phrase
                    break
                if phrase.startswith(extracted_lower + " "):
                    phrase_at_pos = text_lower[skill.start_tok: skill.start_tok + len(phrase)]
                    if phrase_at_pos == phrase:
                        if best_match is None or len(phrase) > len(best_match):
                            best_match = phrase
            if best_match and best_match != extracted_lower:
                new_end  = skill.start_tok + len(best_match)
                new_text = text[skill.start_tok:new_end].strip()
                expanded.append(SkillSpan(
                    text=new_text, label=skill.label,
                    start_tok=skill.start_tok, end_tok=new_end,
                    confidence=skill.confidence,
                ))
            else:
                expanded.append(skill)
        return expanded

    # ── Filter ────────────────────────────────────────────────────────────────

    def _filter_skills(self, skills: List[SkillSpan]) -> List[SkillSpan]:
        """
        Remove false positives using three rules:
          1. Confidence below threshold
          2. Single word in the generic blocklist
          3. Full phrase in the phrase blocklist
        """
        filtered = []
        for s in skills:
            # Rule 1: confidence
            if s.confidence < CONFIDENCE_THRESHOLD:
                continue
            text_lower = s.text.strip().lower()
            words      = text_lower.split()
            # Rule 2: single generic word
            if len(words) == 1 and words[0] in SINGLE_WORD_BLOCKLIST:
                continue
            # Rule 3: known false-positive phrase
            if text_lower in PHRASE_BLOCKLIST:
                continue
            # Rule 4: min length — skip 1-char extractions
            if len(s.text.strip()) < 2:
                continue
            filtered.append(s)
        return filtered

    def _finalise(self, span, text: str) -> SkillSpan:
        char_start, char_end, label, confs = span
        skill_text = text[char_start:char_end].strip()
        confidence = round(float(sum(confs) / len(confs)), 4)
        return SkillSpan(
            text=skill_text, label=label,
            start_tok=char_start, end_tok=char_end,
            confidence=confidence,
        )

    def predict_batch(self, texts: List[str]) -> List[ExtractionResult]:
        return [self.predict(t) for t in texts]

    @staticmethod
    def display(result: ExtractionResult):
        cat = result.by_category
        print("─" * 60)
        print(f"TEXT: {result.text[:100]}{'...' if len(result.text) > 100 else ''}")
        print()
        for category, label in [("Technical Skills", "TECH"), ("Soft Skills", "SOFT")]:
            items = cat.get(label, [])
            icon  = {"TECH": "🔧", "SOFT": "🤝"}[label]
            print(f"  {icon}  {category}:")
            if items:
                for skill in items:
                    conf = next((s.confidence for s in result.skills if s.text == skill), 0)
                    print(f"       • {skill:<35}  (conf: {conf:.2f})")
            else:
                print("       • —")
        print("─" * 60)


# ── Demo texts ────────────────────────────────────────────────────────────────

DEMO_TEXTS = [
    
       ''' Results-driven software engineer with extensive experience in Python and SQL, specializing in building scalable backend services using FastAPI. Proven track record in API Development — designing, documenting, and deploying RESTful and async APIs consumed by millions of users.
Deep expertise in Docker and Kubernetes for container orchestration, paired with hands-on Cloud Infrastructure management across modern cloud platforms. Experienced in implementing robust CI/CD pipelines that streamline delivery cycles and reduce time-to-production.
A strong advocate for Automation at every layer of the stack — from infrastructure provisioning to testing and monitoring. Combines sharp Problem Solving abilities with clear Communication Skills to collaborate effectively across engineering, product, and business teams.
    '''
]


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Skill NER Inference")
    p.add_argument("--model_dir", default="./ml/bert/model")
    p.add_argument("--text",  default=None)
    p.add_argument("--file",  default=None)
    p.add_argument("--demo",  action="store_true")
    p.add_argument("--json",  action="store_true")
    p.add_argument("--show_cleaned", action="store_true",
                   help="Also print the cleaned text that was fed to the model")
    return p.parse_args()


def main():
    args  = parse_args()
    model = SkillExtractor(args.model_dir)

    if args.text:
        texts = [args.text]
    elif args.file:
        with open(args.file) as f:
            texts = [l.strip() for l in f if l.strip()]
    else:
        texts = DEMO_TEXTS

    results = model.predict_batch(texts)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print("\n=== Skill Extraction Results ===\n")
        for r in results:
            if args.show_cleaned:
                print(f"[CLEANED]: {r.cleaned_text[:120]}...\n")
            SkillExtractor.display(r)


if __name__ == "__main__":
    main()