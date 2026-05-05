<template>
  <div class="knowledge-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">知识库</h2>
        <p class="page-subtitle">运维知识积累与共享，支持文档分类管理和智能搜索</p>
      </div>
      <div class="page-header-actions">
        <el-button @click="handleExport">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><DocumentAdd /></el-icon>
          新建文档
        </el-button>
      </div>
    </div>

    <!-- 搜索区域 -->
    <div class="search-section">
      <el-input
        v-model="searchText"
        placeholder="搜索文档标题、内容..."
        size="large"
        style="width: 500px"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button @click="handleSearch">搜索</el-button>
        </template>
      </el-input>
      
      <div class="search-tags">
        <el-tag 
          v-for="tag in popularTags" 
          :key="tag" 
          : closable
          @close="handleRemoveTag(tag)"
          @click="handleTagClick(tag)"
        >
          {{ tag }}
        </el-tag>
        <el-button text size="small" @click="showTagDialog = true">
          <el-icon><Plus /></el-icon>
          添加标签
        </el-button>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
      <!-- 左侧分类导航 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <span>文档分类</span>
          <el-button text size="small" @click="showCategoryDialog = true">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
        
        <el-menu 
          :default-active="activeCategory" 
          @select="handleCategorySelect"
          class="category-menu"
        >
          <el-menu-item index="all">
            <el-icon><FolderOpened /></el-icon>
            <span>全部文档</span>
            <el-badge :value="totalDocs" type="info" />
          </el-menu-item>
          <el-menu-item-group title="分类">
            <el-menu-item 
              v-for="category in categories" 
              :key="category.id"
              :index="String(category.id)"
            >
              <el-icon><Folder /></el-icon>
              <span>{{ category.name }}</span>
              <el-badge :value="category.count" type="info" />
            </el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="快捷入口">
            <el-menu-item index="favorite">
              <el-icon><Star /></el-icon>
              <span>我的收藏</span>
            </el-menu-item>
            <el-menu-item index="recent">
              <el-icon><Clock /></el-icon>
              <span>最近浏览</span>
            </el-menu-item>
            <el-menu-item index="my">
              <el-icon><Document /></el-icon>
              <span>我的文档</span>
            </el-menu-item>
          </el-menu-item-group>
        </el-menu>
      </div>

      <!-- 右侧文档列表 -->
      <div class="main-content">
        <!-- 筛选工具栏 -->
        <div class="filter-bar">
          <div class="filter-left">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button value="list">
                <el-icon><List /></el-icon>
              </el-radio-button>
              <el-radio-button value="grid">
                <el-icon><Grid /></el-icon>
              </el-radio-button>
            </el-radio-group>

            <el-select v-model="sortBy" style="width: 120px" @change="handleSortChange">
              <el-option label="最新发布" value="created" />
              <el-option label="最近更新" value="updated" />
              <el-option label="浏览最多" value="views" />
              <el-option label="评分最高" value="rating" />
            </el-select>
          </div>

          <div class="filter-right">
            <span class="result-count">共 {{ totalDocs }} 篇文档</span>
            <el-button text @click="handleRefresh">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>

        <!-- 网格视图 -->
        <div class="docs-grid" v-if="viewMode === 'grid'">
          <div 
            v-for="doc in docsData" 
            :key="doc.id"
            class="doc-card"
            @click="handleViewDoc(doc)"
          >
            <div class="doc-header">
              <div class="doc-icon" :class="doc.category.toLowerCase()">
                <el-icon><component :is="getCategoryIcon(doc.category)" /></el-icon>
              </div>
              <div class="doc-actions">
                <el-tooltip content="收藏" placement="top">
                  <el-button text size="small" @click.stop="handleToggleFavorite(doc)">
                    <el-icon :class="{ 'is-favorite': doc.favorite }">
                      <Star :filled="doc.favorite" />
                    </el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
            <div class="doc-body">
              <h4 class="doc-title">{{ doc.title }}</h4>
              <p class="doc-summary">{{ doc.summary }}</p>
              <div class="doc-tags">
                <el-tag 
                  v-for="tag in doc.tags" 
                  :key="tag" 
                  size="small" 
                  effect="plain"
                  @click.stop="handleTagClick(tag)"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </div>
            <div class="doc-footer">
              <div class="doc-meta">
                <span class="meta-item">
                  <el-icon><User /></el-icon>
                  {{ doc.author }}
                </span>
                <span class="meta-item">
                  <el-icon><View /></el-icon>
                  {{ doc.views }}
                </span>
                <span class="meta-item">
                  <el-icon><Clock /></el-icon>
                  {{ doc.updatedAt }}
                </span>
              </div>
              <div class="doc-rating">
                <el-rate v-model="doc.rating" disabled text-color="#ff9900" />
              </div>
            </div>
          </div>
        </div>

        <!-- 列表视图 -->
        <div class="docs-table" v-else>
          <el-table 
            v-loading="loading" 
            :data="docsData" 
            stripe
            @row-click="handleViewDoc"
          >
            <el-table-column label="文档信息" min-width="300">
              <template #default="{ row }">
                <div class="doc-info-cell">
                  <div class="doc-icon-small" :class="row.category.toLowerCase()">
                    <el-icon><component :is="getCategoryIcon(row.category)" /></el-icon>
                  </div>
                  <div class="doc-text">
                    <div class="doc-title">{{ row.title }}</div>
                    <div class="doc-summary">{{ row.summary }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="分类" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ row.category }}</el-tag>
              </template>
            </el-table-column>

            <el-table-column label="标签" width="180">
              <template #default="{ row }">
                <div class="tags-cell">
                  <el-tag 
                    v-for="tag in row.tags.slice(0, 3)" 
                    :key="tag" 
                    size="small" 
                    effect="plain"
                  >
                    {{ tag }}
                  </el-tag>
                  <el-tag v-if="row.tags.length > 3" size="small">
                    +{{ row.tags.length - 3 }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="作者" width="100">
              <template #default="{ row }">
                <span>{{ row.author }}</span>
              </template>
            </el-table-column>

            <el-table-column label="浏览" width="80">
              <template #default="{ row }">
                <span>{{ row.views }}</span>
              </template>
            </el-table-column>

            <el-table-column label="评分" width="100">
              <template #default="{ row }">
                <el-rate v-model="row.rating" disabled size="small" />
              </template>
            </el-table-column>

            <el-table-column label="更新时间" width="120">
              <template #default="{ row }">
                <span>{{ row.updatedAt }}</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-tooltip content="编辑" placement="top">
                    <el-button text type="primary" size="small" @click.stop="handleEditDoc(row)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="收藏" placement="top">
                    <el-button text size="small" @click.stop="handleToggleFavorite(row)">
                      <el-icon :class="{ 'is-favorite': row.favorite }">
                        <Star :filled="row.favorite" />
                      </el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-dropdown trigger="click" @command="(cmd) => handleDocCommand(cmd, row)" @click.stop>
                    <el-button text size="small">
                      <el-icon><MoreFilled /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="view">查看详情</el-dropdown-item>
                        <el-dropdown-item command="copy">复制链接</el-dropdown-item>
                        <el-dropdown-item command="export">导出</el-dropdown-item>
                        <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="table-footer">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[12, 24, 48, 96]"
              :total="totalDocs"
              layout="sizes, prev, pager, next"
              @size-change="handleSizeChange"
              @current-change="handlePageChange"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 文档预览抽屉 -->
    <el-drawer v-model="showDocDrawer" :title="currentDoc?.title" size="800px">
      <div class="doc-preview" v-if="currentDoc">
        <div class="preview-header">
          <div class="preview-badges">
            <el-tag>{{ currentDoc.category }}</el-tag>
            <el-tag v-for="tag in currentDoc.tags" :key="tag" size="small">{{ tag }}</el-tag>
          </div>
          <div class="preview-meta">
            <span>作者: {{ currentDoc.author }}</span>
            <span>浏览: {{ currentDoc.views }}</span>
            <span>更新: {{ currentDoc.updatedAt }}</span>
          </div>
        </div>

        <el-divider />

        <div class="preview-content">
          <h3>摘要</h3>
          <p>{{ currentDoc.summary }}</p>
          
          <h3>正文</h3>
          <div v-html="currentDoc.content"></div>
        </div>

        <el-divider />

        <div class="preview-actions">
          <el-button type="primary" @click="handleEditDoc(currentDoc)">
            <el-icon><Edit /></el-icon>
            编辑文档
          </el-button>
          <el-button @click="handleToggleFavorite(currentDoc)">
            <el-icon><Star /></el-icon>
            {{ currentDoc.favorite ? '取消收藏' : '收藏' }}
          </el-button>
          <el-rate v-model="currentDoc.rating" allow-half @change="handleRateChange" />
        </div>

        <div class="preview-comments">
          <h4>评论 ({{ currentDoc.comments?.length || 0 }})</h4>
          <div class="comment-list">
            <div v-for="(comment, index) in currentDoc.comments" :key="index" class="comment-item">
              <div class="comment-header">
                <el-avatar :size="28" :icon="UserFilled" />
                <span class="comment-author">{{ comment.author }}</span>
                <span class="comment-time">{{ comment.time }}</span>
              </div>
              <div class="comment-text">{{ comment.text }}</div>
            </div>
          </div>
          <div class="comment-input">
            <el-input
              v-model="commentText"
              type="textarea"
              :rows="3"
              placeholder="添加评论..."
            />
            <el-button type="primary" @click="handleAddComment" style="margin-top: 10px;">
              发表评论
            </el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 创建文档对话框 -->
    <el-dialog 
      v-model="showCreateDialog" 
      title="新建文档" 
      width="800px"
      :close-on-click-modal="false"
    >
      <el-form :model="docForm" label-width="100px" :rules="formRules" ref="docFormRef">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="docForm.title" placeholder="请输入文档标题" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="文档分类" prop="category">
          <el-select v-model="docForm.category" placeholder="选择分类" style="width: 100%">
            <el-option 
              v-for="cat in categories" 
              :key="cat.id" 
              :label="cat.name" 
              :value="cat.name" 
            />
          </el-select>
        </el-form-item>

        <el-form-item label="文档标签" prop="tags">
          <el-select 
            v-model="docForm.tags" 
            multiple 
            filterable 
            allow-create
            placeholder="选择或输入标签"
            style="width: 100%"
          >
            <el-option 
              v-for="tag in popularTags" 
              :key="tag" 
              :label="tag" 
              :value="tag" 
            />
          </el-select>
        </el-form-item>

        <el-form-item label="文档摘要" prop="summary">
          <el-input 
            v-model="docForm.summary" 
            type="textarea" 
            :rows="3" 
            placeholder="请输入文档摘要"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="文档内容" prop="content">
          <el-input 
            v-model="docForm.content" 
            type="textarea" 
            :rows="10" 
            placeholder="请输入文档内容，支持富文本"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button @click="handleSaveDraft">保存草稿</el-button>
        <el-button type="primary" @click="handleSubmitDoc">发布文档</el-button>
      </template>
    </el-dialog>

    <!-- 标签管理对话框 -->
    <el-dialog v-model="showTagDialog" title="标签管理" width="500px">
      <div class="tag-management">
        <div class="tag-input-section">
          <el-input v-model="newTag" placeholder="输入新标签名称" style="width: 200px" />
          <el-button type="primary" @click="handleAddTag">添加</el-button>
        </div>
        <div class="tag-list">
          <el-tag
            v-for="tag in popularTags"
            :key="tag"
            closable
            @close="handleRemoveTag(tag)"
          >
            {{ tag }}
          </el-tag>
        </div>
      </div>
    </el-dialog>

    <!-- 分类管理对话框 -->
    <el-dialog v-model="showCategoryDialog" title="分类管理" width="500px">
      <div class="category-management">
        <div class="category-input-section">
          <el-input v-model="newCategory" placeholder="输入新分类名称" style="width: 200px" />
          <el-button type="primary" @click="handleAddCategory">添加</el-button>
        </div>
        <el-table :data="categories" stripe>
          <el-table-column prop="name" label="分类名称" />
          <el-table-column prop="count" label="文档数" width="100" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button text size="small" type="primary" @click="handleEditCategory(row)">
                编辑
              </el-button>
              <el-button text size="small" type="danger" @click="handleDeleteCategory(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Download, DocumentAdd, Plus, Folder, FolderOpened, Star, Clock,
  List, Grid, View, User, UserFilled, Edit, MoreFilled, Document
} from '@element-plus/icons-vue'

