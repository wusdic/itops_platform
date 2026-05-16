<template>
  <div class="page-container">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">分类管理</h1>
        <p class="page-subtitle">管理SOP文档和故障案例的分类目录</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAddTop">
          <el-icon><Plus /></el-icon> 新建分类
        </el-button>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-bar">
      <span>文档总数: <strong>{{ stats.total_documents || 0 }}</strong></span>
      <span class="divider">|</span>
      <span>SOP: <strong>{{ stats.sop_count || 0 }}</strong></span>
      <span class="divider">|</span>
      <span>故障案例: <strong>{{ stats.fault_case_count || 0 }}</strong></span>
      <span class="divider">|</span>
      <span>分类: <strong>{{ stats.category_count || 0 }}</strong></span>
    </div>

    <!-- Main Content -->
    <div class="content-wrapper">
      <!-- Left: Category Tree -->
      <div class="tree-panel">
        <div class="panel-title">分类树</div>
        <el-tree
          ref="treeRef"
          :data="treeData"
          :props="{ label: 'name', children: 'children' }"
          node-key="id"
          :expand-on-click-node="false"
          :default-expand-all="true"
          highlight-current
          @node-click="handleNodeClick"
        >
          <template #default="{ node, data }">
            <span class="tree-node">
              <span class="node-label">{{ node.label }}</span>
              <span class="node-type">
                <el-tag v-if="data.doc_type === 'sop'" size="small" type="success">SOP</el-tag>
                <el-tag v-else-if="data.doc_type === 'fault_case'" size="small" type="warning">故障</el-tag>
              </span>
            </span>
          </template>
        </el-tree>
      </div>

      <!-- Right: Detail Panel -->
      <div class="detail-panel">
        <div class="panel-title">分类详情</div>
        <template v-if="selectedCategory">
          <div class="detail-info">
            <div class="detail-row">
              <span class="detail-label">名称:</span>
              <span class="detail-value">{{ selectedCategory.name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">编码:</span>
              <span class="detail-value">{{ selectedCategory.code || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">上级:</span>
              <span class="detail-value">{{ getParentName(selectedCategory) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">类型:</span>
              <span class="detail-value">
                <el-tag v-if="selectedCategory.doc_type === 'sop'" type="success">SOP文档</el-tag>
                <el-tag v-else-if="selectedCategory.doc_type === 'fault_case'" type="warning">故障案例</el-tag>
                <span v-else>-</span>
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">文档数:</span>
              <span class="detail-value">{{ selectedCategory.doc_count || 0 }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">描述:</span>
              <span class="detail-value">{{ selectedCategory.description || '-' }}</span>
            </div>
          </div>
          <div class="detail-actions">
            <el-button type="primary" @click="handleEdit">编辑分类</el-button>
            <el-button type="danger" @click="handleDelete">删除分类</el-button>
          </div>
          <div class="sub-action">
            <el-button @click="handleAddChild">新建子分类</el-button>
          </div>
        </template>
        <template v-else>
          <div class="empty-detail">请选择左侧分类查看详情</div>
        </template>
      </div>
    </div>

    <!-- Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" label-width="80px" :rules="rules" ref="formRef">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入分类编码" />
        </el-form-item>
        <el-form-item label="类型" prop="doc_type">
          <el-select v-model="form.doc_type" placeholder="请选择类型" style="width: 100%">
            <el-option label="SOP文档" value="sop" />
            <el-option label="故障案例" value="fault_case" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { knowledge } from '@/api'

const treeRef = ref(null)
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新建分类')
const treeData = ref([])
const selectedCategory = ref(null)
const stats = ref({})
const formRef = ref(null)

const form = reactive({
  id: null,
  name: '',
  code: '',
  parent_id: null,
  doc_type: 'sop',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  doc_type: [{ required: true, message: '请选择类型', trigger: 'change' }]
}

// Build tree structure from flat list
const buildTree = (items, parentId = null) => {
  return items
    .filter(item => item.parent_id === parentId)
    .map(item => ({
      ...item,
      children: buildTree(items, item.id)
    }))
}

const loadCategory = async () => {
  loading.value = true
  try {
    const res = await knowledge.getCategory()
    const items = res.items || []
    treeData.value = buildTree(items, null)
  } catch (error) {
    console.error('Load category error:', error)
    ElMessage.error('加载分类失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await knowledge.getStats()
    stats.value = res
  } catch (error) {
    console.error('Load stats error:', error)
  }
}

const handleNodeClick = (data) => {
  selectedCategory.value = data
}

const getParentName = (category) => {
  if (!category.parent_id) return '顶级'
  const findParent = (items, id) => {
    for (const item of items) {
      if (item.id === id) return item.name
      if (item.children?.length) {
        const found = findParent(item.children, id)
        if (found) return found
      }
    }
    return null
  }
  return findParent(treeData.value, category.parent_id) || '顶级'
}

const handleAddTop = () => {
  dialogTitle.value = '新建顶级分类'
  Object.assign(form, { id: null, name: '', code: '', parent_id: null, doc_type: 'sop', description: '' })
  dialogVisible.value = true
}

const handleAddChild = () => {
  if (!selectedCategory.value) {
    ElMessage.warning('请先选择父分类')
    return
  }
  dialogTitle.value = '新建子分类'
  Object.assign(form, { id: null, name: '', code: '', parent_id: selectedCategory.value.id, doc_type: selectedCategory.value.doc_type || 'sop', description: '' })
  dialogVisible.value = true
}

const handleEdit = () => {
  if (!selectedCategory.value) {
    ElMessage.warning('请先选择分类')
    return
  }
  dialogTitle.value = '编辑分类'
  Object.assign(form, {
    id: selectedCategory.value.id,
    name: selectedCategory.value.name,
    code: selectedCategory.value.code || '',
    parent_id: selectedCategory.value.parent_id,
    doc_type: selectedCategory.value.doc_type || 'sop',
    description: selectedCategory.value.description || ''
  })
  dialogVisible.value = true
}

const handleDelete = () => {
  if (!selectedCategory.value) {
    ElMessage.warning('请先选择分类')
    return
  }
  const hasChildren = treeData.value.some(item => item.id === selectedCategory.value.id && item.children?.length > 0) ||
    (selectedCategory.value.children && selectedCategory.value.children.length > 0)
  const hasDocs = selectedCategory.value.doc_count > 0

  let msg = `确定删除分类 "${selectedCategory.value.name}" 吗？`
  if (hasDocs) {
    msg = `该分类下有 ${selectedCategory.value.doc_count} 个文档，删除后无法恢复。\n\n` + msg
  } else if (hasChildren) {
    msg = `该分类下有子分类，删除后子分类也会被删除。\n\n` + msg
  }

  ElMessageBox.confirm(msg, '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    .then(async () => {
      try {
        // Using same API for delete - if not available, show message
        if (knowledge.deleteCategory) {
          await knowledge.deleteCategory(selectedCategory.value.id)
        } else {
          // API doesn't support delete, show warning
          ElMessage.warning('当前API不支持删除分类')
          return
        }
        ElMessage.success('删除成功')
        selectedCategory.value = null
        await loadCategory()
        await loadStats()
      } catch (error) {
        console.error('Delete error:', error)
        ElMessage.error('删除失败')
      }
    }).catch(() => {})
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    const data = {
      name: form.name,
      code: form.code || undefined,
      parent_id: form.parent_id || undefined,
      doc_type: form.doc_type,
      description: form.description || undefined
    }

    if (form.id) {
      // Update - check if API supports it
      if (knowledge.updateCategory) {
        await knowledge.updateCategory(form.id, data)
      } else {
        // Fallback: use create with id (some backends support this)
        try {
          await knowledge.createCategory({ ...data, id: form.id })
        } catch {
          ElMessage.warning('当前API不支持更新分类')
          return
        }
      }
      ElMessage.success('更新成功')
    } else {
      await knowledge.createCategory(data)
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    await loadCategory()
    await loadStats()
  } catch (error) {
    console.error('Submit error:', error)
    ElMessage.error(form.id ? '更新失败' : '创建失败')
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  loadCategory()
  loadStats()
})
</script>

<style lang="scss" scoped>
.page-container {
  padding: 20px;
  min-height: 100%;
  background: #f5f7fa;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 8px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.page-subtitle {
  margin: 4px 0 0;
  color: #909399;
  font-size: 13px;
}

.page-actions {
  display: flex;
  gap: 8px;
}

.stats-bar {
  margin-bottom: 16px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 8px;
  font-size: 14px;
  color: #606266;

  .divider {
    margin: 0 12px;
    color: #dcdfe6;
  }

  strong {
    color: #409eff;
  }
}

.content-wrapper {
  display: flex;
  gap: 16px;
  min-height: 500px;
}

.tree-panel {
  width: 300px;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  flex-shrink: 0;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.detail-panel {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;

  .node-label {
    flex: 1;
  }

  .node-type {
    margin-left: 8px;
  }
}

.empty-detail {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
  font-size: 14px;
}

.detail-info {
  margin-bottom: 20px;
}

.detail-row {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px solid #f5f7fa;

  &:last-child {
    border-bottom: none;
  }
}

.detail-label {
  width: 80px;
  color: #909399;
  font-size: 14px;
  flex-shrink: 0;
}

.detail-value {
  flex: 1;
  color: #303133;
  font-size: 14px;
}

.detail-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.sub-action {
  margin-top: 16px;
}

:deep(.el-tree) {
  background: transparent;

  .el-tree-node__content {
    height: 36px;
  }
}
</style>
