<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">系统用户管理</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon> 添加用户
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchKeyword" placeholder="搜索用户名/姓名" style="width: 200px" clearable @change="handleSearch" />
      <el-select v-model="filterStatus" placeholder="用户状态" style="width: 120px" clearable @change="handleSearch">
        <el-option label="启用" value="1" />
        <el-option label="禁用" value="0" />
      </el-select>
    </div>

    <div class="table-container">
      <el-table :data="userList" v-loading="loading" style="width: 100%">
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getRoleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '1' ? 'success' : 'info'" size="small">{{ row.status === '1' ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="primary" link size="small" @click="handleResetPwd(row)">重置密码</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="运维人员" value="operator" />
            <el-option label="访客" value="guest" />
          </el-select>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { user } from '@/api'
import { formatTime } from '@/utils/date'

const loading = ref(false)
const searchKeyword = ref('')
const filterStatus = ref('')
const userList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('添加用户')
const formRef = ref(null)

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, username: '', name: '', email: '', phone: '', role: '', status: '1' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

onMounted(() => { loadData() })

const loadData = async () => {
  loading.value = true
  try {
    const res = await user.getList({ page: pagination.page, page_size: pagination.pageSize, keyword: searchKeyword.value, status: filterStatus.value }).catch(() => ({ items: [], total: 0 }))
    userList.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) { console.error('Load users error:', error) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; loadData() }
const getRoleText = (r) => ({ admin: '管理员', operator: '运维人员', guest: '访客' }[r] || r)

const handleAdd = () => { dialogTitle.value = '添加用户'; Object.assign(form, { id: null, username: '', name: '', email: '', phone: '', role: '', status: '1' }); dialogVisible.value = true }
const handleEdit = (row) => { dialogTitle.value = '编辑用户'; Object.assign(form, { id: row.id, username: row.username, name: row.name, email: row.email, phone: row.phone, role: row.role, status: row.status }); dialogVisible.value = true }

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除用户 "${row.username}" 吗?`, '提示', { type: 'warning' })
    .then(async () => { try { await user.delete(row.id); ElMessage.success('删除成功'); loadData() } catch (error) { console.error('Delete error:', error) } }).catch(() => {})
}

const handleResetPwd = (row) => {
  ElMessageBox.confirm(`确定重置用户 "${row.username}" 的密码吗?`, '提示', { type: 'warning' })
    .then(async () => { try { await user.resetPassword(row.id); ElMessage.success('密码已重置为: 123456') } catch (error) { console.error('Reset password error:', error) } }).catch(() => {})
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (form.id) { await user.update(form.id, form); ElMessage.success('更新成功') }
    else { await user.create(form); ElMessage.success('创建成功') }
    dialogVisible.value = false; loadData()
  } catch (error) { console.error('Submit error:', error) }
}
</script>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #fff; border-radius: 8px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
:deep(.el-table .el-table__header th) { background: #f7f8fa; }
</style>
