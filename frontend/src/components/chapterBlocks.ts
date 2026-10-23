export type ChapterBlock = { type: "paragraph"; text: string; heading_level?: number | null } | { type: "table"; rows: string[][] };
export const serializeBlocks = (blocks: ChapterBlock[]): ChapterBlock[] => structuredClone(blocks);

