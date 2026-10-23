<script setup lang="ts">
import { ref } from "vue";
import type { Project } from "./api/projects";
import ProjectListView from "./pages/ProjectListView.vue";
import ProjectWorkspaceView from "./pages/ProjectWorkspaceView.vue";

const project = ref<Project | null>(null);

function openProject(value: Project) {
  project.value = value;
}

function backToProjects() {
  project.value = null;
}
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">施工组织设计工作台</p>
        <h1>技术标生成系统</h1>
      </div>
      <span class="status">真实资料模式 · DeepSeek {{ project ? "已配置" : "待调用" }}</span>
    </header>
    <ProjectWorkspaceView v-if="project" :project="project" @back="backToProjects" />
    <ProjectListView v-else @open="openProject" />
  </main>
</template>

<style>
:root { font-family: "Microsoft YaHei", system-ui, sans-serif; color: #17202a; background: #f5f7f8; }
* { box-sizing: border-box; }
body { margin: 0; }
.shell { min-height: 100vh; max-width: 1180px; margin: 0 auto; padding: 28px 32px 56px; }
.topbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; border-bottom: 1px solid #dfe5e8; padding-bottom: 24px; }
.eyebrow, .label { margin: 0 0 8px; color: #5b6b73; font-size: 13px; letter-spacing: .04em; }
h1, h2 { margin: 0; font-weight: 650; letter-spacing: 0; }
h1 { font-size: 28px; }
h2 { font-size: 30px; }
.status { padding: 8px 12px; border: 1px solid #b8d6c1; color: #216c3a; background: #eff8f1; font-size: 13px; }
button, input, select, textarea { font: inherit; }
button { border: 1px solid #173f5f; color: #fff; background: #173f5f; padding: 9px 14px; cursor: pointer; }
button:hover { background: #0f2f48; }
button:disabled { cursor: wait; opacity: .55; }
button.secondary { border-color: #ccd6db; color: #334047; background: #fff; }
button.secondary:hover { background: #f3f6f7; }
input, select, textarea { border: 1px solid #cbd6db; background: #fff; color: #17202a; padding: 9px 10px; }
input:focus, select:focus, textarea:focus, button:focus-visible { outline: 2px solid #74a7c7; outline-offset: 2px; }
.section-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin: 28px 0 16px; }
.section-title h2, .section-title h3 { margin: 0; }
.workspace { padding-top: 8px; }
.workspace-tabs { display: flex; flex-wrap: wrap; gap: 8px; padding: 4px 0 20px; border-bottom: 1px solid #dfe5e8; }
.workspace-tabs button { border-color: #ccd6db; color: #334047; background: #fff; }
.workspace-tabs button.selected { border-color: #173f5f; color: #fff; background: #173f5f; }
.workspace-section { padding-top: 4px; }
.data-table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e1e7ea; }
.data-table th, .data-table td { padding: 11px 12px; border-bottom: 1px solid #e6ecef; text-align: left; vertical-align: top; }
.data-table th { color: #53646c; font-size: 13px; font-weight: 600; background: #f7f9fa; }
.data-table tr:last-child td { border-bottom: 0; }
.data-table button { padding: 6px 10px; font-size: 13px; }
.project-form, .inline-form, .knowledge-form { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 20px; }
.knowledge-form textarea { flex: 1 1 100%; min-height: 100px; resize: vertical; }
.project-form input:nth-child(2) { min-width: 260px; flex: 1 1 260px; }
.project-form .error { flex-basis: 100%; }
.upload { margin-bottom: 16px; padding: 14px; border: 1px dashed #b8c7ce; background: #fbfcfc; }
.upload label { color: #334047; }
.upload input { margin-left: 12px; border: 0; padding: 0; background: transparent; }
.outline { display: grid; gap: 8px; margin-bottom: 12px; }
.outline-row { display: grid; grid-template-columns: minmax(180px, 1fr) auto 100px; gap: 10px; align-items: center; }
.chapter-editor { padding: 18px; border: 1px solid #e1e7ea; background: #fff; }
.chapter-heading { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.chapter-heading h3 { margin: 0; }
.block { margin: 10px 0; }
.block textarea { width: 100%; resize: vertical; line-height: 1.7; }
.editor-table { width: 100%; border-collapse: collapse; }
.editor-table td { border: 1px solid #d9e2e6; padding: 4px; }
.editor-table input { width: 100%; border: 0; }
.chapter-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.chapter-list button { color: #334047; border-color: #ccd6db; background: #fff; }
.error { color: #b42318; }
.notice { color: #216c3a; background: #eff8f1; border: 1px solid #b8d6c1; padding: 10px 12px; }
.muted { color: #68777e; }
.warning { color: #8a5a00; background: #fff6df; border: 1px solid #e7c978; padding: 4px 8px; font-size: 12px; }
.count { color: #5b6b73; font-size: 14px; }
@media (max-width: 760px) {
  .shell { padding: 20px 16px 40px; }
  .topbar, .section-title { flex-direction: column; }
  .outline-row { grid-template-columns: 1fr; }
  .project-form > * { flex: 1 1 100%; }
  .data-table { display: block; overflow-x: auto; }
}
</style>
