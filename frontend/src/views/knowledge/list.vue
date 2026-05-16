<template>
  <div class="knowledge-container">
    <div class="page-header">
      <h1>知识文档</h1>
      <p>运维知识库 - SOP文档和故障案例</p>
    </div>

    <el-tabs v-model="activeTab" class="knowledge-tabs">
      <el-tab-pane label="SOP文档" name="sop">
        <div class="toolbar">
          <el-input v-model="sopSearch" placeholder="搜索SOP标题/内容" style="width: 300px" clearable @keyup.enter="loadSop" />
          <el-button type="primary" @click="loadSop">搜索</el-button>
          <el-button type="success" @click="showSopDialog = true">新建SOP</el-button>
        </div>
        <el-table :data="sopList" v-loading="sopLoading" stripe style="width: 100%; margin-top: 16px">
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
                {{ row.status === 'published' ? '已发布' : '草稿' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="180">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="viewSop(row)">查看</el-button>
              <el-button type="danger" link size="small" @click="deleteSop(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination v-model:current-page="sopPage" :total="sopTotal" :page-size="20" layout="total, prev, pager, next" style="margin-top: 16px" />
      </el-tab-pane>

      <el-tab-pane label="故障案例" name="fault">
        <div class="toolbar">
          <el-input v-model="faultSearch" placeholder="搜索故障案例" style="width: 300px" clearable @keyup.enter="loadFault" />
          <el-button type="primary" @click="loadFault">搜索</el-button>
        </div>
        <el-table :data="faultList" v-loading="faultLoading" stripe style="width: 100%; margin-top: 16px">
          <el-table-column prop="title" label="故障标题" min-width="200" />
          <el-table-column prop="severity" label="严重程度" width="100">
            <template #default="{ row }">
              <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'resolved' ? 'success' : 'warning'" size="small">
                {{ row.status === 'resolved' ? '已解决' : '处理中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" width="180">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="viewFault(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination v-model:current-page="faultPage" :total="faultTotal" :page-size="20" layout="total, prev, pager, next" style="margin-top: 16px" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="sopDetailVisible" title="SOP文档详情" width="700px">
      <div v-if="currentSop">
        <h3>{{ currentSop.title }}</h3>
        <el-divider />
        <div class="sop-content" v-html="currentSop.content || '<p>暂无内容</p>'"></div>
      </div>
    </el-dialog>

    <el-dialog v-model="faultDetailVisible" title="故障案例详情" width="700px">
      <div v-if="currentFault">
        <h3>{{ currentFault.title }}</h3>
        <el-divider />
        <el-descriptions :column="2" border>
          <el-descriptions-item label="严重程度">{{ currentFault.severity }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ currentFault.status === 'resolved' ? '已解决' : '处理中' }}</el-descriptions-item>
          <el-descriptions-item label="影响范围" :span="2">{{ currentFault.impact || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="根本原因" :span="2">{{ currentFault.root_cause || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="解决方案" :span="2">{{ currentFault.solution || '未知' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <el-dialog v-model="showSopDialog" title="新建SOP文档" width="600px" @close="resetSopForm">
      <el-form :model="sopForm" label-width="100px">
        <el-form-item label="标题" required>
          <el-input v-model="sopForm.title" placeholder="请输入SOP标题" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="sopForm.category" placeholder="请选择分类" style="width: 100%">
            <el-option label="网络" value="network" />
            <el-option label="服务器" value="server" />
            <el-option label="数据库" value="database" />
            <el-option label="应用" value="application" />
            <el-option label="安全" value="security" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="sopForm.content" type="textarea" :rows="8" placeholder="请输入SOP内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSopDialog = false">取消</el-button>
        <el-button type="primary" @click="createSop" :loading="sopCreating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledge } from '@/api'

const activeTab = ref('sop')
const sopSearch = ref('')
const sopList = ref([])
const sopLoading = ref(false)
const sopPage = ref(1)
const sopTotal = ref(0)
const sopDetailVisible = ref(false)
const showSopDialog = ref(false)
const sopCreating = ref(false)
const currentSop = ref(null)
const sopForm = ref({ title: '', category: 'server', content: '' })

const faultSearch = ref('')
const faultList = ref([])
const faultLoading = ref(false)
const faultPage = ref(1)
const faultTotal = ref(0)
const faultDetailVisible = ref(false)
const currentFault = ref(null)



const loadSop = async () => {
  sopLoading.value = true
  try {
    const res = await knowledge.getSopList({ page: sopPage.value, page_size: 20, search: sopSearch.value })
    sopList.value = res.items || []
    sopTotal.value = res.total || 0
  } catch (error) {
    console.error('Load SOP error:', error)
    ElMessage.error('加载SOP列表失败')
    sopList.value = []
  } finally { sopLoading.value = false }
}

const loadFault = async () => {
  faultLoading.value = true
  try {
    const res = await knowledge.getFaultCaseList({ page: faultPage.value, page_size: 20, search: faultSearch.value })
    faultList.value = res.items || []
    faultTotal.value = res.total || 0
  } catch (error) {
    console.error('Load fault cases error:', error)
    ElMessage.error('加载故障案例失败')
    faultList.value = []
  } finally { faultLoading.value = false }
}

const viewSop = (row) => { currentSop.value = row; sopDetailVisible.value = true }
const viewFault = (row) => { currentFault.value = row; faultDetailVisible.value = true }

const deleteSop = (row) => {
  ElMessageBox.confirm(`确定删除SOP《${row.title}》吗？`, '提示', { type: 'warning' })
    .then(async () => {
      try { await knowledge.deleteSop(row.id); ElMessage.success('删除成功'); loadSop() }
      catch { ElMessage.error('删除失败') }
    }).catch(() => {})
}

const createSop = async () => {
  if (!sopForm.value.title) { ElMessage.warning('请输入标题'); return }
  sopCreating.value = true
  try {
    await knowledge.createSop(sopForm.value)
    ElMessage.success('创建成功')
    showSopDialog.value = false
    loadSop()
  } catch (error) {
    console.error('Create SOP error:', error)
    ElMessage.error('创建失败')
  } finally { sopCreating.value = false }
}

const resetSopForm = () => { sopForm.value = { title: '', category: 'server', content: '' } }

const getSeverityType = (severity) => {
  if (severity?.startsWith('P1')) return 'danger'
  if (severity?.startsWith('P2')) return 'warning'
  return 'info'
}

const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  if (diff < 2592000) return `${Math.floor(diff / 86400)}天前`
  return d.toLocaleDateString()
}

onMounted(() => { loadSop() })
</script>

<style scoped>
.knowledge-container { padding: 24px; }
.page-header { margin-bottom: 24px; }
.page-header h1 { margin: 0 0 8px 0; font-size: 24px; font-weight: 600; }
.page-header p { margin: 0; color: #909399; }
.toolbar { display: flex; gap: 12px; align-items: center; }
.sop-content { line-height: 1.8; }
</style>
