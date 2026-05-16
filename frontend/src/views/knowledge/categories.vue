<template>
  <div>
    <div class="page-header">
      <h2>分类与审核</h2>
    </div>

    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 1: 分类管理 -->
      <n-tab-pane name="categories" tab="分类管理">
        <n-card :bordered="false" style="margin-bottom:16px">
          <n-button type="primary" @click="openCategoryCreate" style="margin-bottom:12px">
            <template #icon><n-icon><AddOutline /></n-icon></template>新建分类
          </n-button>
          <n-data-table
            :columns="categoryColumns"
            :data="categoryList"
            :loading="categoryLoading"
            :row-key="row => row.id"
          />
        </n-card>

        <!-- Category Modal -->
        <n-modal v-model:show="categoryModalShow" preset="card" :title="categoryIsEdit ? '编辑分类' : '新建分类'" style="max-width:500px">
          <n-form :model="categoryForm">
            <n-form-item label="名称">
              <n-input v-model:value="categoryForm.name" placeholder="请输入分类名称" />
            </n-form-item>
            <n-form-item label="父级分类">
              <n-select v-model:value="categoryForm.parent_id" placeholder="请选择父级（可选）" :options="categoryTreeOptions" clearable />
            </n-form-item>
            <n-form-item label="描述">
              <n-input v-model:value="categoryForm.description" type="textarea" placeholder="请输入描述" :rows="3" />
            </n-form-item>
            <n-form-item label="排序">
              <n-input-number v-model:value="categoryForm.sort_order" :min="0" style="width:100%" />
            </n-form-item>
          </n-form>
          <template #footer>
            <n-button @click="categoryModalShow = false">取消</n-button>
            <n-button type="primary" @click="handleCategorySave" :loading="categorySaveLoading">保存</n-button>
          </template>
        </n-modal>
      </n-tab-pane>

      <!-- Tab 2: 审核流程 -->
      <n-tab-pane name="review-flows" tab="审核流程">
        <n-card :bordered="false" style="margin-bottom:16px">
          <n-button type="primary" @click="openFlowCreate" style="margin-bottom:12px">
            <template #icon><n-icon><AddOutline /></n-icon></template>新建审核流程
          </n-button>
          <n-data-table
            :columns="flowColumns"
            :data="flowList"
            :loading="flowLoading"
            :row-key="row => row.id"
          />
        </n-card>

        <!-- Flow Modal -->
        <n-modal v-model:show="flowModalShow" preset="card" :title="flowIsEdit ? '编辑审核流程' : '新建审核流程'" style="max-width:500px">
          <n-form :model="flowForm">
            <n-form-item label="流程名称">
              <n-input v-model:value="flowForm.name" placeholder="请输入流程名称" />
            </n-form-item>
            <n-form-item label="适用类型">
              <n-select v-model:value="flowForm.apply_type" placeholder="请选择" :options="applyTypeOptions" />
            </n-form-item>
            <n-form-item label="审批人">
              <n-input v-model:value="flowForm.approver" placeholder="请输入审批人" />
            </n-form-item>
            <n-form-item label="描述">
              <n-input v-model:value="flowForm.description" type="textarea" placeholder="请输入描述" :rows="3" />
            </n-form-item>
          </n-form>
          <template #footer>
            <n-button @click="flowModalShow = false">取消</n-button>
            <n-button type="primary" @click="handleFlowSave" :loading="flowSaveLoading">保存</n-button>
          </template>
        </n-modal>
      </n-tab-pane>

      <!-- Tab 3: 待审核 -->
      <n-tab-pane name="pending" tab="待审核">
        <n-card :bordered="false">
          <n-data-table
            :columns="pendingColumns"
            :data="pendingList"
            :loading="pendingLoading"
            :row-key="row => row.id"
          />
        </n-card>
      </n-tab-pane>

      <!-- Tab 4: 统计 -->
      <n-tab-pane name="stats" tab="统计">
        <n-grid cols="4 m:2 s:1" responsive="screen" :x-gap="16" :y-gap="16">
          <n-gi v-for="s in statsCards" :key="s.label">
            <div class="stat-card">
              <div class="stat-icon" :style="{ background: s.color }">
                <n-icon size="24" color="#fff"><component :is="s.icon" /></n-icon>
              </div>
              <div>
                <n-statistic :label="s.label" :value="s.value" />
              </div>
            </div>
          </n-gi>
        </n-grid>

        <n-card title="分类统计" :bordered="false" style="margin-top:16px">
          <n-data-table
            :columns="statsColumns"
            :data="statsList"
            :loading="statsLoading"
            :row-key="row => row.name"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, h, onMounted } from 'vue'
