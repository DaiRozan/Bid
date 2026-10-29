<script setup lang="ts">
import { ref } from "vue";
import { parseDocument, uploadDocument, type SourceDocument } from "../api/documents";
const props = defineProps<{ projectId: string }>();
const emit = defineEmits<{ updated: [SourceDocument] }>();
const error = ref("");
const busy = ref(false);
async function onChange(event: Event) { const input = event.target as HTMLInputElement; const file = input.files?.[0]; if (!file) return; busy.value = true; error.value = ""; try { const document = await uploadDocument(props.projectId, file); emit("updated", document); emit("updated", await parseDocument(document.id)); } catch (e) { error.value = e instanceof Error ? e.message : "上传失败"; } finally { busy.value = false; input.value = ""; } }
</script>
<template><div class="upload"><label>上传完整招标资料包或单文件 <input type="file" accept=".zip,.rar,.doc,.docx,.pdf,.xls,.xlsx,.dwg,.dxf" :disabled="busy" @change="onChange" /></label><p v-if="busy" class="notice" role="status">正在上传、解包并读取资料，图纸较多时可能需要数分钟。完成后可在固定事实库核对结果。</p><span v-if="error" class="error">{{ error }}</span></div></template>