// 状态
const loading = ref(false)
const docsData = ref([])
const showDocDrawer = ref(false)
const showCreateDialog = ref(false)
const showTagDialog = ref(false)
const showCategoryDialog = ref(false)
const viewMode = ref('grid')
const currentDoc = ref(null)
const commentText = ref('')
const docFormRef = ref(null)

// 搜索和筛选
const searchText = ref('')
const activeCategory = ref('all')
const sortBy = ref('updated')

// 分页
const currentPage = ref(1)
const pageSize = ref(12)
const totalDocs = ref(0)

// 分类和标签
const categories = ref([
  { id: 1, name: '故障处理', count: 12 },
  { id: 2, name: '变更记录', count: 8 },
  { id: 3, name: '最佳实践', count: 15 },
  { id: 4, name: '操作手册', count: 10 },
  { id: 5, name: '常见问题', count: 20 }
])

const popularTags = ref(['服务器', '数据库', '网络', '安全', '备份', '监控'])

const newTag = ref('')
const newCategory = ref('')

// 文档表单
const docForm = reactive({
  title: '',
  category: '',
  tags: [],
  summary: '',
  content: ''
})

// 表单验证
const formRules = {
  title: [{ required: true, message: '请输入文档标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择文档分类', trigger: 'change' }],
  summary: [{ required: true, message: '请输入文档摘要', trigger: 'blur' }]
}

