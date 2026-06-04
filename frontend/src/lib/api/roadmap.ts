import { api } from "./client";

export interface RoadmapStep {
  id: number;
  week_number: number;
  title: string;
  skill_name?: string;
  type: string;
  resource_link?: string;
  description?: string;
  tip?: string;
}

export interface RoadmapOut {
  roadmap_id: number;
  job_name: string;
  duration_weeks: number;
  engine: string;
  intro?: string;
  market_insight?: string;
  steps: RoadmapStep[];
  summary: Record<string, number>;
  created_at: string;
}

export async function generateRoadmap(
  careerGapId: number,
  durationWeeks = 8,
  useRag = true,
  useLlm = true
): Promise<RoadmapOut> {
  const { data } = await api.post<RoadmapOut>("/roadmap/generate", {
    career_gap_id: careerGapId,
    duration_weeks: durationWeeks,
    use_rag: useRag,
    use_llm: useLlm,
  });
  return data;
}

export async function listRoadmaps(): Promise<RoadmapOut[]> {
  const { data } = await api.get<RoadmapOut[]>("/roadmap/");
  return data;
}

export async function getRoadmap(id: number): Promise<RoadmapOut> {
  const { data } = await api.get<RoadmapOut>(`/roadmap/${id}`);
  return data;
}

export async function updateStepProgress(
  stepId: number,
  status: "completed" | "in_progress" | "not_started"
): Promise<void> {
  await api.patch("/roadmap/progress", { step_id: stepId, status });
}
