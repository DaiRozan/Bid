<script setup lang="ts">
import { onMounted, ref } from "vue";
import SiteAnalysisDialog from './SiteAnalysisDialog.vue';
import { adoptLibraryFact, getLibrary, getLibraryFile, getSnapshot, publishLibrary, type LibraryDraft, type LibraryEntry, type Snapshot } from "../api/factLibrary";

const props = defineProps<{ projectId: string }>();
const emit = defineEmits<{ published: [Snapshot] }>();
const draft = ref<LibraryDraft | null>(null);
const current = ref<Snapshot | null>(null);
const section = ref("facts"); const search = ref(""); const offset = ref(0);
const busy = ref(""); const error = ref(""); const notice = ref(""); const acknowledged = ref(false);
const editing = ref<LibraryEntry | null>(null); const value = ref(""); const reason = ref("");
const evidence = ref<LibraryEntry | null>(null); const preview = ref(""); const fileName = ref("采用事实.md"); const publishedFiles = ref(false);
function visibleFile(name: string) { return name === "采用事实.md" || name === "现场条件与施工影响.md" || name === "待处理事项.md" || name.startsWith("清单/"); }
async function load() {
  busy.value = "正在读取事实库"; error.value = "";
  try { [draft.value, current.value] = await Promise.all([getLibrary(props.projectId, section.value, search.value, offset.value), getSnapshot(props.projectId)]); }
  catch (e) { error.value = e instanceof Error ? e.message : String(e); }
  finally { busy.value = ""; }
}
onMounted(load);
async function changeSection(next: string) { section.value = next; offset.value = 0; await load(); }
function edit(entry: LibraryEntry) { editing.value = entry; value.value = String(entry.value ?? ""); reason.value = ""; }
async function save() {
  if (!editing.value) return;
  const sources = evidence.value?.source_block_ids || editing.value.source_block_ids || [];
  if (!sources.length) { error.value = "请先在原文与图纸复核中选择本次采用值的来源依据"; return; }
  busy.value = "正在登记采用值";
  try { await adoptLibraryFact(props.projectId, editing.value.id, value.value, reason.value, sources); editing.value = null; notice.value = "已保存到草稿，发布新版本后才会用于写作"; await load(); }
  catch (e) { error.value = e instanceof Error ? e.message : String(e); busy.value = ""; }
}
async function publish() {
  busy.value = "正在发布固定版本"; error.value = "";
  try { current.value = await publishLibrary(props.projectId, acknowledged.value); emit("published", current.value); notice.value = `固定事实版本 v${current.value.version} 已发布`; }
  catch (e) { error.value = e instanceof Error ? e.message : String(e); }
  finally { busy.value = ""; }
}
async function showFile() {
  busy.value = "正在读取 Markdown";
  try { preview.value = (await getLibraryFile(props.projectId, fileName.value, publishedFiles.value)).content; }
  catch (e) { error.value = e instanceof Error ? e.message : String(e); }
  finally { busy.value = ""; }
}
</script>

