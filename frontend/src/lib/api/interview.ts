import { api } from "./client";

export interface InterviewQuestion {
  question_text: string;
  related_skill?: string;
}

export interface InterviewSessionResponse {
  session_id: number;
  questions: InterviewQuestion[];
  created_at: string;
}

export async function startInterview(
  userTargetJobId: number,
  numQuestions = 5,
  offerId?: number
): Promise<InterviewSessionResponse> {
  const { data } = await api.post<InterviewSessionResponse>("/interview/start", {
    user_target_job_id: userTargetJobId,
    num_questions: numQuestions,
    offer_id: offerId ?? null,
  });
  return data;
}

export async function listInterviewSessions(): Promise<InterviewSessionResponse[]> {
  const { data } = await api.get<InterviewSessionResponse[]>("/interview/sessions");
  return data;
}
