import { apiRequest } from "./client";
export type ExportRecord = { id: string; status: string; page_count: string };
export const createExport = (id: string) => apiRequest<ExportRecord>(`/projects/${id}/exports`, { method: "POST" });
export const downloadExport = (id: string) => `/api/exports/${id}/download`;