<template>
  <section class="fact-library">
    <div class="section-title"><div><h3>项目事实库</h3><p class="muted">{{ current ? `已固定 v${current.version} · ${current.fact_count} 条采用事实` : "尚未发布固定版本，AI 章节生成暂不可用" }}</p></div><button class="secondary" :disabled="!!busy" @click="load">刷新资料与事实</button></div>
    <p>采用最新明确补疑及工程量清单的数量，图纸计算用于复核。修改先进入草稿，发布新版本后生效。</p>
    <SiteAnalysisDialog :project-id="projectId" @adopted="load" />
    <p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" class="notice" role="status">{{ notice }}</p><p v-if="busy" class="notice">{{ busy }}</p>
    <template v-if="draft">
      <div class="library-overview"><span>采用事实 {{ draft.fact_count }}</span><span>图纸明细已后台归档</span><span>待处理事项 {{ draft.issues.length }}</span></div>
      <details v-if="draft.issues.length"><summary>查看待处理事项与图纸读取限制</summary><ul><li v-for="(issue, i) in draft.issues" :key="i">{{ issue.message }}</li></ul></details>
      <div class="library-actions"><button :class="{secondary: section !== 'facts'}" @click="changeSection('facts')">采用事实</button><button :class="{secondary: section !== 'review'}" @click="changeSection('review')">补疑与待确认事实</button></div>
      <form class="inline-form" @submit.prevent="offset = 0; load()"><input v-model="search" placeholder="按单位工程、项目名称、图纸文字搜索" aria-label="搜索项目事实" /><button :disabled="!!busy">搜索</button></form>
      <p v-if="evidence" class="notice">当前修改依据：{{ evidence.field_name }} · {{ String(evidence.value).slice(0,160) }} <button class="secondary" @click="evidence = null">清除依据</button></p>
      <div class="library-entries"><article v-for="entry in (section === 'facts' ? draft.facts : draft.review)" :key="entry.id" class="library-entry">
        <strong>{{ entry.field_name || entry.name || ({area:'闭合图形面积',length:'图形长度',volume:'明确参数体积',count:'块实例数量'}[entry.type || ''] || '图纸测量') }}</strong>
        <p class="preserve-lines">{{ entry.value }} {{ entry.type ? entry.unit : '' }}</p>
        <p v-if="entry.formula" class="muted">计算依据：{{ entry.formula }}；待复核，不能直接作为清单工程量</p>
        <details><summary>来源位置</summary><p class="source-path">{{ entry.archive_path || '人工确认的项目事实' }}</p><pre>{{ entry.location }}</pre></details>
        <div v-if="section === 'facts' || entry.adoptable" class="library-actions"><button class="secondary" @click="edit(entry)">{{ section === 'facts' ? '修改采用值' : '核对并采用此条' }}</button><button v-if="section === 'review'" class="secondary" @click="evidence = entry">设为修改依据</button></div>
      </article><p v-if="!draft.filtered_count" class="muted">没有符合条件的条目</p></div>
      <div class="library-actions"><button class="secondary" :disabled="offset === 0 || !!busy" @click="offset -= 50; load()">上一页</button><span>{{ offset + 1 }}–{{ Math.min(offset + 50, draft.filtered_count) }} / {{ draft.filtered_count }}</span><button class="secondary" :disabled="offset + 50 >= draft.filtered_count || !!busy" @click="offset += 50; load()">下一页</button></div>
      <form v-if="editing" class="library-edit" @submit.prevent="save"><h4>{{ editing.field_name }} · 采用值</h4><textarea v-model="value" rows="5" required aria-label="采用值" /><input v-model="reason" placeholder="填写采用或修改原因，例如明确补疑条款" required aria-label="采用原因" /><p class="muted">{{ evidence ? '使用当前已选修改依据' : '使用本条原始来源；采用补疑修改时，请先选择补疑条款作为依据' }}</p><div class="library-actions"><button :disabled="!!busy">保存到草稿</button><button type="button" class="secondary" @click="editing = null">取消</button></div></form>
      <div class="library-publication"><label v-if="draft.issues.length"><input type="checkbox" v-model="acknowledged" /> 我已核对待处理事项，未确认的原文和图纸测量不作为写作采用值</label><button :disabled="!!busy || !draft.fact_count || (draft.issues.length > 0 && !acknowledged)" @click="publish">发布{{ current ? '新' : '首个' }}固定版本</button></div>
      <details><summary>查看事实库 Markdown 文件</summary><div class="library-actions"><label><input type="checkbox" v-model="publishedFiles" :disabled="!current" /> 查看已发布版本</label><select v-model="fileName" aria-label="选择事实库文件"><option v-for="name in (publishedFiles ? current?.files.filter(n => visibleFile(n)) : draft.files.filter(n => visibleFile(n)))" :key="name" :value="name">{{ draft.file_labels[name] || name }}</option></select><button class="secondary" :disabled="!!busy" @click="showFile">读取文件</button></div><pre v-if="preview" class="markdown-preview">{{ preview }}</pre></details>
    </template>
  </section>
</template>

<style scoped>
.library-overview,.library-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:16px 0}.library-overview span{padding:8px 12px;background:#eef4f1;border-radius:6px}.library-entry{padding:16px 0;border-bottom:1px solid #dce4df}.preserve-lines,.source-path{white-space:pre-wrap;overflow-wrap:anywhere}.library-entries{max-height:650px;overflow:auto}.library-edit{margin:20px 0;padding:18px;background:#f1f5f2;border:1px solid #d2ddd5;border-radius:8px}.library-edit textarea,.library-edit input{display:block;width:100%;box-sizing:border-box;margin:10px 0}.library-publication{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:24px 0;padding-top:18px;border-top:1px solid #dce4df}.markdown-preview{white-space:pre-wrap;overflow-wrap:anywhere;max-height:600px;overflow:auto;background:#f5f7f5;padding:16px}details{margin:12px 0}summary{cursor:pointer}select{max-width:60%;padding:8px}
</style>