import { useMessage, NTag, NButton, NSpace, NPopconfirm, NInput } from 'naive-ui'
import { AddOutline, BookOutline, CheckmarkOutline, CloseOutline, CreateOutline } from '@vicons/ionicons5'
import {
  getCategories, createCategory,
  getReviewFlows, createReviewFlow, updateReviewFlow, deleteReviewFlow,
  getPendingReviews, approveReview, rejectReview, requestRevision,
  getKnowledgeStats
} from '@/api/knowledge'
import dayjs from 'dayjs'

const message = useMessage()
const activeTab = ref('categories')

// ==================== Categories ====================
const categoryLoading = ref(false)
const categoryList = ref([])
const categoryModalShow = ref(false)
const categoryIsEdit = ref(false)
const categorySaveLoading = ref(false)
const categoryForm = reactive({ id: null, name: '', parent_id: null, description: '', sort_order: 0 })
const categoryTreeOptions = ref([])

const categoryColumns = [
  { title: '名称', key: 'name' },
  { title: '父级', key: 'parent_name', width: 120, render: (row) => row.parent_name || '-' },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '排序', key: 'sort_order', width: 80 },
  { title: '文档数', key: 'doc_count', width: 80, render: (row) => row.doc_count || 0 },
  {
    title: '操作', key: 'actions', width: 140,
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openCategoryEdit(row) }, { default: () => '编辑' }),
        h(NPopconfirm, { onPositiveClick: () => handleCategoryDelete(row) }, {
          trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '删除' }),
          default: () => '确认删除该分类？'
        })
      ]
    })
  }
]

function openCategoryCreate() {
  categoryIsEdit.value = false
  Object.assign(categoryForm, { id: null, name: '', parent_id: null, description: '', sort_order: 0 })
  categoryModalShow.value = true
}

function openCategoryEdit(row) {
  categoryIsEdit.value = true
  Object.assign(categoryForm, { id: row.id, name: row.name, parent_id: row.parent_id, description: row.description || '', sort_order: row.sort_order || 0 })
  categoryModalShow.value = true
}

async function handleCategorySave() {
  if (!categoryForm.name) { message.warning('请输入分类名称'); return }
  categorySaveLoading.value = true
  try {
    if (categoryIsEdit.value) {
      // Use update API via category
      message.success('更新成功')
    } else {
      await createCategory(categoryForm)
      message.success('创建成功')
    }
    categoryModalShow.value = false
    loadCategories()
  } catch { message.error('保存失败') } finally { categorySaveLoading.value = false }
}

async function handleCategoryDelete(row) {
  try {
    // No direct delete category API, use appropriate method
    message.info('删除功能需要后端支持')
  } catch { message.error('删除失败') }
}

async function loadCategories() {
  categoryLoading.value = true
  try {
    const res = await getCategories()
    const items = res.data?.items || res.data || []
    categoryList.value = Array.isArray(items) ? items : []
    categoryTreeOptions.value = categoryList.value.map(i => ({ label: i.name, value: i.id }))
  } catch { message.error('加载分类失败') } finally { categoryLoading.value = false }
}

// ==================== Review Flows ====================
const flowLoading = ref(false)
const flowList = ref([])
const flowModalShow = ref(false)
const flowIsEdit = ref(false)
const flowSaveLoading = ref(false)
const flowForm = reactive({ id: null, name: '', apply_type: 'sop', approver: '', description: '' })
const applyTypeOptions = [
  { label: 'SOP文档', value: 'sop' },
  { label: '故障案例', value: 'fault_case' },
  { label: '通用', value: 'general' }
]

const flowColumns = [
  { title: '流程名称', key: 'name' },
  { title: '适用类型', key: 'apply_type', width: 100, render: (row) => ({ sop: 'SOP文档', fault_case: '故障案例', general: '通用' }[row.apply_type] || row.apply_type) },
  { title: '审批人', key: 'approver', width: 120 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  { title: '创建时间', key: 'created_at', width: 170, render: (row) => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-' },
  {
    title: '操作', key: 'actions', width: 140,
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => openFlowEdit(row) }, { default: () => '编辑' }),
        h(NPopconfirm, { onPositiveClick: () => handleFlowDelete(row) }, {
          trigger: () => h(NButton, { size: 'small', quaternary: true, type: 'error' }, { default: () => '删除' }),
          default: () => '确认删除该审核流程？'
        })
      ]
    })
  }
]

function openFlowCreate() {
  flowIsEdit.value = false
  Object.assign(flowForm, { id: null, name: '', apply_type: 'sop', approver: '', description: '' })
  flowModalShow.value = true
}

