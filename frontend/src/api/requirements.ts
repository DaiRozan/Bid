import { apiRequest } from "./client";
export type Requirement = { id: string; text: string; category?: string | null; score?: string | null; response_chapter_id?: string | null; status: string };
export const listRequirements = (id: string) => apiRequest<Requirement[]>(`/projects/${id}/requirements`);
export const addRequirement = (id: string, text: string) => apiRequest<Requirement>(`/projects/${id}/requirements/manual`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });

