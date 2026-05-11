<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">菜单管理</h1>
        <p class="page-subtitle">系统菜单和权限管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd(null)">
          <el-icon><Plus /></el-icon> 添加菜单
        </el-button>
      </div>
    </div>

    <div class="table-container">
      <el-table :data="menuList" v-loading="loading" style="width: 100%" row-key="id" :tree-props="{ children: 'children' }">
        <el-table-column prop="name" label="菜单名称" min-width="180" />
        <el-table-column prop="icon" label="图标" width="100">
          <template #default="{ row }">
            <el-icon v-if="row.icon"><component :is="row.icon" /></el-icon>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路由路径" min-width="200" />
        <el-table-column prop="component" label="组件路径" min-width="200" />
        <el-table-column prop="sort" label="排序" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '1' ? 'success' : 'info'" size="small">{{ row.status === '1' ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleAdd(row)">添加子菜单</el-button>
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="上级菜单">
          <el-tree-select v-model="form.parent_id" :data="treeData" placeholder="请选择上级菜单" clearable check-strictly style="width: 100%" />
        </el-form-item>
        <el-form-item label="菜单名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入菜单名称" />
        </el-form-item>
        <el-form-item label="菜单图标">
          <el-input v-model="form.icon" placeholder="请输入图标名称" />
        </el-form-item>
        <el-form-item label="路由路径" prop="path">
          <el-input v-model="form.path" placeholder="请输入路由路径" />
        </el-form-item>
        <el-form-item label="组件路径">
          <el-input v-model="form.component" placeholder="请输入组件路径" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="1">启用</el-radio>
            <el-radio value="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { menu } from '@/api'

const loading = ref(false)
const menuList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('添加菜单')
const formRef = ref(null)

const form = reactive({ id: null, parent_id: null, name: '', icon: '', path: '', component: '', sort: 0, status: '1' })
const rules = {
  name: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }],
  path: [{ required: true, message: '请输入路由路径', trigger: 'blur' }],
  sort: [{ required: true, message: '请输入排序', trigger: 'blur' }]
}

const treeData = computed(() => [{ id: 0, label: '顶级菜单', children: menuList.value.map(m => ({ id: m.id, label: m.name })) }])

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await menu.getList().catch(() => [])
    menuList.value = res || []
  } catch (error) { console.error('Load menus error:', error) }
  finally { loading.value = false }
}

const handleAdd = (parent) => {
  dialogTitle.value = '添加菜单'
  Object.assign(form, { id: null, parent_id: parent?.id || null, name: '', icon: '', path: '', component: '', sort: 0, status: '1' })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑菜单'
  Object.assign(form, { id: row.id, parent_id: row.parent_id, name: row.name, icon: row.icon, path: row.path, component: row.component, sort: row.sort, status: row.status })
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除菜单 "${row.name}" 吗?`, '提示', { type: 'warning' })
    .then(async () => {
      try { await menu.delete(row.id); ElMessage.success('删除成功'); loadData() }
      catch (error) { console.error('Delete error:', error) }
    }).catch(() => {})
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await menu.update(form.id, form); ElMessage.success('更新成功') }
    else { await menu.create(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>

<style lang="scss" scoped>
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
