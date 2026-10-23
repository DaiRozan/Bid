import { describe, expect, it } from "vitest";
import { serializeBlocks, type ChapterBlock } from "./chapterBlocks";

describe("chapter block editor data", () => {
  it("preserves paragraph and table blocks when saved", () => {
    const blocks: ChapterBlock[] = [
      { type: "paragraph", text: "施工部署" },
      { type: "table", rows: [["工作", "安排"], ["测量", "复核"]] },
    ];
    expect(serializeBlocks(blocks)).toEqual(blocks);
  });
});
