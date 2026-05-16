<template>
  <div>
    <div class="page-header">
      <h2>通知规则</h2>
    </div>

    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- 目标规则 -->
      <n-tab-pane name="rules" tab="目标规则">
        <div style="margin-bottom: 12px">
          <n-button type="primary" @click="openRuleCreate">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            新建规则
          </n-button>
          <n-button type="info" @click="openMatchTest" style="margin-left: 8px">
            <template #icon><n-icon><SearchOutline /></n-icon></template>
            匹配测试
          </n-button>
        </div>
        <n-card :bordered="false">
          <n-data-table
            :columns="ruleColumns"
            :data="rules"
            :loading="loading"
            :pagination="pagination"
            :row-key="row => row.id"
          />
        </n-card>
      </n-tab-pane>

      <!-- 通知对象 -->
      <n-tab-pane name="targets" tab="通知对象">
        <div style="margin-bottom: 12px">
          <n-button type="primary" @click="openTargetCreate">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            新建对象
          </n-button>
        </div>
        <n-card :bordered="false">
          <n-data-table
            :columns="targetColumns"
            :data="targets"
            :loading="targetsLoading"
            :pagination="targetPagination"
            :row-key="row => row.id"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- 规则创建/编辑弹窗 -->
    <n-modal v-model:show="showRuleModal" preset="card"
      :title="isRuleEdit ? '编辑规则' : '新建规则'"
      style="width: 560px" :bordered="false">
      <n-form :model="ruleForm" label-placement="left" label-width="90">
        <n-form-item label="规则名称" required>
          <n-input v-model:value="ruleForm.name" placeholder="规则名称" />
        </n-form-item>
        <n-form-item label="匹配条件" required>
          <n-input v-model:value="ruleForm.condition" type="textarea"
            placeholder='JSON规则，如 {"severity": "critical", "type": "cpu"}' :rows="4" />
        </n-form-item>
        <n-form-item label="目标对象">
          <n-select v-model:value="ruleForm.target_ids" :options="targetSelectOptions"
            multiple placeholder="选择通知对象" />
        </n-form-item>
        <n-form-item label="优先级">
          <n-select v-model:value="ruleForm.priority" :options="priorityOptions" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="ruleForm.description" placeholder="规则描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showRuleModal = false">取消</n-button>
          <n-button type="primary" @click="handleRuleSave" :loading="ruleSaving">
            {{ isRuleEdit ? '保存' : '创建' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 通知对象创建弹窗 -->
    <n-modal v-model:show="showTargetModal" preset="card"
      title="新建通知对象" style="width: 480px" :bordered="false">
      <n-form :model="targetForm" label-placement="left" label-width="90">
        <n-form-item label="名称" required>
          <n-input v-model:value="targetForm.name" placeholder="对象名称" />
        </n-form-item>
        <n-form-item label="类型">
          <n-select v-model:value="targetForm.type" :options="targetTypeOptions" />
        </n-form-item>
        <n-form-item label="值">
          <n-input v-model:value="targetForm.value" placeholder="邮箱/钉钉UserID/手机号等" />
        </n-form-item>
        <n-form-item label="标签">
          <n-dynamic-tags v-model:value="targetForm.tags" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showTargetModal = false">取消</n-button>
          <n-button type="primary" @click="handleTargetSave" :loading="targetSaving">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 匹配测试弹窗 -->
    <n-modal v-model:show="showMatchModal" preset="card"
      title="匹配规则测试" style="width: 520px" :bordered="false">
      <n-form :model="matchForm">
        <n-form-item label="测试数据">
          <n-input v-model:value="matchForm.input" type="textarea"
            placeholder='输入JSON测试数据，如 {"severity": "critical", "type": "cpu"}' :rows="6" />
        </n-form-item>
      </n-form>
      <n-space style="margin-bottom: 12px">
        <n-button type="primary" @click="handleMatchTest" :loading="matchLoading">测试匹配</n-button>
      </n-space>
      <div v-if="matchResult">
        <n-alert :type="matchResult.matched ? 'success' : 'warning'">
          {{ matchResult.matched ? '匹配成功！' : '未匹配到规则' }}
        </n-alert>
        <div v-if="matchResult.matched_rules?.length" style="margin-top: 8px">
          <n-list bordered>
            <n-list-item v-for="r in matchResult.matched_rules" :key="r.id">
              <span>{{ r.name }} (优先级: {{ r.priority }})</span>
            </n-list-item>
          </n-list>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, h, onMounted, computed } from 'vue'
import { useMessage, useDialog, NButton, NSpace, NIcon, NSwitch, NTag, NList, NListItem } from 'naive-ui'
import { AddOutline, CreateOutline, TrashOutline, SearchOutline } from '@vicons/ionicons5'
import {
  getTargetRules, createTargetRule, updateTargetRule, deleteTargetRule, toggleTargetRule,
  getTargets, createTarget, deleteTarget, matchTargetRules
} from '@/api/notification'
import dayjs from 'dayjs'

const message = useMessage()
const dialog = useDialog()
const activeTab = ref('rules')

// ========== 目标规则 ==========
const loading = ref(false)
const rules = ref([])
const pagination = ref({ page: 1, pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] })

