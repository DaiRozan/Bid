<script setup lang="ts">
import type { ReviewIssue } from "../api/reviews";
defineProps<{ issues: ReviewIssue[] }>();
</script>
<template><ul class="issues"><li v-for="issue in issues" :key="issue.id"><strong>{{ issue.code }}</strong> {{ issue.message }} <span>{{ issue.severity }}</span></li><li v-if="!issues.length" class="muted">当前没有已记录问题</li></ul></template>

