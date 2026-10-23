import { apiRequest } from "./client";
import type { ChapterBlock } from "../components/chapterBlocks";
export type Chapter = { id: string; title: string; outline_position: number; stale: boolean; versions: { id: string; blocks: ChapterBlock[]; source: string; fact_version: number }[] };
export const listChapters = (id: string) => apiRequest<Chapter[]>(`/projects/${id}/chapters`);
export const createChapter = (id: string, value: { title: string; outline_position: number; blocks: ChapterBlock[] }) => apiRequest<Chapter>(`/projects/${id}/chapters`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(value) });
export const updateChapter = (id: string, blocks: ChapterBlock[]) => apiRequest<Chapter>(`/chapters/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ blocks }) });
export const generateChapter = (id: string) => apiRequest<{ job: { id: string }; chapter: Chapter }>(`/chapters/${id}/generate`, { method: "POST" });

