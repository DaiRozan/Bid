import { apiRequest } from "./client";
export type KnowledgeItem = { id: string; kind: string; title: string; source: string; verification_status: string };
export const listKnowledge = (keyword = "") => apiRequest<KnowledgeItem[]>(`/knowledge?keyword=${encodeURIComponent(keyword)}`);
export const addKnowledge = (value: { kind: string; title: string; body: string; source: string; standard_number?: string }) => apiRequest<KnowledgeItem>("/knowledge", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(value) });

