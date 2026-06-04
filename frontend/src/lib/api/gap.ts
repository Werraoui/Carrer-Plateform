import { api } from "./client";

export interface TargetJobOut {
  id: number;
  name: string;
  description?: string;
  sector?: string;
}

export interface UserTargetJobOut {
  id: number;
  user_id: number;
  target_job_id: number;
  is_active: boolean;
  target_job?: TargetJobOut;
}

export interface GapSkillDetail {
  skill_name: string;
  status: "acquired" | "missing";
  weight: number;
}

export interface GapResult {
  career_gap_id: number;
  employability_score: number;
  acquired_skills: string[];
  missing_skills: string[];
  gap_details: GapSkillDetail[];
  created_at: string;
}

export async function getAvailableJobs(): Promise<TargetJobOut[]> {
  const { data } = await api.get<TargetJobOut[]>("/gap/target-jobs/available");
  return data;
}

export async function setTargetJob(targetJobId: number): Promise<UserTargetJobOut> {
  const { data } = await api.post<UserTargetJobOut>("/gap/target-job", { target_job_id: targetJobId });
  return data;
}

export async function getMyTargetJobs(): Promise<UserTargetJobOut[]> {
  const { data } = await api.get<UserTargetJobOut[]>("/gap/target-jobs");
  return data;
}

export async function analyzeGap(
  cvId: number,
  targetJobId?: number,
  offerId?: number
): Promise<GapResult> {
  const { data } = await api.post<GapResult>("/gap/analyze", {
    cv_id: cvId,
    target_job_id: targetJobId ?? null,
    offer_id: offerId ?? null,
  });
  return data;
}

export async function getGapHistory(): Promise<GapResult[]> {
  const { data } = await api.get<GapResult[]>("/gap/history");
  return data;
}