const priorityOptions = [
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' }
]

const showRuleModal = ref(false)
const isRuleEdit = ref(false)
const editRuleId = ref(null)
const ruleForm = ref({ name: '', condition: '', target_ids: [], priority: 'medium', description: '' })
const ruleSaving = ref(false)

// 目标选择
const targetList = ref([])
const targetSelectOptions = computed(() => targetList.value.map(t => ({ label: t.name, value: t.id })))

const ruleColumns = ref([
  { title: 'ID', key: 'id', width: 80 },
  { title: '规则名称', key: 'name' },
  { title: '匹配条件', key: 'condition', ellipsis: { tooltip: true } },
  {
    title: '优先级', key: 'priority', width: 80,
    render: row => {
      const typeMap = { high: 'error', medium: 'warning', low: 'info' }
      const labelMap = { high: '高', medium: '中', low: '低' }
      return h(NTag, { type: typeMap[row.priority] || 'default', size: 'small' },
        { default: () => labelMap[row.priority] || row.priority })
    }
  },
  {
    title: '状态', key: 'enabled', width: 80,
    render: row => h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small' },
      { default: () => row.enabled ? '启用' : '禁用' })
  },
  {
    title: '创建时间', key: 'created_at', width: 180,
    render: row => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-'
  },
  {
    title: '操作', key: 'actions', width: 220, fixed: 'right',
    render: row => h(NSpace, null, {
      default: () => [
        h(NSwitch, { value: row.enabled, size: 'small', onUpdateValue: () => handleToggleRule(row) }),
        h(NButton, { size: 'small', onClick: () => openRuleEdit(row) },
          { default: () => '编辑', icon: () => h(NIcon, null, { default: () => h(CreateOutline) }) }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDeleteRule(row.id) },
          { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) })
      ]
    })
  }
])