// 模拟文档数据
const mockDocs = [
  {
    id: 1,
    title: 'Windows服务器CPU占用率过高的排查与解决',
    category: '故障处理',
    tags: ['服务器', 'Windows', 'CPU', '故障排查'],
    summary: '详细介绍Windows服务器CPU占用率过高的常见原因及排查步骤，包括进程分析、性能监控工具使用等。',
    content: '<h2>概述</h2><p>本文档介绍Windows服务器CPU占用率过高的排查与解决方法。</p><h2>排查步骤</h2><p>1. 打开任务管理器查看进程</p><p>2. 使用性能监控器分析</p><p>3. 检查服务日志</p>',
    author: '张三',
    views: 1256,
    rating: 4.5,
    updatedAt: '2024-05-03',
    favorite: false,
    comments: [
      { author: '李四', time: '2024-05-04', text: '很实用的文档，帮助我解决了问题。' }
    ]
  },
  {
    id: 2,
    title: 'CentOS系统磁盘空间扩容操作手册',
    category: '操作手册',
    tags: ['Linux', '磁盘', '扩容'],
    summary: '详细说明CentOS系统如何进行磁盘空间扩容，包括LVM配置、文件系统扩展等操作步骤。',
    content: '<h2>概述</h2><p>本文档介绍CentOS磁盘扩容操作步骤。</p>',
    author: '李四',
    views: 892,
    rating: 4.8,
    updatedAt: '2024-05-02',
    favorite: true,
    comments: []
  },
  {
    id: 3,
    title: '数据库连接池配置最佳实践',
    category: '最佳实践',
    tags: ['数据库', '性能', '配置'],
    summary: '介绍数据库连接池的配置原则和最佳实践，包括连接数设置、超时配置、监控指标等。',
    content: '<h2>概述</h2><p>本文档介绍数据库连接池配置的最佳实践。</p>',
    author: '王五',
    views: 1567,
    rating: 4.6,
    updatedAt: '2024-05-01',
    favorite: false,
    comments: []
  },
  {
    id: 4,
    title: '网络安全设备巡检标准流程',
    category: '操作手册',
    tags: ['安全', '网络', '巡检'],
    summary: '网络安全设备日常巡检的标准操作流程，包括防火墙、入侵检测、VPN设备的巡检要点。',
    content: '<h2>概述</h2><p>本文档介绍网络安全设备巡检流程。</p>',
    author: '赵六',
    views: 634,
    rating: 4.2,
    updatedAt: '2024-04-30',
    favorite: false,
    comments: []
  },
  {
    id: 5,
    title: 'VMware虚拟化平台常见故障处理',
    category: '故障处理',
    tags: ['虚拟化', 'VMware', '故障'],
    summary: '汇总VMware虚拟化平台常见故障及处理方法，包括vCenter、ESXi主机的故障排查。',
    content: '<h2>概述</h2><p>本文档介绍VMware故障处理方法。</p>',
    author: '孙七',
    views: 1089,
    rating: 4.4,
    updatedAt: '2024-04-29',
    favorite: false,
    comments: []
  },
  {
    id: 6,
    title: '数据备份与恢复方案设计指南',
    category: '最佳实践',
    tags: ['备份', '恢复', '数据安全'],
    summary: '介绍数据备份方案的设计原则，包括备份策略、恢复测试、异地备份等内容。',
    content: '<h2>概述</h2><p>本文档介绍数据备份方案设计。</p>',
    author: '周八',
    views: 2345,
    rating: 4.9,
    updatedAt: '2024-04-28',
    favorite: true,
    comments: []
  },
  {
    id: 7,
    title: '交换机端口环路故障排查',
    category: '故障处理',
    tags: ['网络', '交换机', '环路'],
    summary: '详细说明如何排查和解决网络交换机端口环路导致的网络故障。',
    content: '<h2>概述</h2><p>本文档介绍交换机环路故障排查。</p>',
    author: '吴九',
    views: 567,
    rating: 4.3,
    updatedAt: '2024-04-27',
    favorite: false,
    comments: []
  },
  {
    id: 8,
    title: '监控系统告警规则配置手册',
    category: '操作手册',
    tags: ['监控', '告警', '配置'],
    summary: '详细介绍监控系统告警规则的配置方法，包括阈值设置、通知渠道、告警升级等。',
    content: '<h2>概述</h2><p>本文档介绍告警规则配置。</p>',
    author: '郑十',
    views: 789,
    rating: 4.1,
    updatedAt: '2024-04-26',
    favorite: false,
    comments: []
  }
]

