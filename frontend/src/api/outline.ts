import { apiRequest } from "./client";
export type Outline = { engineering_type: string; items: { title: string; body: string; required: boolean; budget_pages: number }[] };
export const getOutline = (id: string) => apiRequest<Outline>(`/projects/${id}/outline`);
export const saveOutline = (id: string, value: Outline) => apiRequest<Outline>(`/projects/${id}/outline`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(value) });

