<template>
  <div class="app-layout" :class="[themeClass, { 'is-collapse': isCollapse }]">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <!-- Logo区域 -->
      <div class="sidebar-header">
        <div class="logo" @click="goHome">
          <div class="logo-icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="8" :fill="accentColor"/>
              <path d="M8 12L16 8L24 12V20L16 24L8 20V12Z" stroke="white" stroke-width="2"/>
              <circle cx="16" cy="16" r="3" fill="white"/>
            </svg>
          </div>
          <span class="logo-text" v-show="!isCollapse">智能运维平台</span>
        </div>
        <button class="collapse-btn" @click="toggleCollapse" title="收起/展开">
          <el-icon :size="16"><Expand v-if="isCollapse"/><Fold v-else/></el-icon>
        </button>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <div
          v-for="group in navGroups"
          :key="group.key"
          class="nav-group"
        >
          <div class="nav-group-title" v-show="!isCollapse">{{ group.label }}</div>
          <div
            v-for="item in group.items"
            :key="item.path"
            class="nav-item"
            :class="{ active: isActive(item) }"
            @click="navigate(item)"
            :title="isCollapse ? item.label : ''"
          >
            <el-icon :size="18"><component :is="item.icon"/></el-icon>
            <span class="nav-label" v-show="!isCollapse">{{ item.label }}</span>
            <span class="nav-badge" v-if="item.badge && !isCollapse">{{ item.badge }}</span>
          </div>
        </div>
      </nav>

      <!-- 快捷操作 -->
      <div class="sidebar-quick-actions" v-show="!isCollapse">
        <div class="quick-action-label">快捷操作</div>
        <div class="quick-actions-grid">
          <div class="quick-action-btn" @click="createWorkOrder" title="创建工单">
            <el-icon><Edit /></el-icon>
          </div>
          <div class="quick-action-btn" @click="quickCollect" title="快速采集">
            <el-icon><Download /></el-icon>
          </div>
          <div class="quick-action-btn" @click="openAIPanel" title="AI助手">
            <el-icon><MagicStick /></el-icon>
          </div>
          <div class="quick-action-btn" @click="showShortcuts" title="快捷键">
            <el-icon><EditPen /></el-icon>
          </div>
        </div>
      </div>

      <!-- 底部用户信息 -->
      <div class="sidebar-footer">
        <div class="user-card" @click="showUserMenu = true">
          <el-avatar :size="32" class="user-avatar">
            <el-icon :size="18"><User /></el-icon>
          </el-avatar>
          <div class="user-info" v-show="!isCollapse">
            <span class="user-name">{{ username }}</span>
            <span class="user-role">{{ userRoleText }}</span>
          </div>
          <el-icon :size="14" class="user-arrow" v-show="!isCollapse"><ArrowRight /></el-icon>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-container">
      <!-- 顶部标签页 -->
      <header class="top-tabs">
        <div class="tabs-scroll">
          <div
            v-for="(tab, index) in tabList"
            :key="tab.path"
            class="tab-item"
            :class="{ active: currentTab === tab.path }"
            @click="switchTab(tab)"
          >
            <el-icon :size="14"><component :is="tab.icon"/></el-icon>
            <span>{{ tab.label }}</span>
            <el-icon class="tab-close" :size="12" @click.stop="closeTab(tab, index)"><Close /></el-icon>
          </div>
        </div>
        <div class="tabs-actions">
          <el-dropdown trigger="click" @command="handleTabCommand">
            <el-button size="small" text>
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="close-others">关闭其他</el-dropdown-item>
                <el-dropdown-item command="close-all">关闭全部</el-dropdown-item>
                <el-dropdown-item command="refresh">刷新页面</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="main-content">
        <router-view v-slot="{ Component, route }">
          <transition :name="transitionName" mode="out-in">
            <component :is="Component" :key="route.path"/>
          </transition>
        </router-view>
      </main>
    </div>

    <!-- 右侧设置面板 -->
    <transition name="slide-right">
      <aside class="settings-panel" v-if="showSettings">
        <div class="settings-header">
          <h3>偏好设置</h3>
          <el-button text @click="showSettings = false">
            <el-icon :size="18"><Close /></el-icon>
          </el-button>
        </div>
        <div class="settings-content">
          <!-- 主题设置 -->
          <div class="settings-section">
            <h4>主题</h4>
            <div class="theme-options">
              <div
                v-for="t in themes"
                :key="t.value"
                class="theme-option"
                :class="{ active: theme === t.value }"
                @click="setTheme(t.value)"
              >
                <div class="theme-preview" :style="{ background: t.bg }">
                  <div class="theme-sidebar" :style="{ background: t.sidebar }"></div>
                </div>
                <span>{{ t.label }}</span>
              </div>
            </div>
          </div>

          <!-- 主题色设置 -->
          <div class="settings-section">
            <h4>主题色</h4>
            <div class="accent-colors">
              <div
                v-for="c in accentColors"
                :key="c.value"
                class="accent-option"
                :class="{ active: accentColor === c.value }"
                :style="{ background: c.value }"
                @click="accentColor = c.value"
                :title="c.label"
              ></div>
            </div>
          </div>

          <!-- 导航设置 -->
          <div class="settings-section">
            <h4>导航</h4>
            <div class="setting-item">
              <span>收起侧边栏</span>
              <el-switch v-model="isCollapse" @change="savePreference"/>
            </div>
            <div class="setting-item">
              <span>显示标签页</span>
              <el-switch v-model="showTabBar" @change="savePreference"/>
            </div>
          </div>

          <!-- 快捷键 -->
          <div class="settings-section">
            <h4>快捷键</h4>
            <div class="shortcut-list">
              <div class="shortcut-item">
                <span>全局搜索</span>
                <kbd>Ctrl</kbd> + <kbd>K</kbd>
              </div>
              <div class="shortcut-item">
                <span>新建工单</span>
                <kbd>Ctrl</kbd> + <kbd>N</kbd>
              </div>
              <div class="shortcut-item">
                <span>AI助手</span>
                <kbd>Ctrl</kbd> + <kbd>I</kbd>
              </div>
              <div class="shortcut-item">
                <span>设置面板</span>
                <kbd>Ctrl</kbd> + <kbd>,</kbd>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </transition>

    <!-- 遮罩层 -->
    <div class="panel-overlay" v-if="showSettings" @click="showSettings = false"></div>

    <!-- 用户菜单弹窗 -->
    <el-dialog v-model="showUserMenu" title="用户信息" width="400" :append-to-body="true">
      <div class="user-menu-content">
        <div class="user-menu-header">
          <el-avatar :size="64">
            <el-icon :size="32"><User /></el-icon>
          </el-avatar>
          <div class="user-menu-info">
            <h3>{{ username }}</h3>
            <p>{{ userRoleText }}</p>
          </div>
        </div>
        <el-divider/>
        <div class="user-menu-actions">
          <el-button @click="goProfile"><el-icon><User /></el-icon> 个人中心</el-button>
          <el-button @click="goSettings"><el-icon><Tools /></el-icon> 系统设置</el-button>
          <el-button type="danger" @click="logout"><el-icon><SwitchButton /></el-icon> 退出登录</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Fold, Expand, Odometer, Monitor, Server, Bell, Document, Reading, Folder,
  Setting, ChatDotRound, Tools, Timer, DataLine, Message, Search, Sunny, Moon,
  FullScreen, User, ArrowRight, Edit, Download, MagicStick, Close,
  MoreFilled, SwitchButton, Connection, Operation, Memo, TrendCharts, EditPen
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 主题
const theme = ref('light')
const accentColor = ref('#165dff')
const themeClass = computed(() => `theme-${theme.value}`)
const themes = [
  { value: 'light', label: '浅色', bg: '#ffffff', sidebar: '#1f1f1f' },
  { value: 'dark', label: '深色', bg: '#1a1a1a', sidebar: '#0f0f0f' },
  { value: 'auto', label: '自动', bg: 'linear-gradient(135deg, #fff 50%, #1a1a1a 50%)', sidebar: '#333' }
]

