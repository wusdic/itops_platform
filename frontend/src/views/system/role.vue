<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">角色管理</h1>
        <p class="page-subtitle">系统角色和权限管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加角色
        </el-button>
      </div>
    </div>

    <div class="table-container">
      <el-table :data="roleList" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="角色名称" width="180" />
        <el-table-column prop="code" label="角色编码" width="150" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '1' ? 'success' : 'info'" size="small">{{ row.status === '1' ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handlePermission(row)">权限</el-button>
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入角色名称" />
        </el-form-item>
        <el-form-item label="角色编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入角色编码" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入描述" />
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

    <el-dialog v-model="permissionDialogVisible" title="分配权限" width="600px">
      <el-tree ref="permissionTreeRef" :data="permissionTree" show-checkbox node-key="id" :props="{ label: 'name', children: 'children' }" default-expand-all />
      <template #footer>
        <el-button @click="permissionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPermission">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { role, menu } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const roleList = ref([])
const dialogVisible = ref(false)
const permissionDialogVisible = ref(false)
const dialogTitle = ref('添加角色')
const formRef = ref(null)
const permissionTree = ref([])
const currentRoleId = ref(null)
const permissionTreeRef = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', code: '', description: '', status: '1' })
const rules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }]
}

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await role.getList({ page: pagination.page, page_size: pagination.pageSize }).catch(() => ({ items: [], total: 0 }))
    roleList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load roles error:', error) }
  finally { loading.value = false }
}

const handleAdd = () => { dialogTitle.value = '添加角色'; Object.assign(form, { id: null, name: '', code: '', description: '', status: '1' }); dialogVisible.value = true }
const handleEdit = (row) => { dialogTitle.value = '编辑角色'; Object.assign(form, { id: row.id, name: row.name, code: row.code, description: row.description, status: row.status }); dialogVisible.value = true }

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除角色 "${row.name}" 吗?`, '提示', { type: 'warning' })
    .then(async () => { try { await role.delete(row.id); ElMessage.success('删除成功'); loadData() } catch (error) { console.error('Delete error:', error) } }).catch(() => {})
}

const handlePermission = async (row) => {
  currentRoleId.value = row.id
  try {
    const [menuRes, permRes] = await Promise.all([
      menu.getList().catch(() => []),
      role.getPermissions(row.id).catch(() => [])
    ])
    permissionTree.value = menuRes || []
    await nextTick()
    if (permRes && permRes.length > 0) {
      const checkedKeys = permRes.map(p => p)
      checkedKeys.forEach(key => {
        permissionTreeRef.value?.setChecked(key, true, false)
      })
    }
  } catch (e) { console.error(e) }
  permissionDialogVisible.value = true
}

const submitPermission = async () => {
  try {
    const checkedNodes = permissionTreeRef.value?.getCheckedNodes(false, true) || []
    const permissionIds = checkedNodes.map(node => node.id)
    await role.assignPermissions(currentRoleId.value, { permission_ids: permissionIds })
    ElMessage.success('权限分配成功')
    permissionDialogVisible.value = false
  } catch (error) { console.error('Submit permission error:', error) }
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await role.update(form.id, form); ElMessage.success('更新成功') }
    else { await role.create(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>

<style lang="scss" scoped>
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
