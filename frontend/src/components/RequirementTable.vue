<script setup lang="ts">
import type { Requirement } from "../api/requirements";
defineProps<{ requirements: Requirement[] }>();
</script>
<template><table class="data-table"><thead><tr><th>编制要求</th><th>类别</th><th>响应章节</th><th>状态</th></tr></thead><tbody><tr v-for="item in requirements" :key="item.id"><td>{{ item.text }}</td><td>{{ item.category || "未分类" }}</td><td>{{ item.response_chapter_id || "未对应" }}</td><td>{{ item.status }}</td></tr></tbody></table></template>

