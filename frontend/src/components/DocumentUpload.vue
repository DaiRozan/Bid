<script setup lang="ts">
import { ref } from "vue";
import { parseDocument, uploadDocument, type SourceDocument } from "../api/documents";
const props = defineProps<{ projectId: string }>();
const emit = defineEmits<{ updated: [SourceDocument] }>();
const error = ref("");
async function onChange(event: Event) { const input = event.target as HTMLInputElement; const file = input.files?.[0]; if (!file) return; try { const document = await uploadDocument(props.projectId, file); emit("updated", await parseDocument(document.id)); } catch (e) { error.value = e instanceof Error ? e.message : "上传失败"; } }
</script>
<template><div class="upload"><label>上传招标文件 <input type="file" accept=".docx,.pdf" @change="onChange" /></label><span v-if="error" class="error">{{ error }}</span></div></template>

