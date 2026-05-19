<template>
  <div class="page-container">
    <n-card title="用户管理" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加用户
        </n-button>
      </template>

      <n-space style="margin-bottom: 12px" align="center">
        <n-input v-model:value="searchKeyword" placeholder="搜索用户名/姓名" clearable style="width: 200px" @input="handleSearchInput">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="filterStatus" :options="statusOptions" placeholder="用户状态" clearable style="width: 120px" @update:value="debouncedSearch" />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="userList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 新建/编辑用户 -->
    <n-modal v-model:show="dialogVisible" preset="card" :title="dialogTitle" style="width: 600px">
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item label="用户名" required>
          <n-input v-model:value="form.username" placeholder="请输入用户名" :disabled="!!form.id" />
        </n-form-item>
        <n-form-item v-if="!form.id" label="密码">
          <n-input
            v-model:value="form.password"
            type="password"
            placeholder="请输入密码"
            show-password-on="click"
          />
        </n-form-item>
        <n-form-item label="姓名">
          <n-input v-model:value="form.full_name" placeholder="请输入姓名" />
        </n-form-item>
        <n-form-item label="邮箱">
          <n-input v-model:value="form.email" placeholder="请输入邮箱" />
        </n-form-item>
        <n-form-item label="手机号">
          <n-input v-model:value="form.phone" placeholder="请输入手机号" />
        </n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="form.role" :options="roleOptions" placeholder="请选择角色" style="width: 100%" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitForm" :loading="submitting">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NSpace, NTag, NIcon, useMessage } from 'naive-ui'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const userList = ref([])
const searchKeyword = ref('')
const filterStatus = ref(null)
const dialogVisible = ref(false)
const dialogTitle = ref('添加用户')

let searchTimer = null
function handleSearchInput() {
  // 实时筛选，立即清空旧定时器，每次输入都重新开始计时
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pagination.page = 1
    loadData()
  }, 300)
}

function debouncedSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pagination.page = 1
    loadData()
  }, 300)
}

// 手机号格式校验
function validatePhone(phone) {
  if (!phone) return true
  return /^1[3-9]\d{9}$/.test(phone)
}

// 邮箱格式校验
function validateEmail(email) {
  if (!email) return true
  return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)
}

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, username: '', password: '', full_name: '', email: '', phone: '', role: null })

const statusOptions = [
  { label: '全部', value: null },
  { label: '启用', value: '1' },
  { label: '禁用', value: '0' }
]

const roleOptions = ref([
  { label: '管理员', value: 'admin' },
  { label: '运维人员', value: 'operator' },
  { label: '访客', value: 'guest' }
])

async function loadRoles() {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch('/api/v1/admin/roles', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) return
    const data = await res.json()
    const items = data.items || data.data?.items || []
    roleOptions.value = items.map(r => ({ label: r.name, value: r.code }))
  } catch (e) {
    console.warn('loadRoles failed, using defaults:', e)
  }
}

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '用户名', key: 'username', width: 150 },
  { title: '姓名', key: 'full_name', width: 120 },
  { title: '邮箱', key: 'email', width: 180 },
  { title: '手机号', key: 'phone', width: 130 },
  { title: '角色', key: 'role', width: 120,
    render: (r) => {
      const map = { admin: '管理员', operator: '运维人员', guest: '访客' }
      return h(NTag, { size: 'small', type: 'info' }, () => map[r.role] || r.role || '-')
    }
  },
  { title: '状态', key: 'is_active', width: 100,
    render: (r) => h(NTag, { size: 'small', type: r.is_active ? 'success' : 'default' }, () => r.is_active ? '启用' : '禁用')
  },
  { title: '创建时间', key: 'created_at', width: 180 },
  {
    title: '操作', key: 'actions', width: 240, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 12 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleEdit(row) }, () => '编辑'),
        h(NButton, { size: 'small', quaternary: true, type: 'warning', onClick: () => handleResetPwd(row) }, () => '重置密码'),
        h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, () => '删除')
      ])
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const params = new URLSearchParams({ page: pagination.page, page_size: pagination.pageSize })
    if (filterStatus.value) params.append('status', filterStatus.value)
    if (searchKeyword.value) params.append('search', searchKeyword.value)
    const res = await fetch(`/api/v1/admin/users?${params}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    userList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载用户失败: ${e.message}`)
    console.error('[user] loadData error:', e)
    userList.value = []
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  dialogTitle.value = '添加用户'
  Object.assign(form, { id: null, username: '', password: '', full_name: '', email: '', phone: '', role: null })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑用户'
  Object.assign(form, { id: row.id, username: row.username, password: '', full_name: row.full_name || '', email: row.email || '', phone: row.phone || '', role: row.role || null })
  dialogVisible.value = true
}

async function handleResetPwd(row) {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/admin/users/${row.id}/reset-password`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    message.success('密码已重置，请查看系统通知或联系管理员')
  } catch (e) {
    message.error(`重置失败: ${e.message}`)
  }
}

async function handleDelete(row) {
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/admin/users/${row.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error(`删除失败: ${e.message}`)
    console.error('[user] delete error:', e)
  }
}

async function submitForm() {
  if (!form.username) {
    message.warning('请填写用户名')
    return
  }
  if (form.email && !validateEmail(form.email)) {
    message.warning('邮箱格式不正确')
    return
  }
  if (form.phone && !validatePhone(form.phone)) {
    message.warning('手机号格式不正确')
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const method = form.id ? 'PUT' : 'POST'
    const url = form.id ? `/api/v1/admin/users/${form.id}` : '/api/v1/admin/users'
    const body = { username: form.username, full_name: form.full_name, email: form.email, phone: form.phone, role: form.role }
    if (form.password) body.password = form.password
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body)
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success(form.id ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadData()
  } catch (e) {
    message.error(`操作失败: ${e.message}`)
    console.error('[user] submit error:', e)
  } finally {
    submitting.value = false
  }
}

onMounted(() => { loadData(); loadRoles() })
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
