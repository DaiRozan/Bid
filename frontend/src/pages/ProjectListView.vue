<script setup lang="ts">
import { onMounted, ref } from "vue";
import { listProjects, type Project } from "../api/projects";
import ProjectForm from "../components/ProjectForm.vue";
const emit = defineEmits<{ open: [Project] }>();
const projects = ref<Project[]>([]);
const error = ref("");
async function load() { try { projects.value = await listProjects(); error.value = ""; } catch (e) { error.value = e instanceof Error ? e.message : "项目列表读取失败"; } }
onMounted(load);
</script>
<template><section><div class="section-title"><div><p class="eyebrow">工作区</p><h2>项目列表</h2></div><span class="count">{{ projects.length }} 个项目</span></div><ProjectForm @created="load" /><p v-if="error" class="error">{{ error }}</p><table class="data-table project-table"><thead><tr><th>项目编号</th><th>项目名称</th><th>工程类别</th><th>目标页数</th><th>处理状态</th><th>操作</th></tr></thead><tbody><tr v-for="project in projects" :key="project.id"><td>{{ project.code }}</td><td>{{ project.name }}</td><td>{{ project.engineering_type === "building" ? "建筑工程" : "市政工程" }}</td><td>{{ project.target_pages }}</td><td>{{ project.status }}</td><td><button type="button" @click="emit('open', project)">进入项目</button></td></tr><tr v-if="!projects.length"><td colspan="6" class="muted">还没有项目</td></tr></tbody></table></section></template>

