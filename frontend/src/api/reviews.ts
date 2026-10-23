import { apiRequest } from "./client";
export type ReviewIssue = { id: string; code: string; severity: string; message: string; location?: string | null; status: string };
export const runChecks = (id: string) => apiRequest<{ status: string; issues: ReviewIssue[] }>(`/projects/${id}/checks/run`, { method: "POST" });
export const listIssues = (id: string) => apiRequest<ReviewIssue[]>(`/projects/${id}/issues`);

