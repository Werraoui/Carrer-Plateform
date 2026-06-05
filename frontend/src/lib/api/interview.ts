import { api } from "./client";

export interface McqQuestion {
  question: string;
  choices: string[];
}

export interface AnswerReviewItem {
  question_number: number;
  question_type: string;
  question_text: string;
  user_answer: string;
  is_correct: boolean;
  feedback: string;
  improvement?: string | null;
}

export interface InterviewFinalReport {
  score_percent: number;
  score_label: string;
  overall_advice: string;
  summary: string;
  answers_review: AnswerReviewItem[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  question_type?: string | null;
  mcq?: McqQuestion | null;
  open_question?: string | null;
  final_report?: InterviewFinalReport | null;
}

export interface InterviewChatResponse {
  session_id: string;
  assistant_message: string;
  question_type?: string | null;
  mcq?: McqQuestion | null;
  open_question?: string | null;
  interview_complete: boolean;
  final_report?: InterviewFinalReport | null;
  history: ChatMessage[];
}

export async function sendInterviewMessage(
  message: string,
  sessionId?: string | null
): Promise<InterviewChatResponse> {
  const { data } = await api.post<InterviewChatResponse>("/interview/chat", {
    session_id: sessionId ?? null,
    message,
  });
  return data;
}

export async function getInterviewSession(sessionId: string): Promise<InterviewChatResponse> {
  const { data } = await api.get<InterviewChatResponse>(`/interview/chat/${sessionId}`);
  return data;
}
