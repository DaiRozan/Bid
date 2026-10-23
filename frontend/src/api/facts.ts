import { apiRequest } from "./client";
export type Fact = { id: string; field_name: string; raw_value: string | null; confirmed_value: string | null; unit: string | null; source_block_ids: string[]; status: string };
export const listFacts = (id: string) => apiRequest<Fact[]>(`/projects/${id}/facts`);
export const saveFact = (projectId: string, factId: string, value: string | null) => apiRequest<Fact>(`/projects/${projectId}/facts/${factId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmed_value: value }) });

