import { apiRequest, jsonBody } from "./client";
export type Project = { id: string; code: string; name: string; engineering_type: "building" | "municipal"; status: string; target_pages: number; facts_version: number };
export const listProjects = () => apiRequest<Project[]>("/projects");
export const createProject = (value: Pick<Project, "code" | "name" | "engineering_type"> & { target_pages?: number }) => apiRequest<Project>("/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(value) });
export const getProject = (id: string) => apiRequest<Project>(`/projects/${id}`);

