<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { Project } from "../api/projects";
import { extractProject, listDocuments, parseDocument, type SourceDocument } from "../api/documents";
import { listFacts, type Fact } from "../api/facts";
import { listRequirements, addRequirement, type Requirement } from "../api/requirements";
import { getOutline, saveOutline, type Outline } from "../api/outline";
import { createChapter, generateChapter, listChapters, type Chapter } from "../api/chapters";
import { addKnowledge, listKnowledge, type KnowledgeItem } from "../api/knowledge";
import { pollJob } from "../api/jobs";
import { listIssues, runChecks, type ReviewIssue } from "../api/reviews";
import { createExport, downloadExport } from "../api/exports";
import DocumentUpload from "../components/DocumentUpload.vue";
import FactTable from "../components/FactTable.vue";
import RequirementTable from "../components/RequirementTable.vue";
import OutlineEditor from "../components/OutlineEditor.vue";
import ChapterEditor from "../components/ChapterEditor.vue";
import IssueList from "../components/IssueList.vue";
import KnowledgePanel from "../components/KnowledgePanel.vue";
import FactLibraryPanel from "../components/FactLibraryPanel.vue";
import { getSnapshot, type Snapshot } from "../api/factLibrary";

const props = defineProps<{ project: Project }>();
defineEmits<{ back: [] }>();
const tabs = ["资料与事实", "固定事实库", "要求与目录", "章节工作区", "案例规范", "检查与导出"];
const snapshot = ref<Snapshot | null>(null);
const activeTab = ref(tabs[0]);
const documents = ref<SourceDocument[]>([]); const facts = ref<Fact[]>([]); const requirements = ref<Requirement[]>([]);
const outline = ref<Outline>({ engineering_type: props.project.engineering_type, items: [] }); const chapters = ref<Chapter[]>([]);
const knowledge = ref<KnowledgeItem[]>([]); const issues = ref<ReviewIssue[]>([]); const error = ref(""); const message = ref(""); const busy = ref("");
const requirementText = ref(""); const knowledgeTitle = ref(""); const knowledgeBody = ref(""); const knowledgeKind = ref("case"); const knowledgeSource = ref("");
const modelName = "deepseek-flash";
const currentChapter = computed(() => chapters.value[0]);

async function load() {
  error.value = "";
  try {
    snapshot.value = await getSnapshot(props.project.id);
    [documents.value, facts.value, requirements.value, outline.value, chapters.value, knowledge.value, issues.value] = await Promise.all([
      listDocuments(props.project.id), listFacts(props.project.id), listRequirements(props.project.id), getOutline(props.project.id), listChapters(props.project.id), listKnowledge(), listIssues(props.project.id),
    ]);
  } catch (e) { error.value = e instanceof Error ? e.message : "项目资料读取失败"; }
}
onMounted(load);
async function onDocument(document: SourceDocument) { documents.value = [document, ...documents.value.filter((item) => item.id !== document.id)]; if (document.status !== 'uploaded') await load(); }
async function extract() { busy.value = "正在提取事实与要求"; error.value = ""; try { const { job } = await extractProject(props.project.id); const completed = await pollJob(job.id); if (completed.status !== "succeeded") throw new Error(completed.error_message || "资料抽取失败"); await load(); message.value = "事实与要求提取完成，请逐项确认"; } catch (e) { error.value = e instanceof Error ? e.message : "抽取失败"; } finally { busy.value = ""; } }
async function saveOutlineAction() { try { outline.value = await saveOutline(props.project.id, outline.value); message.value = "目录已保存"; } catch (e) { error.value = String(e); } }
async function addOutlineItem() { outline.value.items.push({ title: "新章节", body: "", required: false, budget_pages: 1 }); }
async function saveRequirements() { if (!requirementText.value.trim()) return; await addRequirement(props.project.id, requirementText.value); requirementText.value = ""; requirements.value = await listRequirements(props.project.id); }
async function createOutlineChapters() { await saveOutline(props.project.id, outline.value); for (const [index, item] of outline.value.items.entries()) { if (!chapters.value.some((chapter) => chapter.title === item.title)) await createChapter(props.project.id, { title: item.title, outline_position: index + 1, blocks: [] }); } chapters.value = await listChapters(props.project.id); }
async function onSaved(chapter: Chapter) { chapters.value = chapters.value.map((item) => item.id === chapter.id ? chapter : item); message.value = "章节版本已保存"; }
async function generate() { if (!currentChapter.value) return; busy.value = `正在调用 ${modelName} 生成`; error.value = ""; try { const result = await generateChapter(currentChapter.value.id); const job = await pollJob(result.job.id); if (job.status !== "succeeded") throw new Error(job.error_message || "模型生成失败"); chapters.value = await listChapters(props.project.id); message.value = `已生成新版本 · ${modelName}`; } catch (e) { error.value = e instanceof Error ? e.message : "模型生成失败"; } finally { busy.value = ""; } }
async function check() { try { const result = await runChecks(props.project.id); issues.value = result.issues; message.value = result.status === "passed" ? "确定性检查完成" : `发现 ${result.issues.length} 项待处理问题`; } catch (e) { error.value = String(e); } }
async function exportDocx() { try { const record = await createExport(props.project.id); const anchor = document.createElement("a"); anchor.href = downloadExport(record.id); anchor.download = "技术标审核稿.docx"; anchor.click(); message.value = `审核稿已导出 · 页数${record.page_count}`; } catch (e) { error.value = String(e); } }
async function saveKnowledge() { if (!knowledgeTitle.value.trim() || !knowledgeBody.value.trim() || !knowledgeSource.value.trim()) return; await addKnowledge({ kind: knowledgeKind.value, title: knowledgeTitle.value, body: knowledgeBody.value, source: knowledgeSource.value }); knowledgeTitle.value = ""; knowledgeBody.value = ""; knowledgeSource.value = ""; knowledge.value = await listKnowledge(); }
</script>

