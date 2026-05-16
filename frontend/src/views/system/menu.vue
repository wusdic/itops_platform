<template>
  <div class="page-container">
    <n-card title="菜单管理" :bordered="false">
      <template #header-extra>
        <n-button type="primary" @click="handleAdd(null)">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加菜单
        </n-button>
      </template>

      <n-tree
        block-line
        :data="menuTree"
        :default-expanded-keys="['monitoring', 'workorder', 'system']"
        :selected-keys="[]"
        key-field="key"
        label-field="label"
        children-field="children"
      >
        <template #label="{ label, data }">
          <n-space>
            <n-icon v-if="data.icon"><component :is="data.icon" /></n-icon>
            <span>{{ label }}</span>
            <n-tag v-if="data.type === 'btn'" size="tiny" type="warning">按钮</n-tag>
          </n-space>
        </template>
      </n-tree>
    </n-card>
  </div>
</template>

<script setup>
import { ref, h } from 'vue'
import { NCard, NButton, NTree, NSpace, NTag, NIcon, useMessage } from 'naive-ui'
import { AddOutline, DashboardOutline, ServerOutline, AlertCircleOutline, ConstructOutline, FolderOutline, SettingsOutline, PeopleOutline, KeyOutline, FlashOutline } from '@vicons/ionicons5'

const message = useMessage()

const menuTree = [
  {
    key: 'dashboard', label: '仪表盘', icon: DashboardOutline, children: [
      { key: 'dashboard:index', label: '总览', path: '/dashboard' }
    ]
  },
  {
    key: 'monitoring', label: '监控中心', icon: ServerOutline, children: [
      { key: 'monitoring:devices', label: '设备管理', path: '/monitoring/devices' },
      { key: 'monitoring:alerts', label: '告警管理', path: '/monitoring/alerts' },
      { key: 'monitoring:performance', label: '性能监控', path: '/monitoring/performance' }
    ]
  },
  {
    key: 'workorder', label: '工单管理', icon: ConstructOutline, children: [
      { key: 'workorder:list', label: '工单列表', path: '/workorder/list' },
      { key: 'workorder:create', label: '创建工单', path: '/workorder/create' },
      { key: 'workorder:my', label: '我的工单', path: '/workorder/my' }
    ]
  },
  {
    key: 'ai', label: 'AI 助手', icon: FlashOutline, children: [
      { key: 'ai:chat', label: 'AI 聊天', path: '/ai/chat' },
      { key: 'ai:copilot', label: 'AI 分类', path: '/ai/copilot' }
    ]
  },
  {
    key: 'knowledge', label: '知识库', icon: FolderOutline, children: [
      { key: 'knowledge:list', label: '知识文档', path: '/knowledge/list' },
      { key: 'knowledge:cases', label: '故障案例', path: '/knowledge/cases' }
    ]
  },
  {
    key: 'automation', label: '自动化运维', icon: FlashOutline, children: [
      { key: 'automation:script', label: '脚本管理', path: '/automation/script' },
      { key: 'automation:task', label: '任务管理', path: '/automation/task' },
      { key: 'automation:execute', label: '执行记录', path: '/automation/execute' }
    ]
  },
  {
    key: 'backup', label: '备份恢复', icon: ServerOutline, children: [
      { key: 'backup:restore', label: '备份管理', path: '/backup/restore' }
    ]
  },
  {
    key: 'system', label: '系统管理', icon: SettingsOutline, children: [
      { key: 'system:user', label: '用户管理', path: '/system/user' },
      { key: 'system:role', label: '角色管理', path: '/system/role' },
      { key: 'system:menu', label: '菜单管理', path: '/system/menu' },
      { key: 'system:config', label: '参数配置', path: '/system/config' },
      { key: 'system:dict', label: '字典管理', path: '/system/dict' }
    ]
  }
]

function handleAdd(parent) {
  message.info('添加菜单功能开发中')
}
</script>

<style scoped>
.page-container { padding: 16px; }
</style>
