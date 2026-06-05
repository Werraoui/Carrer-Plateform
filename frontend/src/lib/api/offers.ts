import { api } from "./client";

export interface OfferSubmitResponse {
  offer_id: number;
  skills_extracted: string[];
  target_job_id?: number | null;
  next_steps: string[];
}

export async function submitOffer(payload: {
  title: string;
  company: string;
  raw_text: string;
  target_job_id?: number;
}): Promise<OfferSubmitResponse> {
  const { data } = await api.post<OfferSubmitResponse>("/offers/submit", payload);
  return data;
}