<template>
  <section class="workspace">
    <div class="section-title"><div><p class="eyebrow">{{ project.code }} · {{ project.engineering_type === "building" ? "建筑工程" : "市政工程" }}</p><h2>{{ project.name }}</h2></div><button type="button" class="secondary" @click="$emit('back')">返回项目列表</button></div>
    <nav class="workspace-tabs"><button v-for="tab in tabs" :key="tab" type="button" :class="{ selected: activeTab === tab }" @click="activeTab = tab">{{ tab }}</button></nav>
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="message" class="notice" role="status">{{ message }}</p><p v-if="busy" class="notice">{{ busy }}</p>

    <section v-if="activeTab === '资料与事实'" class="workspace-section"><div class="section-title"><h3>招标资料</h3><button type="button" @click="extract">从已解析资料提取事实与要求</button></div><DocumentUpload :project-id="project.id" @updated="onDocument" /><p class="muted">完整资料包会递归解包。清单和图纸读取结果请在“固定事实库”核对并发布。</p><table class="data-table"><thead><tr><th>文件与来源</th><th>解析状态</th><th>文字片段</th><th>操作</th></tr></thead><tbody><tr v-for="doc in documents" :key="doc.id"><td><details><summary>{{ doc.filename }}</summary><p style="overflow-wrap:anywhere">{{ doc.archive_path }}</p><p v-if="doc.error_message" class="error">{{ doc.error_message }}</p></details></td><td>{{ doc.status }}</td><td>{{ doc.block_count ?? doc.blocks.length }}</td><td><button type="button" @click="parseDocument(doc.id).then(load)">重新解析</button></td></tr><tr v-if="!documents.length"><td colspan="4" class="muted">尚未上传文件</td></tr></tbody></table><h3>项目事实确认</h3><p class="muted">确认后的修改进入草稿，发布新事实版本后才用于 AI 写作。</p><FactTable :project-id="project.id" :facts="facts" @changed="load" /></section>

    <section v-else-if="activeTab === '固定事实库'" class="workspace-section"><FactLibraryPanel :project-id="project.id" @published="snapshot = $event" /></section>

    <section v-else-if="activeTab === '要求与目录'" class="workspace-section"><h3>编制要求</h3><form class="inline-form" @submit.prevent="saveRequirements"><input v-model="requirementText" placeholder="添加一项招标要求" /><button type="submit">添加要求</button></form><RequirementTable :requirements="requirements" /><div class="section-title"><h3>章节目录</h3><div><button type="button" class="secondary" @click="addOutlineItem">添加章节</button> <button type="button" @click="saveOutlineAction">保存目录</button></div></div><OutlineEditor :outline="outline" /><button type="button" class="secondary" @click="createOutlineChapters">按目录创建章节</button></section>

    <section v-else-if="activeTab === '章节工作区'" class="workspace-section"><div class="section-title"><div><h3>章节正文</h3><p class="muted">生成模型：{{ modelName }} · {{ snapshot ? `固定事实库 v${snapshot.version}` : '请先核对并发布固定事实库' }}</p></div><button type="button" :disabled="!currentChapter || !!busy || !snapshot" @click="generate">生成当前章节</button></div><ChapterEditor v-if="currentChapter" :key="currentChapter.id + currentChapter.versions.length" :chapter="currentChapter" @saved="onSaved" /><p v-else class="muted">请先在目录页按目录创建章节</p><div v-if="chapters.length > 1" class="chapter-list"><button v-for="chapter in chapters" :key="chapter.id" type="button" @click="chapters = [chapter, ...chapters.filter((item) => item.id !== chapter.id)]">{{ chapter.title }}{{ chapter.stale ? " · 待复核" : "" }}</button></div></section>

    <section v-else-if="activeTab === '案例规范'" class="workspace-section"><h3>案例与规范资料</h3><p class="muted">导入记录默认待核验；基础关键词检索可用，向量检索与规范现行性核验未接入。</p><form class="knowledge-form" @submit.prevent="saveKnowledge"><select v-model="knowledgeKind"><option value="case">案例</option><option value="standard">规范</option></select><input v-model="knowledgeTitle" placeholder="资料名称" required /><input v-model="knowledgeSource" placeholder="来源" required /><textarea v-model="knowledgeBody" placeholder="资料正文或条文摘录" required rows="4" /><button type="submit">登记资料</button></form><KnowledgePanel :items="knowledge" /></section>

    <section v-else class="workspace-section"><div class="section-title"><h3>检查与导出</h3><div><button type="button" class="secondary" @click="check">运行确定性检查</button> <button type="button" @click="exportDocx">导出可编辑 DOCX</button></div></div><p class="muted">语义审查、工程计算和实际分页尚未接入。导出文件为审核稿，页数未验证。</p><IssueList :issues="issues" /></section>
  </section>
</template>

