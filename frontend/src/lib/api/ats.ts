import { api } from "./client";

export interface ATSResult {
  cv_id: number;
  ats_score: number;
  keyword_score: number;
  format_score: number;
  completeness_score: number;
  missing_keywords: string[];
  matched_keywords: string[];
  warnings: string[];
  suggestions: string[];
  created_at: string;
}

export async function optimizeCV(
  cvId: number,
  offerText?: string,
  offerId?: number
): Promise<ATSResult> {
  const { data } = await api.post<ATSResult>("/ats/optimize", {
    cv_id: cvId,
    offer_text: offerText ?? null,
    offer_id: offerId ?? null,
  });
  return data;
}

export async function getATSHistory(cvId: number): Promise<ATSResult[]> {
  const { data } = await api.get<ATSResult[]>(`/ats/history/${cvId}`);
  return data;
}
