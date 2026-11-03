<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { apiRequest } from '../api/client';
type Evidence = {id:string; filename:string; text:string};
type Report = {id:string; summary:string; stale:boolean; created_at:string; findings:{title:string; observation:string; impact:string; recommendation:string; uncertainty:string; evidence:Evidence[]}[]; limitations:string[]};
const props = defineProps<{projectId:string}>();
const emit = defineEmits<{adopted:[]}>();
const opened=ref(false), busy=ref(false), error=ref(''), notice=ref(''), report=ref<Report|null>(null);
onMounted(async()=>{
  try { const response=await fetch(`/api/projects/${props.projectId}/site-analysis`); if(response.status===404)return; if(!response.ok)throw new Error('读取现场分析失败'); report.value=await response.json(); }
  catch(e){error.value=String(e);}
});
async function analyze(){
  busy.value=true; error.value=''; notice.value='';
  try {report.value=await apiRequest<Report>(`/projects/${props.projectId}/site-analysis`,{method:'POST'});}
  catch(e){error.value=e instanceof Error?e.message:String(e);}
  finally{busy.value=false;}
}
async function adopt(){
  busy.value=true; error.value='';
  try {await apiRequest(`/projects/${props.projectId}/site-analysis/adopt`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({analysis_id:report.value?.id})}); notice.value='已纳入事实草稿，发布新固定版本后供写作调用。'; emit('adopted');}
  catch(e){error.value=e instanceof Error?e.message:String(e);}
  finally{busy.value=false;}
}
</script>
<template>
  <div class="site-entry"><div><strong>现场条件与施工影响</strong><p class="muted">综合图纸证据分析周边、运输、排水、作业面和施工重难点，结果保存到本项目事实库。</p></div><button @click="opened=true">{{report?'查看图纸分析结果':'分析现场条件与施工影响'}}</button></div>
  <div v-if="opened" class="site-backdrop" @keydown.esc="opened=false">
    <section role="dialog" aria-modal="true" aria-labelledby="site-title" class="site-dialog" tabindex="-1">
      <header><h3 id="site-title">现场条件与施工影响分析</h3><button class="secondary" aria-label="关闭图纸分析" @click="opened=false">关闭</button></header>
      <p v-if="error" role="alert" class="error">{{error}}</p><p v-if="notice" role="status">{{notice}}</p>
      <p v-if="busy" role="status">正在处理图纸证据与分析结果，请稍候。可关闭对话框，完成后结果仍会保存。</p>
      <template v-if="report">
        <p v-if="report.stale" class="error">资料已变化，请重新分析。当前旧结果不能直接采用。</p>
        <p class="site-summary">{{report.summary}}</p><p class="muted">{{new Date(report.created_at).toLocaleString()}} · 分析判断，需核对现场条件</p>
        <article v-for="(item,i) in report.findings" :key="i"><h4>{{i+1}}. {{item.title}}</h4><p><b>图纸依据与现场条件：</b>{{item.observation}}</p><p><b>施工影响：</b>{{item.impact}}</p><p><b>应对建议：</b>{{item.recommendation}}</p><p class="muted"><b>待核实：</b>{{item.uncertainty}}</p><details><summary>查看本项出处</summary><p v-for="e in item.evidence" :key="e.id">{{e.filename}}（本项依据已在后台归档）</p></details></article>
        <details><summary>分析范围与待补资料</summary><ul><li v-for="item in report.limitations" :key="item">{{item}}</li></ul></details>
      </template>
      <p v-else>读取当前项目已解析图纸、坐标线形和有关文件，形成“现场条件—施工影响—建议—待核实事项”的分析。原始图纸明细保存在后台。</p>
      <footer><button :disabled="busy" @click="analyze">{{report?'重新分析当前资料':'开始分析'}}</button><button v-if="report" class="secondary" :disabled="busy||report.stale" @click="adopt">核对后纳入写作事实</button></footer>
    </section>
  </div>
</template>
<style scoped>
.site-entry{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px;background:#eef4f1;border-radius:8px;margin:16px 0}.site-entry p{margin-bottom:0}.site-backdrop{position:fixed;inset:0;background:#15271e80;display:flex;align-items:center;justify-content:center;z-index:1000;padding:20px}.site-dialog{background:#fff;border-radius:12px;padding:24px;max-width:900px;width:100%;max-height:85vh;overflow:auto;box-shadow:0 20px 80px #0004}.site-dialog header,.site-dialog footer{display:flex;align-items:center;justify-content:space-between;gap:16px}.site-dialog footer{position:sticky;bottom:-24px;background:white;padding:16px 0;margin-top:20px;justify-content:flex-start}.site-dialog article{border-top:1px solid #dce4df;padding:12px 0}.site-dialog p{line-height:1.75;white-space:pre-wrap;overflow-wrap:anywhere}.site-summary{font-size:1.1em;font-weight:600}summary{cursor:pointer}
</style>