// 辅助函数
const getCategoryIcon = (category) => {
  const iconMap = {
    '故障处理': 'Warning',
    '变更记录': 'Edit',
    '最佳实践': 'CircleCheck',
    '操作手册': 'Document',
    '常见问题': 'QuestionFilled'
  }
  return iconMap[category] || 'Document'
}

// 加载文档数据
const loadDocs = async () => {
  loading.value = true
  try {
    docsData.value = [...mockDocs]
    totalDocs.value = mockDocs.length
  } catch (error) {
    console.error('Failed to load docs:', error)
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

// 事件处理
const handleSearch = () => {
  currentPage.value = 1
  loadDocs()
}

const handleRefresh = () => {
  loadDocs()
  ElMessage.success('刷新成功')
}

const handleCategorySelect = (index) => {
  activeCategory.value = index
  currentPage.value = 1
  loadDocs()
}

const handleSortChange = () => {
  loadDocs()
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadDocs()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  loadDocs()
}

const handleViewDoc = (doc) => {
  currentDoc.value = doc
  commentText.value = ''
  showDocDrawer.value = true
}

const handleEditDoc = (doc) => {
  docForm.title = doc.title
  docForm.category = doc.category
  docForm.tags = [...doc.tags]
  docForm.summary = doc.summary
  docForm.content = doc.content
  showCreateDialog.value = true
  showDocDrawer.value = false
}

const handleToggleFavorite = (doc) => {
  doc.favorite = !doc.favorite
  ElMessage.success(doc.favorite ? '已收藏' : '已取消收藏')
}

const handleDocCommand = (command, doc) => {
  switch (command) {
    case 'view': handleViewDoc(doc); break
    case 'copy': 
      navigator.clipboard.writeText(window.location.origin + '/knowledge/' + doc.id)
      ElMessage.success('链接已复制')
      break
    case 'export': ElMessage.success('导出成功'); break
    case 'delete': 
      ElMessageBox.confirm('确定要删除此文档吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        docsData.value = docsData.value.filter(d => d.id !== doc.id)
        ElMessage.success('文档已删除')
      }).catch(() => {})
      break
  }
}

const handleAddComment = () => {
  if (!commentText.value.trim()) {
    ElMessage.warning('请输入评论内容')
    return
  }
  
  if (!currentDoc.value.comments) {
    currentDoc.value.comments = []
  }
  
  currentDoc.value.comments.push({
    author: '当前用户',
    time: new Date().toLocaleDateString('zh-CN'),
    text: commentText.value
  })
  
  commentText.value = ''
  ElMessage.success('评论已添加')
}

const handleRateChange = (rating) => {
  ElMessage.success(`文档评分: ${rating}`)
}

const handleSubmitDoc = async () => {
  if (!docFormRef.value) return
  
  await docFormRef.value.validate((valid) => {
    if (valid) {
      const newDoc = {
        id: mockDocs.length + 1,
        title: docForm.title,
        category: docForm.category,
        tags: docForm.tags,
        summary: docForm.summary,
        content: docForm.content,
        author: '当前用户',
        views: 0,
        rating: 0,
        updatedAt: new Date().toLocaleDateString('zh-CN'),
        favorite: false,
        comments: []
      }
      
      docsData.value.unshift(newDoc)
      totalDocs.value++
      
      showCreateDialog.value = false
      Object.keys(docForm).forEach(key => docForm[key] = Array.isArray(docForm[key]) ? [] : '')
      
      ElMessage.success('文档发布成功')
    }
  })
}

const handleSaveDraft = () => {
  ElMessage.success('草稿已保存')
}

const handleTagClick = (tag) => {
  if (!docForm.tags.includes(tag)) {
    docForm.tags.push(tag)
  }
}

const handleAddTag = () => {
  if (newTag.value && !popularTags.value.includes(newTag.value)) {
    popularTags.value.push(newTag.value)
    newTag.value = ''
  }
}

const handleRemoveTag = (tag) => {
  popularTags.value = popularTags.value.filter(t => t !== tag)
}

const handleAddCategory = () => {
  if (newCategory.value) {
    categories.value.push({
      id: categories.value.length + 1,
      name: newCategory.value,
      count: 0
    })
    newCategory.value = ''
  }
}

const handleEditCategory = (category) => {
  ElMessage.info('编辑分类: ' + category.name)
}

const handleDeleteCategory = (category) => {
  ElMessageBox.confirm('确定要删除此分类吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    categories.value = categories.value.filter(c => c.id !== category.id)
    ElMessage.success('分类已删除')
  }).catch(() => {})
}