async function loadRules() {
  loading.value = true
  try {
    const params = { page: pagination.value.page, page_size: pagination.value.pageSize }
    const res = await getTargetRules(params)
    const data = res.data || {}
    rules.value = data.items || data.rules || data || []
    if (data.total !== undefined) pagination.value.itemCount = data.total
  } catch (e) {
    console.error('Load rules error:', e)
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

function openRuleCreate() {
  isRuleEdit.value = false
  editRuleId.value = null
  ruleForm.value = { name: '', condition: '', target_ids: [], priority: 'medium', description: '' }
  showRuleModal.value = true
}

function openRuleEdit(row) {
  isRuleEdit.value = true
  editRuleId.value = row.id
  ruleForm.value = {
    name: row.name,
    condition: typeof row.condition === 'object' ? JSON.stringify(row.condition, null, 2) : row.condition,
    target_ids: row.target_ids || [],
    priority: row.priority || 'medium',
    description: row.description || ''
  }
  showRuleModal.value = true
}

async function handleRuleSave() {
  if (!ruleForm.value.name || !ruleForm.value.condition) {
    message.warning('请填写必填项')
    return false
  }
  ruleSaving.value = true
  try {
    let condition
    try {
      condition = JSON.parse(ruleForm.value.condition)
    } catch {
      condition = ruleForm.value.condition
    }
    const payload = { ...ruleForm.value, condition }
    if (isRuleEdit.value) {
      await updateTargetRule(editRuleId.value, payload)
      message.success('已更新')
    } else {
      await createTargetRule(payload)
      message.success('已创建')
    }
    showRuleModal.value = false
    await loadRules()
  } catch (e) {
    message.error('操作失败')
    return false
  } finally {
    ruleSaving.value = false
  }
}

async function handleToggleRule(row) {
  try {
    await toggleTargetRule(row.id)
    message.success(row.enabled ? '已禁用' : '已启用')
    await loadRules()
  } catch (e) {
    message.error('操作失败')
  }
}

function handleDeleteRule(id) {
  dialog.warning({
    title: '确认删除', content: '确定删除此规则吗？',
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteTargetRule(id)
        message.success('已删除')
        await loadRules()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

// ========== 通知对象 ==========
const targetsLoading = ref(false)
const targets = ref([])
const targetPagination = ref({ page: 1, pageSize: 10, showSizePicker: true, pageSizes: [10, 20, 50] })

const targetTypeOptions = [
  { label: '邮箱', value: 'email' },
  { label: '钉钉', value: 'dingtalk' },
  { label: '飞书', value: 'feishu' },
  { label: '企微', value: 'wecom' },
  { label: '短信', value: 'sms' },
  { label: '站内信', value: 'in_app' }
]

const showTargetModal = ref(false)
const targetForm = ref({ name: '', type: 'email', value: '', tags: [] })
const targetSaving = ref(false)

const targetColumns = ref([
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name' },
  {
    title: '类型', key: 'type', width: 100,
    render: row => {
      const opt = targetTypeOptions.find(o => o.value === row.type)
      return h(NTag, { size: 'small' }, { default: () => opt?.label || row.type })
    }
  },
  { title: '值', key: 'value' },
  {
    title: '标签', key: 'tags', width: 200,
    render: row => {
      if (!row.tags || !row.tags.length) return '-'
      return h(NSpace, null, {
        default: () => row.tags.map(t => h(NTag, { size: 'small', bordered: false }, { default: () => t }))
      })
    }
  },
  {
    title: '操作', key: 'actions', width: 100, fixed: 'right',
    render: row => h(NButton, { size: 'small', type: 'error', onClick: () => handleDeleteTarget(row.id) },
      { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) })
  }
])

async function loadTargets() {
  targetsLoading.value = true
  try {
    const params = { page: targetPagination.value.page, page_size: targetPagination.value.pageSize }
    const res = await getTargets(params)
    const data = res.data || {}
    targets.value = data.items || data.targets || data || []
    if (data.total !== undefined) targetPagination.value.itemCount = data.total
  } catch (e) {
    console.error('Load targets error:', e)
  } finally {
    targetsLoading.value = false
  }
}

function openTargetCreate() {
  targetForm.value = { name: '', type: 'email', value: '', tags: [] }
  showTargetModal.value = true
}

async function handleTargetSave() {
  if (!targetForm.value.name || !targetForm.value.value) {
    message.warning('请填写必填项')
    return false
  }
  targetSaving.value = true
  try {
    await createTarget(targetForm.value)
    message.success('已创建')
    showTargetModal.value = false
    await loadTargets()
  } catch (e) {
    message.error('创建失败')
    return false
  } finally {
    targetSaving.value = false
  }
}

function handleDeleteTarget(id) {
  dialog.warning({
    title: '确认删除', content: '确定删除此通知对象吗？',
    positiveText: '删除', negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteTarget(id)
        message.success('已删除')
        await loadTargets()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

// ========== 匹配测试 ==========
const showMatchModal = ref(false)
const matchForm = ref({ input: '' })
const matchLoading = ref(false)
const matchResult = ref(null)

function openMatchTest() {
  matchForm.value = { input: '' }
  matchResult.value = null
  showMatchModal.value = true
}

async function handleMatchTest() {
  if (!matchForm.value.input.trim()) {
    message.warning('请输入测试数据')
    return
  }
  matchLoading.value = true
  try {
    let input
    try {
      input = JSON.parse(matchForm.value.input)
    } catch {
      message.error('请输入有效的JSON')
      return
    }
    const res = await matchTargetRules(input)
    matchResult.value = res.data || {}
  } catch (e) {
    message.error('匹配测试失败')
  } finally {
    matchLoading.value = false
  }
}

onMounted(() => {
  loadTargets()
  loadRules()
})
</script>
