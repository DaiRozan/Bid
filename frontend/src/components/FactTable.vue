<script setup lang="ts">
import { ref } from "vue";
import { saveFact, type Fact } from "../api/facts";
const props = defineProps<{ projectId: string; facts: Fact[] }>();
const emit = defineEmits<{ changed: [] }>();
const saving = ref("");
async function save(fact: Fact) { saving.value = fact.id; await saveFact(props.projectId, fact.id, fact.confirmed_value); saving.value = ""; emit("changed"); }
</script>
<template><table class="data-table"><thead><tr><th>字段</th><th>原始值</th><th>确认值</th><th>状态</th><th></th></tr></thead><tbody><tr v-for="fact in props.facts" :key="fact.id"><td>{{ fact.field_name }}</td><td>{{ fact.raw_value || "未提取" }}</td><td><input v-model="fact.confirmed_value" :aria-label="`${fact.field_name}确认值`" /></td><td>{{ fact.status }}</td><td><button type="button" @click="save(fact)">{{ saving === fact.id ? "保存中" : "保存" }}</button></td></tr></tbody></table></template>