// 主题色
const accentColors = [
  { value: '#165dff', label: '科技蓝' },
  { value: '#0fc6c2', label: '碧绿' },
  { value: '#722ed1', label: '紫罗兰' },
  { value: '#fa541c', label: '火山橙' },
  { value: '#52c41a', label: '极客绿' },
  { value: '#faad14', label: '琥珀黄' },
  { value: '#f5222d', label: '中国红' },
  { value: '#1890ff', label: '天际蓝' }
]

// 布局
const isCollapse = ref(false)
const showTabBar = ref(true)

// 状态
const showSettings = ref(false)
const showUserMenu = ref(false)
const showAIPanel = ref(false)
const username = ref('管理员')
const userRole = ref('admin')
const userRoleText = computed(() => {
  const map = { admin: '系统管理员', operator: '运维人员', viewer: '访客' }
  return map[userRole.value] || userRole.value
})

// 标签页
const tabList = ref([
  { path: '/dashboard', label: '仪表盘', icon: 'Odometer' }
])
const currentTab = ref('/dashboard')
const transitionName = ref('fade-slide')

// 导航配置
const navGroups = [
  {
    key: 'overview',
    label: '概览',
    items: [
      { path: '/dashboard', label: '仪表盘', icon: 'Odometer' }
    ]
  },
  {
    key: 'monitor',
    label: '监控管理',
    items: [
      { path: '/devices', label: '设备列表', icon: 'Server', badge: 50 },
      { path: '/alerts', label: '告警中心', icon: 'Bell', badge: 3 },
      { path: '/assets', label: '资产管理', icon: 'Connection' }
    ]
  },
  {
    key: 'ops',
    label: '运维工具',
    items: [
      { path: '/workorder', label: '工单管理', icon: 'Document' },
      { path: '/scheduler', label: '任务调度', icon: 'Timer' },
      { path: '/reports', label: '报告中心', icon: 'TrendCharts' }
    ]
  },
  {
    key: 'knowledge',
    label: '知识中心',
    items: [
      { path: '/knowledge', label: '知识库', icon: 'Reading' },
      { path: '/knowledge-base', label: 'RAG知识库', icon: 'Folder' }
    ]
  },
  {
    key: 'ai',
    label: '智能助手',
    items: [
      { path: '/ai-copilot', label: 'AI助手', icon: 'ChatDotRound' }
    ]
  },
  {
    key: 'system',
    label: '系统',
    items: [
      { path: '/notifications', label: '通知渠道', icon: 'Message' },
      { path: '/settings', label: '系统设置', icon: 'Tools' }
    ]
  }
]

