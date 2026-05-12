<template>
  <div class="knowledge-list-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>知识文档</span>
          <el-button type="primary" @click="loadDocs">刷新</el-button>
        </div>
      </template>
      <el-table :data="documents" stripe>
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="category" label="分类" />
        <el-table-column prop="updated_at" label="更新时间" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const documents = ref([])

const loadDocs = async () => {
  try {
    const res = await fetch('/api/knowledge')
    if (res.ok) documents.value = await res.json()
  } catch (e) { /* silent */ }
}

onMounted(loadDocs)
</script>

<style scoped>
.knowledge-list-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
