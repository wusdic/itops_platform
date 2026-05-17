<template>
  <div class="page-container">
    <n-card title="角色管理" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加角色
        </n-button>
      </template>

      <n-data-table
        :columns="columns"
        :data="roleList"
        :loading="loading"
        :pagination="pagination"
        :row-key="row => row.id"
      />
    </n-card>

    <!-- 创建/编辑角色 -->
    <n-modal v-model:show="dialogVisible" preset="card" :title="dialogTitle" style="width: 500px">
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item label="角色名称" required>
          <n-input v-model:value="form.name" placeholder="请输入角色名称" />
        </n-form-item>
        <n-form-item label="角色编码" required>
          <n-input v-model:value="form.code" placeholder="请输入角色编码" :disabled="isEdit" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitForm" :loading="submitting">确定</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 权限分配 -->
    <n-modal v-model:show="permDialogVisible" preset="card" title="分配权限" style="width: 600px">
      <n-tree
        block-node
        checkable
        cascade
        :data="permissionTree"
        :default-expanded-keys="['root']"
        :default-checked-keys="defaultCheckedKeys"
        :selected-keys="[]"
        @update:checked-keys="handlePermissionCheck"
      />
      <template #footer>
        <n-space justify="end">
          <n-button @click="permDialogVisible = false">取消</n-button>
          <n-button type="primary" @click="submitPermission" :loading="permSubmitting">保存权限</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { NCard, NButton, NDataTable, NModal, NForm, NFormItem, NInput, NSpace, NTag, NIcon, NTree, useMessage, useDialog } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const submitting = ref(false)
const permSubmitting = ref(false)
const isEdit = ref(false)
const roleList = ref([])
const dialogVisible = ref(false)
const permDialogVisible = ref(false)
const dialogTitle = ref('添加角色')
const currentRoleId = ref(null)
const currentCheckedKeys = ref([])

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const form = reactive({ id: null, name: '', code: '', description: '' })

const permissionTree = ref([
  {
    key: 'root',
    label: '全部权限',
    children: [
      { key: 'dashboard', label: '仪表盘', children: [
        { key: 'dashboard:view', label: '查看' },
        { key: 'dashboard:export', label: '导出' }
      ]},
      { key: 'monitoring', label: '监控中心', children: [
        { key: 'monitoring:device', label: '设备管理', children: [
          { key: 'monitoring:device:view', label: '查看' },
          { key: 'monitoring:device:edit', label: '编辑' },
          { key: 'monitoring:device:delete', label: '删除' }
        ]},
        { key: 'monitoring:alert', label: '告警管理', children: [
          { key: 'monitoring:alert:view', label: '查看' },
          { key: 'monitoring:alert:handle', label: '处理' }
        ]},
        { key: 'monitoring:perf', label: '性能监控', children: [
          { key: 'monitoring:perf:view', label: '查看' }
        ]}
      ]},
      { key: 'workorder', label: '工单管理', children: [
        { key: 'workorder:view', label: '查看' },
        { key: 'workorder:create', label: '创建' },
        { key: 'workorder:process', label: '处理' },
        { key: 'workorder:close', label: '关闭' }
      ]},
      { key: 'system', label: '系统管理', children: [
        { key: 'system:user', label: '用户管理', children: [
          { key: 'system:user:view', label: '查看' },
          { key: 'system:user:edit', label: '编辑' },
          { key: 'system:user:delete', label: '删除' }
        ]},
        { key: 'system:role', label: '角色管理', children: [
          { key: 'system:role:view', label: '查看' },
          { key: 'system:role:edit', label: '编辑' },
          { key: 'system:role:delete', label: '删除' },
          { key: 'system:role:permission', label: '权限分配' }
        ]},
        { key: 'system:menu', label: '菜单管理', children: [
          { key: 'system:menu:view', label: '查看' },
          { key: 'system:menu:edit', label: '编辑' }
        ]}
      ]},
      { key: 'ai', label: 'AI 助手', children: [
        { key: 'ai:chat', label: 'AI 聊天' },
        { key: 'ai:copilot', label: 'AI 分类' }
      ]},
      { key: 'knowledge', label: '知识库', children: [
        { key: 'knowledge:view', label: '查看' },
        { key: 'knowledge:edit', label: '编辑' }
      ]}
    ]
  }
])