const handleExport = () => {
  ElMessage.success('导出成功')
}

// 初始化
onMounted(() => {
  loadDocs()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.knowledge-page {
  animation: fadeIn 0.3s ease;
}

// ========== 页面头部 ==========
.page-header {
  @include flex-between;
  margin-bottom: $spacing-xl;

  .page-header-left {
    .page-title {
      font-size: $font-size-xxl;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin: 0 0 4px 0;
    }

    .page-subtitle {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin: 0;
    }
  }

  .page-header-actions {
    display: flex;
    gap: $spacing-sm;
  }
}

// ========== 搜索区域 ==========
.search-section {
  margin-bottom: $spacing-xl;

  .search-tags {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-top: $spacing-md;
    flex-wrap: wrap;

    .el-tag {
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        transform: translateY(-1px);
      }
    }
  }
}

// ========== 内容区域 ==========
.content-area {
  display: flex;
  gap: $spacing-xl;
}

// ========== 侧边栏 ==========
.sidebar {
  width: 260px;
  flex-shrink: 0;
  background: $bg-container;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  box-shadow: $shadow-sm;
}

.sidebar-header {
  @include flex-between;
  padding-bottom: $spacing-md;
  margin-bottom: $spacing-md;
  border-bottom: 1px solid $border-light;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.category-menu {
  border-right: none;

  :deep(.el-menu-item) {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    height: 40px;
    line-height: 40px;

    .el-badge {
      margin-left: auto;
    }
  }
}

// ========== 主内容区 ==========
.main-content {
  flex: 1;
  min-width: 0;
}

// ========== 筛选工具栏 ==========
.filter-bar {
  @include flex-between;
  padding: $spacing-md;
  background: $bg-container;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-lg;
  box-shadow: $shadow-sm;

  .filter-left {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }

  .filter-right {
    display: flex;
    align-items: center;
    gap: $spacing-md;

    .result-count {
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }
}

// ========== 文档网格 ==========
.docs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: $spacing-lg;
}

.doc-card {
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  cursor: pointer;
  transition: all 0.25s ease;
  overflow: hidden;
  animation: slideInUp 0.4s ease-out backwards;

  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-base;
  }
}

.doc-header {
  @include flex-between;
  padding: $spacing-md;
  border-bottom: 1px solid $border-light;
}

.doc-icon {
  width: 40px;
  height: 40px;
  border-radius: $border-radius-md;
  @include flex-center;
  font-size: 20px;
  color: #fff;

  &.故障处理 { background: linear-gradient(135deg, #f53f3f, #ff7875); }
  &.变更记录 { background: linear-gradient(135deg, #ff7d00, #ff9d00); }
  &.最佳实践 { background: linear-gradient(135deg, #00b42a, #23c343); }
  &.操作手册 { background: linear-gradient(135deg, #165dff, #4080ff); }
  &.常见问题 { background: linear-gradient(135deg, #722ed1, #b37feb); }
  &.默认 { background: linear-gradient(135deg, #86909c, #a6a8b6); }
}

.doc-actions {
  .is-favorite {
    color: $warning;
  }
}

.doc-body {
  padding: $spacing-md;

  .doc-title {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin: 0 0 $spacing-sm 0;
    @include multi-ellipsis(2);
  }

  .doc-summary {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin: 0 0 $spacing-md 0;
    @include multi-ellipsis(2);
  }

  .doc-tags {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs;
  }
}

.doc-footer {
  padding: $spacing-md;
  background: $bg-page;
  border-top: 1px solid $border-light;

  .doc-meta {
    display: flex;
    gap: $spacing-md;
    margin-bottom: $spacing-sm;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }
}

// ========== 文档表格 ==========
.docs-table {
  background: $bg-container;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.doc-info-cell {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.doc-icon-small {
  width: 36px;
  height: 36px;
  border-radius: $border-radius-sm;
  @include flex-center;
  color: #fff;
  font-size: 16px;
  flex-shrink: 0;

  &.故障处理 { background: linear-gradient(135deg, #f53f3f, #ff7875); }
  &.变更记录 { background: linear-gradient(135deg, #ff7d00, #ff9d00); }
  &.最佳实践 { background: linear-gradient(135deg, #00b42a, #23c343); }
  &.操作手册 { background: linear-gradient(135deg, #165dff, #4080ff); }
  &.常见问题 { background: linear-gradient(135deg, #722ed1, #b37feb); }
}

.doc-text {
  .doc-title {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: 2px;
  }

  .doc-summary {
    font-size: $font-size-xs;
    color: $text-secondary;
    @include multi-ellipsis(1);
  }
}

.tags-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
}

// ========== 表格底部 ==========
.table-footer {
  @include flex-center;
  padding: $spacing-md;
  border-top: 1px solid $border-light;
}

// ========== 文档预览 ==========
.doc-preview {
  .preview-header {
    margin-bottom: $spacing-lg;

    .preview-badges {
      display: flex;
      gap: $spacing-sm;
      margin-bottom: $spacing-md;
      flex-wrap: wrap;
    }

    .preview-meta {
      display: flex;
      gap: $spacing-lg;
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }

  .preview-content {
    h3 {
      font-size: $font-size-base;
      font-weight: $font-weight-semibold;
      color: $text-primary;
      margin: $spacing-lg 0 $spacing-md 0;
    }

    p {
      font-size: $font-size-sm;
      color: $text-regular;
      line-height: 1.8;
    }
  }

  .preview-actions {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    margin-bottom: $spacing-xl;
  }

  .preview-comments {
    h4 {
      font-size: $font-size-base;
      font-weight: $font-weight-medium;
      margin-bottom: $spacing-md;
    }
  }
}

.comment-list {
  margin-bottom: $spacing-lg;
}

.comment-item {
  padding: $spacing-md;
  background: $bg-page;
  border-radius: $border-radius-md;
  margin-bottom: $spacing-sm;

  .comment-header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-sm;

    .comment-author {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .comment-time {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }

  .comment-text {
    font-size: $font-size-sm;
    color: $text-regular;
    line-height: 1.6;
  }
}

// ========== 标签/分类管理 ==========
.tag-management, .category-management {
  .tag-input-section, .category-input-section {
    display: flex;
    gap: $spacing-md;
    margin-bottom: $spacing-lg;
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-sm;
  }
}

// ========== 动画 ==========
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// ========== 响应式 ==========
@include respond-to('xl') {
  .content-area {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
  }

  .docs-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  }
}

@include respond-to('lg') {
  .docs-grid {
    grid-template-columns: 1fr;
  }
}
</style>