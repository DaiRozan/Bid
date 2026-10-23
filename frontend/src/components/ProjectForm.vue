<script setup lang="ts">
import { reactive, ref } from "vue";
import { createProject } from "../api/projects";
const emit = defineEmits<{ created: [] }>();
const error = ref("");
const form = reactive({ code: "", name: "", engineering_type: "building" as "building" | "municipal", target_pages: 50 });
async function submit() { error.value = ""; try { await createProject(form); Object.assign(form, { code: "", name: "", target_pages: 50 }); emit("created"); } catch (e) { error.value = e instanceof Error ? e.message : "创建项目失败"; } }
</script>
<template>
  <form class="project-form" @submit.prevent="submit">
    <input v-model="form.code" required placeholder="项目编号" aria-label="项目编号" />
    <input v-model="form.name" required placeholder="项目名称" aria-label="项目名称" />
    <select v-model="form.engineering_type" aria-label="工程类别"><option value="building">建筑工程</option><option value="municipal">市政工程</option></select>
    <input v-model.number="form.target_pages" type="number" min="1" max="500" aria-label="目标页数" />
    <button type="submit">新建项目</button>
    <span v-if="error" class="error">{{ error }}</span>
  </form>
</template>