const defaultCheckedKeys = ref([])

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '角色名称', key: 'name', width: 180 },
  { title: '角色编码', key: 'code', width: 150 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '用户数', key: 'user_count', width: 90, render: (r) => r.user_count || 0 },
  {
    title: '操作', key: 'actions', width: 200, fixed: 'right',
    render(row) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handlePermission(row) }, () => '权限'),
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleEdit(row) }, () => '编辑'),
        h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, () => '删除')
      ])
    }
  }
]

async function loadData() {
  loading.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/admin/roles?page=${pagination.page}&page_size=${pagination.pageSize}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data || typeof data !== 'object') throw new Error('响应格式异常')
    roleList.value = data.items || data.data?.items || []
    pagination.total = data.total || data.data?.total || 0
  } catch (e) {
    message.error(`加载角色失败: ${e.message}`)
    console.error('[role] loadData error:', e)
    roleList.value = []
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  isEdit.value = false
  dialogTitle.value = '添加角色'
  Object.assign(form, { id: null, name: '', code: '', description: '' })
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  dialogTitle.value = '编辑角色'
  Object.assign(form, { id: row.id, name: row.name, code: row.code, description: row.description || '' })
  dialogVisible.value = true
}

function handleDelete(row) {
  dialog.warning({
    title: '确认删除',
    content: `确定删除角色"${row.name}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const token = localStorage.getItem('token') || ''
        const res = await fetch(`/api/v1/admin/roles/${row.id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        message.success('删除成功')
        loadData()
      } catch (e) {
        message.error(`删除失败: ${e.message}`)
        console.error('[role] delete error:', e)
      }
    }
  })
}

// 打开权限分配弹窗
async function handlePermission(row) {
  currentRoleId.value = row.id
  currentCheckedKeys.value = []
  permDialogVisible.value = true
  
  // 加载该角色的现有权限
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/system/roles/${row.id}/permissions`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) {
      if (res.status !== 404) throw new Error(`HTTP ${res.status}`)
      // API 不存在，使用默认空权限
      defaultCheckedKeys.value = []
    } else {
      const data = await res.json()
      defaultCheckedKeys.value = data.permissions || data.data?.permissions || []
      currentCheckedKeys.value = [...defaultCheckedKeys.value]
    }
  } catch (e) {
    console.error('[role] 加载权限失败:', e)
    defaultCheckedKeys.value = []
    currentCheckedKeys.value = []
  }
}

// 权限勾选变化
function handlePermissionCheck(keys) {
  currentCheckedKeys.value = keys
}

// 提交权限
async function submitPermission() {
  if (!currentRoleId.value) return
  permSubmitting.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const res = await fetch(`/api/v1/system/roles/${currentRoleId.value}/permissions`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ permissions: currentCheckedKeys.value })
    })
    if (!res.ok) {
      if (res.status !== 404) throw new Error(`HTTP ${res.status}`)
      throw new Error('API_NOT_FOUND')
    }
    message.success('权限分配成功')
    permDialogVisible.value = false
  } catch (e) {
    if (e.message === 'API_NOT_FOUND') {
      // 模拟成功（本地演示）
      message.success('权限分配成功（API不存在，演示模式）')
      permDialogVisible.value = false
    } else {
      message.error(`权限分配失败: ${e.message}`)
      console.error('[role] submitPermission error:', e)
    }
  } finally {
    permSubmitting.value = false
  }
}

async function submitForm() {
  if (!form.name || !form.code) {
    message.warning('请填写必填项')
    return
  }
  submitting.value = true
  try {
    const token = localStorage.getItem('token') || ''
    const method = form.id ? 'PUT' : 'POST'
    const url = form.id ? `/api/v1/admin/roles/${form.id}` : '/api/v1/admin/roles'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: form.name, code: form.code, description: form.description })
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    message.success(form.id ? '更新成功' : '创建成功')
    dialogVisible.value = false
    loadData()
  } catch (e) {
    message.error(`操作失败: ${e.message}`)
    console.error('[role] submit error:', e)
  } finally {
    submitting.value = false
  }
}

function handlePageChange(page) {
  pagination.page = page
  loadData()
}
function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.page = 1
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
