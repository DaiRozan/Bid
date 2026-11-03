import { apiRequest } from "./client";

export type LibraryEntry = {
  id: string; field_name?: string; value?: string | number; source_type?: string;
  source_block_ids?: string[]; archive_path?: string; location?: Record<string, unknown>;
  record_type?: string; type?: string; unit?: string; formula?: string; adoptable?: boolean;
  name?: string; review_status?: string; source_handles?: string[];
};
export type LibraryDraft = {
  facts: LibraryEntry[]; review: LibraryEntry[]; fact_count: number; review_count: number;
  filtered_count: number; issues: { message: string }[]; files: string[];
  file_labels: Record<string, string>; documents: { id: string; filename: string; status: string; archive_path: string; analysis_summary: Record<string, number | null> }[];
};
export type Snapshot = { version: number; snapshot_id: string; fact_count: number; review_count: number; files: string[]; directory: string; issues: {message: string}[] };
export const getLibrary = (id: string, section = "facts", search = "", offset = 0) =>
  apiRequest<LibraryDraft>(`/projects/${id}/fact-library?${new URLSearchParams({ section, search, offset: String(offset), limit: "50", exclude_drawings:"true" })}`);
export const getSnapshot = async (id: string): Promise<Snapshot | null> => {
  const response = await fetch(`/api/projects/${id}/fact-library/current?summary=true`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error((await response.json()).detail || "固定事实版本读取失败");
  return response.json();
};
export const publishLibrary = (id: string, acknowledge: boolean) => apiRequest<Snapshot>(`/projects/${id}/fact-library/publish?summary=true`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ acknowledge_issues: acknowledge }),
});
export const adoptLibraryFact = (id: string, targetId: string, value: string, reason: string, sources: string[]) => apiRequest(`/projects/${id}/fact-library/adoptions`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_id: targetId, value, reason, source_block_ids: sources }),
});
export const getLibraryFile = (id: string, name: string, published: boolean) => apiRequest<{ name: string; content: string }>(`/projects/${id}/fact-library/file?${new URLSearchParams({ name, published: String(published) })}`);
