from fastapi import FastAPI
from pydantic import BaseModel
import json
import re

app = FastAPI(title="ML Skill Extraction API")

# -----------------------------
# LOAD TAXONOMY
# -----------------------------
with open("skill_taxonomy.json") as f:
    taxonomy = json.load(f)

alias_to_skill = {}

for skill, aliases in taxonomy.items():
    for alias in aliases:
        alias_to_skill[alias.lower()] = skill.lower()
    alias_to_skill[skill.lower()] = skill.lower()

# -----------------------------
# INPUT MODEL
# -----------------------------
class TextInput(BaseModel):
    text: str

# -----------------------------
# FAKE BERT (TEMP)
# -----------------------------
def bert_inference(text):
    text = text.lower()
    skills = set()

    for alias in alias_to_skill:
        if re.search(r"\b" + re.escape(alias) + r"\b", text):
            skills.add(alias_to_skill[alias])

    return list(skills)

# -----------------------------
# ROUTE 1: Extract Skills
# -----------------------------
@app.post("/extract-skills")
def extract_skills(data: TextInput):
    skills = bert_inference(data.text)

    return {
        "skills": skills,
        "count": len(skills)
    }
from gap_calculator import calculate_gap
from scorer import compute_score


class GapInput(BaseModel):
    cv_text: str
    market_text: str


@app.post("/calculate-gap")
def calculate_gap_api(data: GapInput):

    cv_skills = bert_inference(data.cv_text)

    market_skills = bert_inference(data.market_text)

    gap = calculate_gap(
        cv_skills,
        market_skills
    )

    # poids simples pour test
    job_skills = {
        skill:1 for skill in market_skills
    }

    score = compute_score(
        cv_skills,
        job_skills
    )

    return {
        "cv_skills":cv_skills,
        "market_skills":market_skills,
        "gap":gap,
        "score":score
    }