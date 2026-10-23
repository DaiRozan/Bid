import { apiRequest } from "./client";

export type Job = { id: string; status: string; progress?: number; error_message?: string | null };
export const getJob = (id: string) => apiRequest<Job>(`/jobs/${id}`);

export async function pollJob(id: string, get: (id: string) => Promise<Job> = getJob, interval = 1000): Promise<Job> {
  for (;;) {
    const job = await get(id);
    if (["succeeded", "failed", "interrupted"].includes(job.status)) return job;
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
}