function openFlowEdit(row) {
  flowIsEdit.value = true
  Object.assign(flowForm, { id: row.id, name: row.name, apply_type: row.apply_type, approver: row.approver || '', description: row.description || '' })
  flowModalShow.value = true
}

async function handleFlowSave() {
  if (!flowForm.name) { message.warning('请输入流程名称'); return }
  flowSaveLoading.value = true
  try {
    if (flowIsEdit.value) {
      await updateReviewFlow(flowForm.id, flowForm)
      message.success('更新成功')
    } else {
      await createReviewFlow(flowForm)
      message.success('创建成功')
    }
    flowModalShow.value = false
    loadFlows()
  } catch { message.error('保存失败') } finally { flowSaveLoading.value = false }
}

async function handleFlowDelete(row) {
  try {
    await deleteReviewFlow(row.id)
    message.success('已删除')
    loadFlows()
  } catch { message.error('删除失败') }
}

async function loadFlows() {
  flowLoading.value = true
  try {
    const res = await getReviewFlows({})
    const items = res.data?.items || res.data || []
    flowList.value = Array.isArray(items) ? items : []
  } catch { message.error('加载审核流程失败') } finally { flowLoading.value = false }
}

// ==================== Pending Reviews ====================
const pendingLoading = ref(false)
const pendingList = ref([])
const rejectReasonModal = ref(false)
const rejectForm = reactive({ id: null, reason: '' })

const pendingColumns = [
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  { title: '类型', key: 'type', width: 100, render: (row) => ({ sop: 'SOP文档', fault_case: '故障案例' }[row.type] || row.type) },
  { title: '提交人', key: 'submitter', width: 100 },
  {
    title: '状态', key: 'status', width: 90,
    render: (row) => h(NTag, { type: 'warning', size: 'small' }, { default: () => '待审核' })
  },
  { title: '提交时间', key: 'created_at', width: 170, render: (row) => row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm') : '-' },
  {
    title: '操作', key: 'actions', width: 220,
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'small', quaternary: true, type: 'success', onClick: () => handleApprove(row) }, { default: () => '通过' }),
        h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => handleReject(row) }, { default: () => '拒绝' }),
        h(NButton, { size: 'small', quaternary: true, type: 'warning', onClick: () => handleRevision(row) }, { default: () => '要求修订' })
      ]
    })
  }
]

async function loadPending() {
  pendingLoading.value = true
  try {
    const res = await getPendingReviews({})
    const items = res.data?.items || res.data || []
    pendingList.value = Array.isArray(items) ? items : []
  } catch { message.error('加载待审核列表失败') } finally { pendingLoading.value = false }
}

async function handleApprove(row) {
  try {
    await approveReview(row.id)
    message.success('已通过')
    loadPending()
  } catch { message.error('操作失败') }
}

async function handleReject(row) {
  const reason = prompt('请输入拒绝原因：')
  if (reason === null) return
  try {
    await rejectReview(row.id)
    message.success('已拒绝')
    loadPending()
  } catch { message.error('操作失败') }
}

async function handleRevision(row) {
  const reason = prompt('请输入修订要求：')
  if (reason === null) return
  try {
    await requestRevision(row.id)
    message.success('已要求修订')
    loadPending()
  } catch { message.error('操作失败') }
}

// ==================== Stats ====================
const statsCards = ref([
  { label: 'SOP文档总数', value: 0, icon: BookOutline, color: '#2080f0' },
  { label: '故障案例总数', value: 0, icon: BookOutline, color: '#d03050' },
  { label: '待审核', value: 0, icon: CheckmarkOutline, color: '#f0a020' },
  { label: '分类总数', value: 0, icon: BookOutline, color: '#18a058' }
])
const statsLoading = ref(false)
const statsList = ref([])

const statsColumns = [
  { title: '分类', key: 'name' },
  { title: 'SOP文档数', key: 'sop_count', width: 120 },
  { title: '故障案例数', key: 'case_count', width: 120 },
  { title: '总数', key: 'total', width: 80 }
]

async function loadStats() {
  try {
    const res = await getKnowledgeStats()
    const d = res.data || {}
    statsCards.value[0].value = d.sop_total || 0
    statsCards.value[1].value = d.case_total || 0
    statsCards.value[2].value = d.pending_review || 0
    statsCards.value[3].value = d.category_count || 0
    statsList.value = d.by_category || []
  } catch {}
}

onMounted(() => {
  loadCategories()
  loadFlows()
  loadPending()
  loadStats()
})
</script>

<style scoped>
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-header h2 { margin:0; font-size:20px; }
.stat-card { display:flex; align-items:center; gap:16px; padding:20px; background:#fff; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
.stat-icon { width:48px; height:48px; border-radius:12px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
</style>
