from typing import List, Optional

from pydantic import BaseModel, Field


class McqQuestion(BaseModel):
    question: str
    choices: List[str] = Field(..., min_length=2, max_length=6)


class AnswerReviewItem(BaseModel):
    question_number: int
    question_type: str  # "mcq" | "open"
    question_text: str
    user_answer: str
    is_correct: bool
    feedback: str
    improvement: Optional[str] = None


class InterviewFinalReport(BaseModel):
    score_percent: int = Field(..., ge=0, le=100)
    score_label: str
    overall_advice: str
    summary: str
    answers_review: List[AnswerReviewItem] = []


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    question_type: Optional[str] = None  # "mcq" | "open"
    mcq: Optional[McqQuestion] = None
    open_question: Optional[str] = None
    final_report: Optional[InterviewFinalReport] = None


class InterviewChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1)


class InterviewChatResponse(BaseModel):
    session_id: str
    assistant_message: str
    question_type: Optional[str] = None
    mcq: Optional[McqQuestion] = None
    open_question: Optional[str] = None
    interview_complete: bool = False
    final_report: Optional[InterviewFinalReport] = None
    history: List[ChatMessage] = []
