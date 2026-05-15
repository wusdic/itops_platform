<template>
  <div class="knowledge-base-page">
    <el-tabs
      v-model="activeTab"
      @tab-change="handleTabChange"
    >
      <el-tab-pane
        label="文档管理"
        name="documents"
      >
        <div class="page-header">
          <h2>文档管理</h2>
          <el-button
            type="primary"
            @click="showUploadDialog"
          >
            上传文档
          </el-button>
        </div>

        <!-- 拖拽上传区域 -->
        <div
          class="upload-zone"
          :class="{ 'is-dragover': isDragover }"
          @drop.prevent="handleDrop"
          @dragover.prevent="isDragover = true"
          @dragleave="isDragover = false"
        >
          <el-icon :size="48">
            <UploadFilled />
          </el-icon>
          <p>
            将文件拖拽到此处，或 <el-button
              type="text"
              @click="showUploadDialog"
            >
              点击上传
            </el-button>
          </p>
          <p class="upload-hint">
            支持 PDF、Word、Excel、TXT、Markdown 格式
          </p>
        </div>

        <!-- 文档列表 -->
        <el-table
          :data="documents"
          stripe
          style="width: 100%; margin-top: 20px"
        >
          <el-table-column
            prop="name"
            label="文档名称"
          >
            <template #default="{ row }">
              <div class="doc-name">
                <el-icon><Document /></el-icon>
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="type"
            label="类型"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="getDocTypeTag(row.type)"
              >
                {{ row.type.toUpperCase() }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="size"
            label="大小"
            width="100"
          />
          <el-table-column
            prop="uploadedAt"
            label="上传时间"
            width="180"
          />
          <el-table-column
            prop="status"
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="row.status === 'ready' ? 'success' : 'warning'"
              >
                {{ row.status === 'ready' ? '已处理' : '处理中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="200"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                size="small"
                type="primary"
                @click="searchDoc(row)"
              >
                检索
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="deleteDoc(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane
        label="知识检索"
        name="search"
      >
        <div class="page-header">
          <h2>知识检索</h2>
        </div>

        <div class="search-box">
          <el-input
            v-model="searchQuery"
            placeholder="输入关键词搜索知识库..."
            size="large"
            @keyup.enter="doSearch"
          >
            <template #append>
              <el-button
                :icon="Search"
                @click="doSearch"
              >
                搜索
              </el-button>
            </template>
          </el-input>
        </div>

        <div class="search-filters">
          <el-select
            v-model="searchFilter.docType"
            placeholder="文档类型"
            clearable
            style="width: 150px"
          >
            <el-option
              label="PDF"
              value="pdf"
            />
            <el-option
              label="Word"
              value="doc"
            />
            <el-option
              label="Excel"
              value="xlsx"
            />
            <el-option
              label="TXT"
              value="txt"
            />
          </el-select>
          <el-select
            v-model="searchFilter.topK"
            placeholder="返回数量"
            style="width: 120px"
          >
            <el-option
              label="5条"
              :value="5"
            />
            <el-option
              label="10条"
              :value="10"
            />
            <el-option
              label="20条"
              :value="20"
            />
          </el-select>
        </div>

        <div
          v-if="searchResults.length > 0"
          class="search-results"
        >
          <div class="result-header">
            找到 {{ searchResults.length }} 条相关结果
          </div>
          <div
            v-for="result in searchResults"
            :key="result.id"
            class="result-item"
          >
            <div class="result-header">
              <span class="result-title">{{ result.title }}</span>
              <span class="result-score">相似度: {{ (result.score * 100).toFixed(1) }}%</span>
            </div>
            <div class="result-content">
              {{ result.content }}
            </div>
            <div class="result-meta">
              <span>来源: {{ result.source }}</span>
              <span>页码: {{ result.page || 'N/A' }}</span>
            </div>
          </div>
        </div>

        <div
          v-else-if="hasSearched"
          class="empty-state"
        >
          <el-empty description="未找到相关结果" />
        </div>
      </el-tab-pane>

      <el-tab-pane
        label="RAG对话"
        name="chat"
      >
        <div class="page-header">
          <h2>RAG 对话</h2>
          <el-button
            size="small"
            @click="clearChat"
          >
            清空对话
          </el-button>
        </div>

        <div class="chat-container">
          <div
            ref="chatMessagesRef"
            class="chat-messages"
          >
            <div
              v-for="msg in chatMessages"
              :key="msg.id"
              class="chat-message"
              :class="'msg-' + msg.role"
            >
              <div class="message-content">
                <div
                  v-if="msg.role === 'user'"
                  class="message-text"
                >
                  {{ msg.content }}
                </div>
                <div
                  v-else
                  class="message-text"
                  v-html="renderMarkdown(msg.content)"
                />
                <div class="message-time">
                  {{ msg.time }}
                </div>
              </div>
            </div>
            <div
              v-if="isTyping"
              class="chat-message msg-assistant"
            >
              <div class="message-content">
                <div class="message-text typing">
                  <span class="dot" />
                  <span class="dot" />
                  <span class="dot" />
                </div>
              </div>
            </div>
          </div>

          <div class="chat-input">
            <el-input
              v-model="chatInput"
              type="textarea"
              placeholder="输入问题，AI将基于知识库回答..."
              :rows="2"
              @keydown.enter.meta="sendMessage"
              @keydown.enter.ctrl="sendMessage"
            />
            <el-button
              type="primary"
              :disabled="!chatInput.trim() || isTyping"
              @click="sendMessage"
            >
              发送
            </el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 上传弹窗 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传文档"
      width="500px"
    >
      <el-form
        ref="uploadFormRef"
        :model="uploadForm"
        label-width="100px"
      >
        <el-form-item label="文档名称">
          <el-input
            v-model="uploadForm.name"
            placeholder="自动从文件名获取"
          />
        </el-form-item>
        <el-form-item label="文档类型">
          <el-select
            v-model="uploadForm.type"
            style="width: 100%"
          >
            <el-option
              label="技术文档"
              value="tech"
            />
            <el-option
              label="运维手册"
              value="ops"
            />
            <el-option
              label="故障案例"
              value="case"
            />
            <el-option
              label="配置文档"
              value="config"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="上传文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.md"
            :on-change="handleFileChange"
          >
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="自动解析">
          <el-switch v-model="uploadForm.autoParse" />
          <span class="form-hint">上传后自动进行文本解析和向量化</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="confirmUpload"
        >
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Document, Search } from '@element-plus/icons-vue'
import api from '../api'

const activeTab = ref('documents')
const isDragover = ref(false)
const uploadDialogVisible = ref(false)
const uploadFormRef = ref(null)
const uploadRef = ref(null)
const chatMessagesRef = ref(null)

const documents = ref([
  { id: 1, name: '服务器运维手册.pdf', type: 'pdf', size: '2.5MB', uploadedAt: '2026-05-02 14:30:00', status: 'ready' },
  { id: 2, name: 'K8S部署指南.docx', type: 'docx', size: '1.2MB', uploadedAt: '2026-05-02 10:15:00', status: 'ready' },
  { id: 3, name: '故障处理案例集.xlsx', type: 'xlsx', size: '856KB', uploadedAt: '2026-05-01 16:45:00', status: 'ready' },
  { id: 4, name: 'Nginx配置最佳实践.md', type: 'md', size: '45KB', uploadedAt: '2026-05-01 09:20:00', status: 'ready' },
  { id: 5, name: '数据库优化手册.pdf', type: 'pdf', size: '3.1MB', uploadedAt: '2026-04-30 11:30:00', status: 'processing' }
])

const uploadForm = ref({
  name: '',
  type: 'tech',
  file: null,
  autoParse: true
})

const searchQuery = ref('')
const searchFilter = ref({ docType: '', topK: 10 })
const searchResults = ref([])
const hasSearched = ref(false)

const chatInput = ref('')
const chatMessages = ref([
  { id: 1, role: 'assistant', content: '您好！我是RAG智能助手，可以根据知识库中的文档回答您的问题。请问有什么可以帮您？', time: '09:53' }
])
const isTyping = ref(false)

const getDocTypeTag = (type) => {
  const tags = { pdf: 'danger', doc: 'primary', docx: 'primary', xlsx: 'success', txt: 'info', md: 'info' }
  return tags[type] || ''
}

const showUploadDialog = () => {
  uploadForm.value = { name: '', type: 'tech', file: null, autoParse: true }
  uploadDialogVisible.value = true
}

const handleDrop = (e) => {
  isDragover.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    const file = files[0]
    uploadForm.value.name = file.name
    uploadForm.value.file = file
    confirmUpload()
  }
}

const handleFileChange = (uploadFile) => {
  uploadForm.value.file = uploadFile.raw
  if (!uploadForm.value.name) {
    uploadForm.value.name = uploadFile.name
  }
}

const confirmUpload = async () => {
  if (!uploadForm.value.file) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  
  const formData = new FormData()
  formData.append('file', uploadForm.value.file)
  formData.append('name', uploadForm.value.name)
  formData.append('type', uploadForm.value.type)
  formData.append('autoParse', uploadForm.value.autoParse)
  
  try {
    const res = await api.uploadDocument(formData)
    documents.value.unshift({
      id: res.id,
      name: uploadForm.value.name,
      type: uploadForm.value.file.name.split('.').pop(),
      size: `${(uploadForm.value.file.size / 1024).toFixed(0)}KB`,
      uploadedAt: new Date().toLocaleString(),
      status: uploadForm.value.autoParse ? 'processing' : 'ready'
    })
    ElMessage.success('文档上传成功')
    uploadDialogVisible.value = false
  } catch (err) {
    ElMessage.error('上传失败: ' + (err.message || '未知错误'))
  }
}

const deleteDoc = async (doc) => {
  try {
    await ElMessageBox.confirm(`确定要删除文档 "${doc.name}" 吗？`, '提示', { type: 'warning' })
    await api.deleteDocument(doc.id)
    const idx = documents.value.findIndex(d => d.id === doc.id)
    if (idx !== -1) documents.value.splice(idx, 1)
    ElMessage.success('文档已删除')
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('删除失败')
  }
}

const searchDoc = (doc) => {
  searchQuery.value = `关于 ${doc.name} 的内容`
  activeTab.value = 'search'
  doSearch()
}

const doSearch = async () => {
  if (!searchQuery.value.trim()) return
  
  hasSearched.value = true
  searchResults.value = []
  
  try {
    const res = await api.searchKnowledge({
      query: searchQuery.value,
      top_k: searchFilter.value.topK,
      doc_type: searchFilter.value.docType || undefined
    })
    searchResults.value = res || []
  } catch (err) {
    // 搜索失败时清空结果，不使用假数据
    searchResults.value = []
  }
}

const sendMessage = async () => {
  if (!chatInput.value.trim() || isTyping.value) return
  
  const userMsg = {
    id: Date.now(),
    role: 'user',
    content: chatInput.value,
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  chatMessages.value.push(userMsg)
  const query = chatInput.value
  chatInput.value = ''
  
  isTyping.value = true
  await nextTick()
  chatMessagesRef.value?.scrollTo({ top: chatMessagesRef.value.scrollHeight, behavior: 'smooth' })
  
  try {
    const res = await api.ragChat({ query })
    const assistantMsg = {
      id: Date.now() + 1,
      role: 'assistant',
      content: res.answer || '抱歉，我无法回答这个问题。',
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    chatMessages.value.push(assistantMsg)
  } catch (err) {
    const assistantMsg = {
      id: Date.now() + 1,
      role: 'assistant',
      content: '抱歉，AI 助手暂时无法回答您的问题，请稍后再试。',
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    chatMessages.value.push(assistantMsg)
  }
  
  isTyping.value = false
  await nextTick()
  chatMessagesRef.value?.scrollTo({ top: chatMessagesRef.value.scrollHeight, behavior: 'smooth' })
}

const clearChat = () => {
  chatMessages.value = [
    { id: 1, role: 'assistant', content: '您好！我是RAG智能助手，可以根据知识库中的文档回答您的问题。请问有什么可以帮您？', time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }
  ]
}

const renderMarkdown = (text) => {
  // 简单的markdown渲染
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

const handleTabChange = (tab) => {
  if (tab === 'documents') {
    api.getDocuments().then(res => {
      if (res && res.length) documents.value = res
    }).catch(console.error)
  }
}

onMounted(() => {
  api.getDocuments().then(res => {
    if (res && res.length) documents.value = res
  }).catch(console.error)
})
</script>

<style scoped>
.knowledge-base-page {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.upload-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  color: #909399;
  transition: all 0.3s;
  cursor: pointer;
}

.upload-zone:hover,
.upload-zone.is-dragover {
  border-color: #409eff;
  background: #f0f7ff;
  color: #409eff;
}

.upload-zone p {
  margin: 15px 0 5px;
}

.upload-hint {
  font-size: 12px;
  color: #c0c4cc;
}

.doc-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-box {
  margin-bottom: 15px;
}

.search-filters {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-results {
  margin-top: 20px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 14px;
}

.result-title {
  font-weight: 500;
  color: #303133;
}

.result-score {
  color: #67c23a;
  font-size: 12px;
}

.result-item {
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 15px;
}

.result-content {
  color: #606266;
  line-height: 1.6;
  margin: 10px 0;
}

.result-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 20px;
}

.empty-state {
  padding: 60px 0;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 300px);
  min-height: 400px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.chat-message {
  display: flex;
  margin-bottom: 20px;
}

.msg-user {
  justify-content: flex-end;
}

.msg-assistant {
  justify-content: flex-start;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
}

.msg-user .message-content {
  background: #409eff;
  color: #fff;
}

.msg-assistant .message-content {
  background: #fff;
  border: 1px solid #e4e7ed;
}

.message-text {
  line-height: 1.6;
}

.message-time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 5px;
  text-align: right;
}

.message-text.typing {
  display: flex;
  gap: 4px;
}

.dot {
  width: 8px;
  height: 8px;
  background: #909399;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.chat-input {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.chat-input .el-textarea {
  flex: 1;
}

.form-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style>