import { api } from "./client";

export interface CVResponse {
  id: number;
  user_id: number;
  file_path: string;
  uploaded_at: string;
  skills_extracted: string[];
}

export interface CVUploadResponse {
  cv_id: number;
  message: string;
  skills: string[];
  skill_count: number;
}

export async function uploadCV(file: File): Promise<CVUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<CVUploadResponse>("/cv/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listCVs(): Promise<CVResponse[]> {
  const { data } = await api.get<CVResponse[]>("/cv/");
  return data;
}

export async function deleteCV(cvId: number): Promise<void> {
  await api.delete(`/cv/${cvId}`);
}
