import { apiRequest } from "./client";
export type SourceDocument = { id: string; filename: string; status: string; error_message?: string | null; blocks: { id: string; text: string; location: Record<string, unknown> }[] };
export const listDocuments = (id: string) => apiRequest<SourceDocument[]>(`/projects/${id}/documents`);
export async function uploadDocument(id: string, file: File): Promise<SourceDocument> {
  const form = new FormData(); form.append("file", file);
  return apiRequest(`/projects/${id}/documents`, { method: "POST", body: form });
}
export const parseDocument = (id: string) => apiRequest<SourceDocument>(`/documents/${id}/parse`, { method: "POST" });
export const extractProject = (id: string) => apiRequest<{ job: { id: string }; result: unknown }>(`/projects/${id}/extract`, { method: "POST" });

