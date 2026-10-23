<script setup lang="ts">
import type { Outline } from "../api/outline";
defineProps<{ outline: Outline }>();
</script>
<template><div class="outline"><div v-for="(item, index) in outline.items" :key="index" class="outline-row"><input v-model="item.title" /><label><input v-model="item.required" type="checkbox" /> 必选</label><input v-model.number="item.budget_pages" type="number" min="0" aria-label="篇幅预算" /></div></div></template>