// 方法
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
  savePreference()
}

const isActive = (item) => route.path.startsWith(item.path)

const navigate = (item) => {
  router.push(item.path)
  addTab(item)
}

const addTab = (item) => {
  const exists = tabList.value.find(t => t.path === item.path)
  if (!exists) {
    tabList.value.push({ ...item })
  }
  currentTab.value = item.path
}

const switchTab = (tab) => {
  currentTab.value = tab.path
  router.push(tab.path)
}

const closeTab = (tab, index) => {
  tabList.value.splice(index, 1)
  if (currentTab.value === tab.path && tabList.value.length > 0) {
    const next = tabList.value[Math.min(index, tabList.value.length - 1)]
    switchTab(next)
  }
}

const handleTabCommand = (cmd) => {
  switch (cmd) {
    case 'close-others':
      tabList.value = tabList.value.filter(t => t.path === currentTab.value)
      break
    case 'close-all':
      tabList.value = [tabList.value[0]]
      switchTab(tabList.value[0])
      break
    case 'refresh':
      router.go(0)
      break
  }
}

const setTheme = (t) => {
  theme.value = t
  document.documentElement.setAttribute('data-theme', t)
  savePreference()
}

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

const savePreference = () => {
  localStorage.setItem('itops-pref', JSON.stringify({
    theme: theme.value,
    accentColor: accentColor.value,
    isCollapse: isCollapse.value,
    showTabBar: showTabBar.value
  }))
}

const loadPreference = () => {
  try {
    const pref = JSON.parse(localStorage.getItem('itops-pref') || '{}')
    if (pref.theme) theme.value = pref.theme
    if (pref.accentColor) accentColor.value = pref.accentColor
    if (pref.isCollapse !== undefined) isCollapse.value = pref.isCollapse
    if (pref.showTabBar !== undefined) showTabBar.value = pref.showTabBar
  } catch (e) {}
}

const goHome = () => router.push('/dashboard')
const goProfile = () => { showUserMenu.value = false; router.push('/profile') }
const goSettings = () => { showUserMenu.value = false; router.push('/settings') }
const logout = () => { showUserMenu.value = false; router.push('/login') }

const createWorkOrder = () => router.push('/workorder/create')
const quickCollect = () => router.push('/devices/collect')
const openAIPanel = () => router.push('/ai-copilot')
const showShortcuts = () => { showSettings.value = true }

// 键盘快捷键
const handleKeydown = (e) => {
  if (e.ctrlKey || e.metaKey) {
    switch (e.key.toLowerCase()) {
      case 'k':
        e.preventDefault()
        document.querySelector('.search-btn')?.click()
        break
      case 'n':
        e.preventDefault()
        createWorkOrder()
        break
      case 'i':
        e.preventDefault()
        openAIPanel()
        break
      case ',':
        e.preventDefault()
        showSettings.value = !showSettings.value
        break
    }
  }
}

