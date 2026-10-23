<script setup lang="ts">
import type { KnowledgeItem } from "../api/knowledge";
defineProps<{ items: KnowledgeItem[] }>();
</script>
<template><table class="data-table"><thead><tr><th>资料</th><th>类型</th><th>来源</th><th>核验状态</th></tr></thead><tbody><tr v-for="item in items" :key="item.id"><td>{{ item.title }}</td><td>{{ item.kind }}</td><td>{{ item.source }}</td><td>{{ item.verification_status }}</td></tr></tbody></table></template>

