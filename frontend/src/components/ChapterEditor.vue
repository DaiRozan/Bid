<script setup lang="ts">
import { computed, ref } from "vue";
import { serializeBlocks, type ChapterBlock } from "./chapterBlocks";
import { updateChapter, type Chapter } from "../api/chapters";
const props = defineProps<{ chapter: Chapter }>();
const emit = defineEmits<{ saved: [Chapter] }>();
const blocks = ref<ChapterBlock[]>(serializeBlocks(props.chapter.versions.at(-1)?.blocks || []));
const saving = ref(false);
const currentVersion = computed(() => props.chapter.versions.at(-1));
async function save() { saving.value = true; emit("saved", await updateChapter(props.chapter.id, serializeBlocks(blocks.value))); saving.value = false; }
</script>
<template><section class="chapter-editor"><div class="chapter-heading"><h3>{{ chapter.title }}</h3><span v-if="chapter.stale" class="warning">待复核</span></div><p v-if="currentVersion" class="muted">当前版本 {{ currentVersion.version_number }} · {{ currentVersion.source }}</p><div v-for="(block, index) in blocks" :key="index" class="block"><textarea v-if="block.type === 'paragraph'" v-model="block.text" rows="3" /><table v-else class="editor-table"><tbody><tr v-for="(row, rowIndex) in block.rows" :key="rowIndex"><td v-for="(_, colIndex) in row" :key="colIndex"><input v-model="block.rows[rowIndex][colIndex]" /></td></tr></tbody></table></div><button type="button" @click="save">{{ saving ? "保存中" : "保存本章" }}</button></section></template>