// 路由监听
watch(() => route.path, (path) => {
  const item = findNavItem(path)
  if (item) addTab(item)
  currentTab.value = path
})

function findNavItem(path) {
  for (const group of navGroups) {
    const item = group.items.find(i => path.startsWith(i.path))
    if (item) return item
  }
  return null
}

// 初始化
onMounted(() => {
  loadPreference()
  document.documentElement.setAttribute('data-theme', theme.value)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// 监听主题色变化
watch(accentColor, () => savePreference())
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

// ========== 主布局 ==========
.app-layout {
  display: flex;
  height: 100vh;
  background: $bg-page;
  --accent: #{$primary};

  &.theme-dark {
    --bg-page: #{$dark-bg-page};
    --bg-container: #{$dark-bg-container};
    --bg-elevated: #{$dark-bg-elevated};
    --text-primary: #{$dark-text-primary};
    --text-secondary: #{$dark-text-secondary};
    --border: #{$dark-border};
  }
}

// ========== 侧边栏 ==========
.sidebar {
  width: $sidebar-width;
  height: 100vh;
  background: #1f1f1f;
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 100;

  .is-collapse & {
    width: $sidebar-collapsed-width;
  }
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $spacing-md;
  border-bottom: 1px solid rgba(255,255,255,0.06);

  .logo {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    cursor: pointer;

    .logo-icon {
      width: 32px;
      height: 32px;
      flex-shrink: 0;
    }

    .logo-text {
      font-size: $font-size-md;
      font-weight: $font-weight-semibold;
      color: #fff;
      white-space: nowrap;
    }
  }

  .collapse-btn {
    width: 28px;
    height: 28px;
    border: none;
    background: rgba(255,255,255,0.06);
    border-radius: $radius-sm;
    color: #a6a8ab;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;

    &:hover {
      background: rgba(255,255,255,0.12);
      color: #fff;
    }
  }
}

// 导航
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-sm 0;

  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
}

.nav-group {
  margin-bottom: $spacing-lg;

  .nav-group-title {
    padding: $spacing-xs $spacing-md;
    font-size: $font-size-xs;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.nav-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  margin: 2px $spacing-sm;
  border-radius: $radius-md;
  color: #a6a8ab;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;

  .el-icon {
    flex-shrink: 0;
  }

  .nav-label {
    flex: 1;
    font-size: $font-size-sm;
    white-space: nowrap;
  }

  .nav-badge {
    background: var(--accent);
    color: #fff;
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 10px;
    font-weight: 500;
  }

  &:hover {
    background: rgba(255,255,255,0.06);
    color: #fff;
  }

  &.active {
    background: var(--accent);
    color: #fff;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      background: #fff;
      border-radius: 0 2px 2px 0;
    }
  }
}

// 快捷操作
.sidebar-quick-actions {
  padding: $spacing-md;
  border-top: 1px solid rgba(255,255,255,0.06);

  .quick-action-label {
    font-size: $font-size-xs;
    color: #666;
    margin-bottom: $spacing-sm;
  }

  .quick-actions-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: $spacing-xs;
  }

  .quick-action-btn {
    width: 36px;
    height: 36px;
    border-radius: $radius-md;
    background: rgba(255,255,255,0.06);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #a6a8ab;
    cursor: pointer;
    transition: all 0.15s;

    &:hover {
      background: var(--accent);
      color: #fff;
      transform: scale(1.05);
    }
  }
}

// 用户信息
.sidebar-footer {
  padding: $spacing-md;
  border-top: 1px solid rgba(255,255,255,0.06);

  .user-card {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-sm;
    border-radius: $radius-md;
    cursor: pointer;
    transition: all 0.15s;

    &:hover {
      background: rgba(255,255,255,0.06);
    }

    .user-avatar {
      flex-shrink: 0;
      background: var(--accent);
    }

    .user-info {
      flex: 1;
      min-width: 0;

      .user-name {
        display: block;
        color: #fff;
        font-size: $font-size-sm;
        font-weight: 500;
        @include text-ellipsis;
      }

      .user-role {
        display: block;
        color: #8a8a8a;
        font-size: $font-size-xs;
      }
    }

    .user-arrow {
      color: #666;
    }
  }
}

// ========== 主容器 ==========
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-page);
}

