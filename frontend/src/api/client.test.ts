import { describe, expect, it, vi } from "vitest";
import { apiRequest } from "./client";
import { pollJob } from "./jobs";

describe("API client", () => {
  it("shows safe server errors without exposing a configured key", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "DeepSeek 请求失败" }), { status: 502 })));
    await expect(apiRequest("/projects")).rejects.toThrow("DeepSeek 请求失败");
  });

  it("polls an extraction job until it finishes", async () => {
    const get = vi.fn().mockResolvedValueOnce({ id: "j1", status: "running" }).mockResolvedValueOnce({ id: "j1", status: "succeeded" });
    const job = await pollJob("j1", get, 0);
    expect(get).toHaveBeenCalledTimes(2);
    expect(job.status).toBe("succeeded");
  });
});