// ========== 顶部标签页 ==========
.top-tabs {
  height: 44px;
  display: flex;
  align-items: center;
  background: var(--bg-container);
  border-bottom: 1px solid $border-light;
  padding: 0 $spacing-md;
  gap: $spacing-sm;

  .tabs-scroll {
    flex: 1;
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    overflow-x: auto;
    padding: $spacing-xs 0;

    &::-webkit-scrollbar { height: 0; }
  }

  .tab-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: $radius-md;
    font-size: $font-size-sm;
    color: $text-secondary;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
    background: transparent;
    border: 1px solid transparent;

    .el-icon { flex-shrink: 0; }

    .tab-close {
      margin-left: 4px;
      opacity: 0;
      transition: opacity 0.15s;
      padding: 2px;
      border-radius: 4px;

      &:hover {
        background: rgba(0,0,0,0.1);
      }
    }

    &:hover {
      background: $bg-page;
      color: $text-primary;

      .tab-close { opacity: 1; }
    }

    &.active {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);

      .tab-close:hover {
        background: rgba(255,255,255,0.2);
      }
    }
  }

  .tabs-actions {
    flex-shrink: 0;
  }
}

// ========== 内容区 ==========
.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: $spacing-lg;
}

// ========== 设置面板 ==========
.settings-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 320px;
  height: 100vh;
  background: var(--bg-container);
  box-shadow: -4px 0 24px rgba(0,0,0,0.1);
  z-index: 1001;
  display: flex;
  flex-direction: column;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-lg;
  border-bottom: 1px solid $border-light;

  h3 {
    margin: 0;
    font-size: $font-size-lg;
    font-weight: 600;
  }
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-lg;
}

.settings-section {
  margin-bottom: $spacing-xl;

  h4 {
    font-size: $font-size-sm;
    font-weight: 600;
    color: $text-secondary;
    margin-bottom: $spacing-md;
  }
}

// 主题选项
.theme-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-sm;
}

.theme-option {
  cursor: pointer;
  border-radius: $radius-md;
  overflow: hidden;
  border: 2px solid transparent;
  transition: all 0.15s;

  &.active {
    border-color: var(--accent);
  }

  .theme-preview {
    height: 48px;
    display: flex;

    .theme-sidebar {
      width: 32px;
      height: 100%;
    }
  }

  span {
    display: block;
    padding: $spacing-xs;
    text-align: center;
    font-size: $font-size-xs;
    background: $bg-page;
  }

  &:hover {
    transform: scale(1.02);
  }
}

// 主题色
.accent-colors {
  display: flex;
  gap: $spacing-sm;
  flex-wrap: wrap;
}

.accent-option {
  width: 32px;
  height: 32px;
  border-radius: $radius-round;
  cursor: pointer;
  transition: all 0.15s;
  border: 2px solid transparent;

  &.active {
    border-color: var(--bg-container);
    box-shadow: 0 0 0 2px var(--accent);
  }

  &:hover {
    transform: scale(1.1);
  }
}

// 设置项
.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-sm 0;
  font-size: $font-size-sm;

  span { color: $text-primary; }
}

// 快捷键列表
.shortcut-list {
  .shortcut-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-sm 0;
    font-size: $font-size-sm;

    span { color: $text-primary; }

    kbd {
      display: inline-block;
      padding: 2px 8px;
      background: $bg-page;
      border: 1px solid $border;
      border-radius: $radius-sm;
      font-size: $font-size-xs;
      font-family: inherit;
    }
  }
}

// ========== 遮罩 ==========
.panel-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  z-index: 1000;
}

// ========== 用户菜单 ==========
.user-menu-content {
  .user-menu-header {
    display: flex;
    align-items: center;
    gap: $spacing-lg;
    padding: $spacing-md 0;

    .user-menu-info {
      h3 {
        margin: 0 0 $spacing-xs 0;
        font-size: $font-size-lg;
      }
      p {
        margin: 0;
        color: $text-secondary;
        font-size: $font-size-sm;
      }
    }
  }

  .user-menu-actions {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;

    .el-button {
      justify-content: flex-start;
    }
  }
}

// ========== 过渡 ==========
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.2s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

// ========== 响应式 ==========
@media (max-width: 1024px) {
  .sidebar {
    position: fixed;
    left: -$sidebar-width;
    &.is-show { left: 0; }
  }

  .top-tabs {
    .tab-item .tab-label { display: none; }
    .tab-item.active .tab-label { display: block; }
  }
}
</style>