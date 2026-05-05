<template>
  <div class="settings-page">
    <div class="settings-container">
      <!-- 左侧导航 -->
      <aside class="settings-nav">
        <div class="nav-header">
          <div class="header-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="header-text">
            <span class="header-title">系统设置</span>
            <span class="header-subtitle">Configuration</span>
          </div>
        </div>

        <nav class="nav-list">
          <div 
            v-for="item in navItems" 
            :key="item.key"
            class="nav-item"
            :class="{ active: activeTab === item.key }"
            @click="switchTab(item.key)"
          >
            <div class="nav-icon" :style="{ background: item.gradient }">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
            <div class="nav-text">
              <div class="nav-title">{{ item.title }}</div>
              <div class="nav-desc">{{ item.desc }}</div>
            </div>
            <div class="nav-indicator" v-if="activeTab === item.key">
              <div class="indicator-bar"></div>
            </div>
          </div>
        </nav>

        <!-- 系统状态卡片 -->
        <div class="system-status-card">
          <div class="status-header">
            <span>系统状态</span>
            <div class="status-badge">
              <span class="status-dot"></span>
              在线
            </div>
          </div>
          <div class="status-body">
            <div class="status-row">
              <span class="status-label">
                <el-icon><Timer /></el-icon>
                版本
              </span>
              <span class="status-value">v1.0.0</span>
            </div>
            <div class="status-row">
              <span class="status-label">
                <el-icon><Clock /></el-icon>
                运行时间
              </span>
              <span class="status-value">{{ uptime }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右侧内容 -->
      <main class="settings-content">
        <!-- 基本信息 -->
        <div v-show="activeTab === 'basic'" class="content-section">
          <div class="section-header">
            <div class="header-info">
              <h3 class="section-title">
                <el-icon><InfoFilled /></el-icon>
                基本信息
              </h3>
              <p class="section-desc">配置系统核心信息和全局参数</p>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header">
              <div class="card-icon" style="background: linear-gradient(135deg, #409eff, #53a8ff)">
                <el-icon><OfficeBuilding /></el-icon>
              </div>
              <div class="card-title">
                <span>系统信息</span>
                <span class="card-subtitle">System Information</span>
              </div>
            </div>
            <div class="card-body">
              <el-form label-position="top" class="settings-form">
                <div class="form-grid">
                  <el-form-item label="系统名称">
                    <el-input v-model="basicSettings.systemName" placeholder="给系统起个名字" maxlength="30">
                      <template #prefix>
                        <el-icon><Edit /></el-icon>
                      </template>
                      <template #suffix>
                        <span class="input-hint">{{ basicSettings.systemName.length }}/30</span>
                      </template>
                    </el-input>
                  </el-form-item>
                  <el-form-item label="系统描述">
                    <el-input v-model="basicSettings.description" type="textarea" :rows="3" placeholder="描述系统功能用途" maxlength="200" show-word-limit />
                  </el-form-item>
                </div>
                <div class="form-grid">
                  <el-form-item label="联系邮箱">
                    <el-input v-model="basicSettings.email" placeholder="admin@example.com">
                      <template #prefix>
                        <el-icon><Message /></el-icon>
                      </template>
                    </el-input>
                  </el-form-item>
                  <el-form-item label="时区设置">
                    <el-select v-model="basicSettings.timezone" style="width: 100%">
                      <el-option label="Asia/Shanghai (UTC+8)" value="Asia/Shanghai">
                        <div class="timezone-option">
                          <span>上海</span>
                          <span class="tz-offset">UTC+8</span>
                        </div>
                      </el-option>
                      <el-option label="Asia/Beijing (UTC+8)" value="Asia/Beijing">
                        <div class="timezone-option">
                          <span>北京</span>
                          <span class="tz-offset">UTC+8</span>
                        </div>
                      </el-option>
                      <el-option label="America/New_York (UTC-5)" value="America/New_York">
                        <div class="timezone-option">
                          <span>纽约</span>
                          <span class="tz-offset">UTC-5</span>
                        </div>
                      </el-option>
                      <el-option label="Europe/London (UTC+0)" value="Europe/London">
                        <div class="timezone-option">
                          <span>伦敦</span>
                          <span class="tz-offset">UTC+0</span>
                        </div>
                      </el-option>
                    </el-select>
                  </el-form-item>
                </div>
              </el-form>
              <div class="form-actions">
                <el-button type="primary" @click="saveBasicSettings">
                  <el-icon><Check /></el-icon>
                  保存设置
                </el-button>
              </div>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header">
              <div class="card-icon" style="background: linear-gradient(135deg, #722ed1, #b37feb)">
                <el-icon><Picture /></el-icon>
              </div>
              <div class="card-title">
                <span>品牌标识</span>
                <span class="card-subtitle">Brand Identity</span>
              </div>
            </div>
            <div class="card-body">
              <div class="logo-upload-section">
                <div class="logo-preview-area">
                  <div class="logo-preview" :class="{ 'has-logo': hasLogo }">
                    <el-icon v-if="!hasLogo" :size="48"><Monitor /></el-icon>
                    <img v-else src="" alt="Logo" />
                  </div>
                  <div class="logo-info">
                    <div class="logo-name">{{ basicSettings.systemName || 'IT运维平台' }}</div>
                    <div class="logo-tagline">智能运维管理</div>
                  </div>
                </div>
                <div class="upload-actions">
                  <el-button type="primary" plain>
                    <el-icon><Upload /></el-icon>
                    上传 Logo
                  </el-button>
                  <el-button v-if="hasLogo" type="danger" plain>
                    <el-icon><Delete /></el-icon>
                    移除
                  </el-button>
                  <p class="upload-hint">支持 PNG、JPG，建议尺寸 128x128，最大 2MB</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 监控配置 -->
        <div v-show="activeTab === 'monitoring'" class="content-section">
          <div class="section-header">
            <div class="header-info">
              <h3 class="section-title">
                <el-icon><DataLine /></el-icon>
                监控配置
              </h3>
              <p class="section-desc">配置数据采集源、存储策略和性能参数</p>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header">
              <div class="card-icon" style="background: linear-gradient(135deg, #67c23a, #85ce61)">
                <el-icon><Connection /></el-icon>
              </div>
              <div class="card-title">
                <span>数据源配置</span>
                <span class="card-subtitle">Data Source Configuration</span>
              </div>
            </div>
            <div class="card-body">
              <el-form label-position="top" class="settings-form">
                <el-form-item label="数据源类型">
                  <div class="source-type-grid">
                    <div 
                      v-for="type in sourceTypes" 
                      :key="type.value"
                      class="source-type-item"
                      :class="{ active: monitoringSettings.sourceType === type.value }"
                      @click="monitoringSettings.sourceType = type.value"
                    >
                      <div class="type-icon-wrapper">
                        <div class="type-icon">
                          <el-icon><component :is="type.icon" /></el-icon>
                        </div>
                        <div class="type-check" v-if="monitoringSettings.sourceType === type.value">
                          <el-icon><Check /></el-icon>
                        </div>
                      </div>
                      <div class="type-name">{{ type.label }}</div>
                      <div class="type-desc">{{ type.desc }}</div>
                    </div>
                  </div>
                </el-form-item>
                <div class="form-grid">
                  <el-form-item label="数据源地址">
                    <el-input v-model="monitoringSettings.sourceUrl" placeholder="http://localhost:9090">
                      <template #prefix>
                        <el-icon><Link /></el-icon>
                      </template>
                    </el-input>
                  </el-form-item>
                  <el-form-item label="API Key (可选)">
                    <el-input v-model="monitoringSettings.apiKey" placeholder="输入 API Key" show-password>
                      <template #prefix>
                        <el-icon><Key /></el-icon>
                      </template>
                    </el-input>
                  </el-form-item>
                </div>
                <div class="form-grid half">
                  <el-form-item label="采集间隔">
                    <div class="input-with-unit">
                      <el-input-number v-model="monitoringSettings.interval" :min="10" :max="300" />
                      <span class="unit">秒</span>
                    </div>
                    <div class="field-hint">数据采集的频率，建议 15-60 秒</div>
                  </el-form-item>
                  <el-form-item label="数据保留天数">
                    <div class="input-with-unit">
                      <el-input-number v-model="monitoringSettings.retentionDays" :min="7" :max="365" />
                      <span class="unit">天</span>
                    </div>
                    <div class="field-hint">超出后自动清理历史数据</div>
                  </el-form-item>
                </div>
              </el-form>
              <div class="form-actions">
                <el-button @click="testConnection" :loading="testing">
                  <el-icon><Connection /></el-icon>
                  测试连接
                </el-button>
                <el-button type="primary" @click="saveMonitoringSettings">
                  <el-icon><Check /></el-icon>
                  保存设置
                </el-button>
              </div>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header">
              <div class="card-icon" style="background: linear-gradient(135deg, #e6a23c, #ebb562)">
                <el-icon><Histogram /></el-icon>
              </div>
              <div class="card-title">
                <span>存储策略</span>
                <span class="card-subtitle">Storage Policy</span>
              </div>
              <div class="card-actions">
                <el-tag size="small" type="info">自动优化</el-tag>
              </div>
            </div>
            <div class="card-body">
              <div class="storage-rules">
                <div class="rule-item" v-for="(rule, index) in storageRules" :key="index">
                  <div class="rule-header">
                    <el-tag size="small" :type="rule.enabled ? 'success' : 'info'">
                      {{ rule.period }}
                    </el-tag>
                    <span class="rule-name">{{ rule.name }}</span>
                  </div>
                  <div class="rule-info">
                    <div class="rule-desc">{{ rule.desc }}</div>
                    <div class="rule-progress" v-if="rule.enabled">
                      <div class="progress-bar">
                        <div class="progress-fill" :style="{ width: rule.usage + '%' }"></div>
                      </div>
                      <span class="progress-text">{{ rule.usage }}% 已用</span>
                    </div>
                  </div>
                  <div class="rule-action">
                    <el-switch v-model="rule.enabled" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 告警配置 -->
        <div v-show="activeTab === 'alerts'" class="content-section">
          <div class="section-header">
            <div class="header-info">
              <h3 class="section-title">
                <el-icon><Warning /></el-icon>
                告警配置
              </h3>
              <p class="section-desc">配置告警规则、阈值和通知渠道</p>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header">
              <div class="card-icon" style="background: linear-gradient(135deg, #f56c6c, #ff7875)">
                <el-icon><Bell /></el-icon>
              </div>
              <div class="card-title">
                <span>告警级别</span>
                <span class="card-subtitle">Alert Levels</span>
              </div>
            </div>
            <div class="card-body">
              <el-form label-position="top" class="settings-form">
                <el-form-item label="启用的告警级别">
                  <div class="level-cards">
                    <div 
                      v-for="level in alertLevels" 
                      :key="level.value"
                      class="level-card"
                      :class="{ active: alertSettings.levels.includes(level.value) }"
                      @click="toggleLevel(level.value)"
                    >
                      <div class="level-indicator" :style="{ background: level.color }"></div>
                      <div class="level-content">
                        <div class="level-icon" :style="{ background: level.color }">
                          <el-icon><component :is="level.icon" /></el-icon>
                        </div>
                        <div class="level-info">
                          <div class="level-name">{{ level.label }}</div>
                          <div class="level-desc">{{ level.desc }}</div>
                        </div>
                        <div class="level-check" v-if="alertSettings.levels.includes(level.value)">
                          <el-icon><Check /></el-icon>
                        </div>
                      </div>
                    </div>
                  </div>
                </el-form-item>
                
                <div class="threshold-section">
                  <div class="threshold-title">
                    <el-icon><TrendCharts /></el-icon>
                    <span>告警阈值</span>
                  </div>
                  <div class="threshold-grid">
                    <div class="threshold-item">
                      <div class="threshold-header">
                        <span class="threshold-label">CPU 使用率</span>
                        <span class="threshold-value">{{ alertSettings.cpuThreshold }}%</span>
                      </div>
                      <el-slider v-model="alertSettings.cpuThreshold" :min="0" :max="100" :step="5" :colors="['#67c23a', '#e6a23c', '#f56c6c']" />
                      <div class="threshold-range">
                        <span>0%</span>
                        <span>50%</span>
                        <span>100%</span>
                      </div>
                    </div>
                    <div class="threshold-item">
                      <div class="threshold-header">
                        <span class="threshold-label">内存使用率</span>
                        <span class="threshold-value">{{ alertSettings.memThreshold }}%</span>
                      </div>
                      <el-slider v-model="alertSettings.memThreshold" :min="0" :max="100" :step="5" :colors="['#67c23a', '#e6a23c', '#f56c6c']" />
                      <div class="threshold-range">
                        <span>0%</span>
                        <span>50%</span>
                        <span>100%</span>
                      </div>
                    </div>
                    <div class="threshold-item">
                      <div class="threshold-header">
                        <span class="threshold-label">磁盘使用率</span>
                        <span class="threshold-value">{{ alertSettings.diskThreshold }}%</span>
                      </div>
                      <el-slider v-model="alertSettings.diskThreshold" :min="0" :max="100" :step="5" :colors="['#67c23a', '#e6a23c', '#f56c6c']" />
                      <div class="threshold-range">
                        <span>0%</span>
                        <span>50%</span>
                        <span>100%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </el-form>
              <div class="form-actions">
                <el-button type="primary" @click="saveAlertSettings">
                  <el-icon><Check /></el-icon>
                  保存设置
                </el-button>
              </div>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header">
              <div class="card-icon" style="background: linear-gradient(135deg, #409eff, #53a8ff)">
                <el-icon><Message /></el-icon>
              </div>
              <div class="card-title">
                <span>通知渠道</span>
                <span class="card-subtitle">Notification Channels</span>
              </div>
            </div>
            <div class="card-body">
              <div class="channel-list">
                <div 
                  v-for="channel in notificationChannels" 
                  :key="channel.id"
                  class="channel-item"
                  :class="{ active: alertSettings.channels.includes(channel.id) }"
                >
                  <div class="channel-icon" :style="{ background: channel.color }">
                    <el-icon><component :is="channel.icon" /></el-icon>
                  </div>
                  <div class="channel-info">
                    <div class="channel-name">{{ channel.name }}</div>
                    <div class="channel-desc">{{ channel.desc }}</div>
                  </div>
                  <div class="channel-status">
                    <el-tag v-if="channel.enabled" size="small" type="success">已启用</el-tag>
                    <el-tag v-else size="small" type="info">未启用</el-tag>
                  </div>
                  <div class="channel-action">
                    <el-switch v-model="channel.enabled" @change="toggleChannel(channel.id)" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 用户管理 -->
        <div v-show="activeTab === 'users'" class="content-section">
          <div class="section-header">
            <div class="header-info">
              <h3 class="section-title">
                <el-icon><User /></el-icon>
                用户管理
              </h3>
              <p class="section-desc">管理系统用户、角色权限和访问控制</p>
            </div>
            <div class="header-actions">
              <el-button @click="exportUsers">
                <el-icon><Download /></el-icon>
                导出
              </el-button>
              <el-button type="primary" @click="showUserDialog = true">
                <el-icon><Plus /></el-icon>
                添加用户
              </el-button>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-body no-padding">
              <el-table :data="users" stripe style="width: 100%" :header-cell-style="{ background: '#f5f7fa', color: '#606266' }">
                <el-table-column label="用户信息" min-width="220">
                  <template #default="{ row }">
                    <div class="user-cell">
                      <div class="user-avatar" :style="{ background: row.avatarColor }">
                        {{ row.name.charAt(0).toUpperCase() }}
                      </div>
                      <div class="user-info">
                        <div class="user-name">{{ row.name }}</div>
                        <div class="user-email">{{ row.email }}</div>
                      </div>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="username" label="用户名" width="150">
                  <template #default="{ row }">
                    <span class="mono-text">{{ row.username }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="角色" width="140">
                  <template #default="{ row }">
                    <el-tag :type="getRoleTagType(row.role)" size="small" effect="light">
                      {{ row.roleText }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="120">
                  <template #default="{ row }">
                    <div class="status-cell">
                      <span class="status-dot" :class="row.status"></span>
                      <span>{{ row.statusText }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="最后登录" width="180">
                  <template #default="{ row }">
                    <div class="last-login-cell">
                      <el-icon><Clock /></el-icon>
                      <span>{{ row.lastLogin }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="160" fixed="right">
                  <template #default="{ row }">
                    <div class="action-buttons">
                      <el-tooltip content="编辑用户" placement="top">
                        <el-button size="small" text type="primary" @click="editUser(row)">
                          <el-icon><Edit /></el-icon>
                        </el-button>
                      </el-tooltip>
                      <el-tooltip content="重置密码" placement="top">
                        <el-button size="small" text @click="resetPassword(row)">
                          <el-icon><Key /></el-icon>
                        </el-button>
                      </el-tooltip>
                      <el-tooltip content="删除用户" placement="top">
                        <el-button size="small" text type="danger" @click="deleteUser(row)">
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </el-tooltip>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>

        <!-- 系统日志 -->
        <div v-show="activeTab === 'logs'" class="content-section">
          <div class="section-header">
            <div class="header-info">
              <h3 class="section-title">
                <el-icon><Postcard /></el-icon>
                系统日志
              </h3>
              <p class="section-desc">查看系统运行日志和操作审计记录</p>
            </div>
            <div class="header-actions">
              <el-button @click="clearOldLogs">
                <el-icon><Delete /></el-icon>
                清理旧日志
              </el-button>
              <el-button type="primary" plain @click="exportLogs">
                <el-icon><Download /></el-icon>
                导出日志
              </el-button>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header with-actions">
              <el-form :inline="true" class="log-filters">
                <el-form-item label="日志级别">
                  <el-select v-model="logSettings.level" placeholder="选择级别" style="width: 120px" clearable>
                    <el-option label="全部" value="" />
                    <el-option label="ERROR" value="error">
                      <span style="color: #f56c6c">● ERROR</span>
                    </el-option>
                    <el-option label="WARNING" value="warning">
                      <span style="color: #e6a23c">● WARNING</span>
                    </el-option>
                    <el-option label="INFO" value="info">
                      <span style="color: #409eff">● INFO</span>
                    </el-option>
                  </el-select>
                </el-form-item>
                <el-form-item label="日期范围">
                  <el-date-picker v-model="logSettings.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" style="width: 240px" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="refreshLogs">
                    <el-icon><Search /></el-icon>
                    搜索
                  </el-button>
                  <el-button @click="refreshLogs">
                    <el-icon><Refresh /></el-icon>
                  </el-button>
                </el-form-item>
              </el-form>
            </div>
            <div class="card-body no-padding">
              <el-table :data="logs" stripe style="width: 100%">
                <el-table-column label="时间" width="180">
                  <template #default="{ row }">
                    <span class="log-time">{{ row.time }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="级别" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getLogLevelType(row.level)" size="small" effect="dark">
                      {{ row.level }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="module" label="模块" width="120">
                  <template #default="{ row }">
                    <el-tag type="info" size="small">{{ row.module }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="message" label="日志内容">
                  <template #default="{ row }">
                    <span class="log-message" :class="'log-' + row.level.toLowerCase()">{{ row.message }}</span>
                  </template>
                </el-table-column>
              </el-table>
              <div class="table-footer">
                <div class="footer-info">
                  共 {{ logs.length }} 条记录
                </div>
                <el-pagination
                  v-model:current-page="logPage"
                  :page-size="10"
                  :total="100"
                  layout="prev, pager, next, jumper"
                  background
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 安全设置 -->
        <div v-show="activeTab === 'security'" class="content-section">
          <div class="section-header">
            <div class="header-info">
              <h3 class="section-title">
                <el-icon><Lock /></el-icon>
                安全设置
              </h3>
              <p class="section-desc">系统安全认证、密码策略和访问控制</p>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header">
              <div class="card-icon" style="background: linear-gradient(135deg, #7232dd, #b37feb)">
                <el-icon><Key /></el-icon>
              </div>
              <div class="card-title">
                <span>密码策略</span>
                <span class="card-subtitle">Password Policy</span>
              </div>
            </div>
            <div class="card-body">
              <el-form label-position="top" class="settings-form">
                <div class="form-grid half">
                  <el-form-item label="最小密码长度">
                    <div class="input-with-unit">
                      <el-input-number v-model="securitySettings.minPasswordLength" :min="6" :max="32" />
                      <span class="unit">字符</span>
                    </div>
                  </el-form-item>
                  <el-form-item label="密码过期天数">
                    <div class="input-with-unit">
                      <el-input-number v-model="securitySettings.passwordExpireDays" :min="0" :max="365" />
                      <span class="unit">天</span>
                    </div>
                    <div class="field-hint">0 表示不过期</div>
                  </el-form-item>
                </div>
                <div class="policy-toggles">
                  <div class="policy-item" :class="{ active: securitySettings.requireUppercase }">
                    <div class="policy-icon">
                      <el-icon><ArrowUp /></el-icon>
                    </div>
                    <div class="policy-info">
                      <div class="policy-name">大写字母</div>
                      <div class="policy-desc">密码必须包含至少一个大写字母</div>
                    </div>
                    <el-switch v-model="securitySettings.requireUppercase" />
                  </div>
                  <div class="policy-item" :class="{ active: securitySettings.requireNumber }">
                    <div class="policy-icon">
                      <el-icon><List /></el-icon>
                    </div>
                    <div class="policy-info">
                      <div class="policy-name">数字</div>
                      <div class="policy-desc">密码必须包含至少一个数字</div>
                    </div>
                    <el-switch v-model="securitySettings.requireNumber" />
                  </div>
                  <div class="policy-item" :class="{ active: securitySettings.requireSpecial }">
                    <div class="policy-icon">
                      <el-icon><Star /></el-icon>
                    </div>
                    <div class="policy-info">
                      <div class="policy-name">特殊字符</div>
                      <div class="policy-desc">密码必须包含至少一个特殊字符 (!@#$)</div>
                    </div>
                    <el-switch v-model="securitySettings.requireSpecial" />
                  </div>
                </div>
              </el-form>
              <div class="form-actions">
                <el-button type="primary" @click="saveSecuritySettings">
                  <el-icon><Check /></el-icon>
                  保存设置
                </el-button>
              </div>
            </div>
          </div>

          <div class="settings-card">
            <div class="card-header">
              <div class="card-icon" style="background: linear-gradient(135deg, #165dff, #4080ff)">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="card-title">
                <span>会话管理</span>
                <span class="card-subtitle">Session Management</span>
              </div>
            </div>
            <div class="card-body">
              <el-form label-position="top" class="settings-form">
                <div class="form-grid half">
                  <el-form-item label="会话超时时间">
                    <div class="input-with-unit">
                      <el-input-number v-model="securitySettings.sessionTimeout" :min="5" :max="1440" />
                      <span class="unit">分钟</span>
                    </div>
                  </el-form-item>
                  <el-form-item label="同一账号最多登录">
                    <div class="input-with-unit">
                      <el-input-number v-model="securitySettings.maxSessions" :min="1" :max="10" />
                      <span class="unit">个会话</span>
                    </div>
                  </el-form-item>
                </div>
                <el-form-item label="登录失败锁定">
                  <div class="lockout-toggle">
                    <el-switch v-model="securitySettings.enableLockout" />
                    <span class="toggle-hint">
                      连续登录失败达到阈值后将锁定账户
                    </span>
                  </div>
                </el-form-item>
                <el-form-item v-if="securitySettings.enableLockout" label="失败次数阈值" class="animate-in">
                  <div class="input-with-unit">
                    <el-input-number v-model="securitySettings.maxFailedAttempts" :min="3" :max="10" />
                    <span class="unit">次</span>
                  </div>
                  <div class="field-hint">锁定后需管理员手动解锁</div>
                </el-form-item>
              </el-form>
              <div class="form-actions">
                <el-button type="primary" @click="saveSecuritySettings">
                  <el-icon><Check /></el-icon>
                  保存设置
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- 添加用户对话框 -->
    <el-dialog v-model="showUserDialog" :title="isEditingUser ? '编辑用户' : '添加用户'" width="550px" :close-on-click-modal="false" class="user-dialog">
      <el-form :model="newUser" label-position="top" class="user-form">
        <div class="form-grid">
          <el-form-item label="用户名" required>
            <el-input v-model="newUser.username" placeholder="用于登录" :disabled="isEditingUser" />
          </el-form-item>
          <el-form-item label="姓名" required>
            <el-input v-model="newUser.name" placeholder="显示名称" />
          </el-form-item>
        </div>
        <el-form-item label="邮箱">
          <el-input v-model="newUser.email" placeholder="user@example.com">
            <template #prefix>
              <el-icon><Message /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="角色">
            <el-select v-model="newUser.role" style="width: 100%">
              <el-option label="管理员" value="admin">
                <div class="role-option">
                  <el-tag type="danger" size="small">管理员</el-tag>
                  <span>完全访问权限</span>
                </div>
              </el-option>
              <el-option label="运维工程师" value="operator">
                <div class="role-option">
                  <el-tag type="success" size="small">运维工程师</el-tag>
                  <span>运维操作权限</span>
                </div>
              </el-option>
              <el-option label="只读用户" value="readonly">
                <div class="role-option">
                  <el-tag type="info" size="small">只读用户</el-tag>
                  <span>仅查看权限</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item :label="isEditingUser ? '新密码（留空不修改）' : '初始密码'">
            <el-input v-model="newUser.password" type="password" placeholder="请输入密码" show-password>
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showUserDialog = false">取消</el-button>
        <el-button type="primary" @click="addUser">
          <el-icon><Check /></el-icon>
          {{ isEditingUser ? '保存修改' : '确认添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting, Check, Plus, Edit, Delete, Download, Refresh, Search,
  InfoFilled, Picture, Upload, OfficeBuilding, Message, Monitor,
  DataLine, Link, Connection, Histogram, Warning, User, Lock, Key,
  Bell, Postcard, Clock, Timer, List, Star, ArrowUp, TrendCharts, CircleCheck
} from '@element-plus/icons-vue'

// 状态
const activeTab = ref('basic')
const showUserDialog = ref(false)
const isEditingUser = ref(false)
const logPage = ref(1)
const testing = ref(false)
const uptime = ref('15 天 8 小时')
const hasLogo = ref(false)

// 导航项
const navItems = [
  { key: 'basic', title: '基本信息', desc: '系统信息和全局配置', icon: 'InfoFilled', gradient: 'linear-gradient(135deg, #409eff, #53a8ff)' },
  { key: 'monitoring', title: '监控配置', desc: '数据源和存储策略', icon: 'DataLine', gradient: 'linear-gradient(135deg, #67c23a, #85ce61)' },
  { key: 'alerts', title: '告警配置', desc: '告警规则和通知渠道', icon: 'Warning', gradient: 'linear-gradient(135deg, #e6a23c, #ebb562)' },
  { key: 'users', title: '用户管理', desc: '用户和权限管理', icon: 'User', gradient: 'linear-gradient(135deg, #f56c6c, #ff7875)' },
  { key: 'logs', title: '系统日志', desc: '日志查看和导出', icon: 'Postcard', gradient: 'linear-gradient(135deg, #909399, #b1b3b8)' },
  { key: 'security', title: '安全设置', desc: '密码和会话策略', icon: 'Lock', gradient: 'linear-gradient(135deg, #7232dd, #b37feb)' }
]

// 数据源类型
const sourceTypes = [
  { label: 'Prometheus', value: 'prometheus', icon: 'DataLine', desc: '时序监控' },
  { label: 'Zabbix', value: 'zabbix', icon: 'Monitor', desc: '企业监控' },
  { label: 'TDengine', value: 'tdengine', icon: 'Histogram', desc: '时序数据库' },
  { label: 'InfluxDB', value: 'influxdb', icon: 'Connection', desc: 'Influx 时序' }
]

// 存储规则
const storageRules = reactive([
  { period: '1分钟', name: '高精度数据', desc: '保留详细的原始采样数据', enabled: true, usage: 67 },
  { period: '1小时', name: '高分辨率', desc: '保留5分钟聚合数据', enabled: true, usage: 45 },
  { period: '1天', name: '中分辨率', desc: '保留1小时聚合数据', enabled: true, usage: 28 },
  { period: '1年', name: '低分辨率', desc: '保留1天汇总数据', enabled: true, usage: 12 }
])

// 告警级别
const alertLevels = [
  { value: 'critical', label: '严重', desc: '系统不可用，需要立即处理', color: '#f53f3f', icon: 'CircleCloseFilled' },
  { value: 'warning', label: '警告', desc: '性能下降或即将故障', color: '#ff7d00', icon: 'WarningFilled' },
  { value: 'info', label: '信息', desc: '一般性通知或提示', color: '#165dff', icon: 'InfoFilled' }
]

// 通知渠道
const notificationChannels = reactive([
  { id: 'email', name: '邮件通知', desc: '发送邮件到管理员邮箱', icon: 'Message', color: '#409eff', enabled: true },
  { id: 'webhook', name: 'Webhook', desc: '推送到指定 HTTP 接口', icon: 'Link', color: '#67c23a', enabled: false },
  { id: 'feishu', name: '飞书', desc: '发送到飞书群组', icon: 'ChatLineSquare', color: '#07c160', enabled: false },
  { id: 'sms', name: '短信', desc: '发送短信到手机', icon: 'Phone', color: '#ff9800', enabled: false }
])

// 基本设置
const basicSettings = reactive({
  systemName: 'IT运维平台',
  description: '企业级智能运维管理系统，为内网环境提供全方位的监控、告警和运维支持',
  email: 'admin@example.com',
  timezone: 'Asia/Shanghai'
})

// 监控设置
const monitoringSettings = reactive({
  sourceType: 'prometheus',
  sourceUrl: 'http://localhost:9090',
  apiKey: '',
  interval: 30,
  retentionDays: 30
})

// 告警设置
const alertSettings = reactive({
  levels: ['critical', 'warning', 'info'],
  channels: ['email'],
  cpuThreshold: 90,
  memThreshold: 85,
  diskThreshold: 80
})

// 安全设置
const securitySettings = reactive({
  minPasswordLength: 8,
  passwordExpireDays: 90,
  requireUppercase: true,
  requireNumber: true,
  requireSpecial: true,
  sessionTimeout: 30,
  maxSessions: 3,
  enableLockout: true,
  maxFailedAttempts: 5
})

// 日志设置
const logSettings = reactive({
  level: '',
  dateRange: []
})

// 新用户
const newUser = reactive({
  username: '',
  name: '',
  email: '',
  role: 'operator',
  password: ''
})

// 用户列表
const users = ref([
  { username: 'admin', name: '管理员', email: 'admin@example.com', role: 'admin', roleText: '管理员', status: 'active', statusText: '活跃', lastLogin: '2026-05-04 23:55', avatarColor: '#409eff' },
  { username: 'zhangsan', name: '张三', email: 'zhangsan@example.com', role: 'operator', roleText: '运维工程师', status: 'active', statusText: '活跃', lastLogin: '2026-05-04 18:30', avatarColor: '#67c23a' },
  { username: 'lisi', name: '李四', email: 'lisi@example.com', role: 'operator', roleText: '运维工程师', status: 'active', statusText: '活跃', lastLogin: '2026-05-03 09:15', avatarColor: '#e6a23c' },
  { username: 'wangwu', name: '王五', email: 'wangwu@example.com', role: 'readonly', roleText: '只读用户', status: 'inactive', statusText: '停用', lastLogin: '2026-04-28 14:20', avatarColor: '#909399' }
])

// 日志列表
const logs = ref([
  { time: '2026-05-05 12:00:00', level: 'INFO', module: 'Monitor', message: '数据采集任务执行成功，共采集 128 个指标' },
  { time: '2026-05-05 11:55:00', level: 'WARNING', module: 'Alert', message: '触发告警规则: CPU 使用率 > 90%，服务器 192.168.1.101' },
  { time: '2026-05-05 11:50:00', level: 'ERROR', module: 'API', message: 'API 请求超时: /api/metrics，耗时 30.2s' },
  { time: '2026-05-05 11:45:00', level: 'INFO', module: 'WorkOrder', message: '工单 WO2026050001 已创建，等待处理' },
  { time: '2026-05-05 11:40:00', level: 'INFO', module: 'System', message: '系统健康检查通过，所有服务运行正常' }
])

// 辅助函数
const switchTab = (key) => {
  activeTab.value = key
}

const getRoleTagType = (role) => {
  const types = { admin: 'danger', operator: 'success', readonly: 'info' }
  return types[role] || 'info'
}

const getLogLevelType = (level) => {
  const types = { ERROR: 'danger', WARNING: 'warning', INFO: 'info' }
  return types[level] || 'info'
}

const toggleLevel = (level) => {
  const idx = alertSettings.levels.indexOf(level)
  if (idx > -1) {
    alertSettings.levels.splice(idx, 1)
  } else {
    alertSettings.levels.push(level)
  }
}

const toggleChannel = (channelId) => {
  const idx = alertSettings.channels.indexOf(channelId)
  if (idx > -1) {
    alertSettings.channels.splice(idx, 1)
  } else {
    alertSettings.channels.push(channelId)
  }
}

// 保存操作
const saveBasicSettings = () => {
  ElMessage.success({ message: '基本信息已保存', grouping: true })
}

const saveMonitoringSettings = async () => {
  ElMessage.success({ message: '监控配置已保存', grouping: true })
}

const saveAlertSettings = () => {
  ElMessage.success({ message: '告警配置已保存', grouping: true })
}

const saveSecuritySettings = () => {
  ElMessage.success({ message: '安全设置已保存', grouping: true })
}

const testConnection = async () => {
  testing.value = true
  await new Promise(resolve => setTimeout(resolve, 1500))
  testing.value = false
  ElMessage.success('连接测试成功！数据源可正常访问。')
}

const refreshLogs = () => {
  ElMessage.info('日志已刷新')
}

const exportLogs = () => {
  ElMessage.info('日志导出中，请稍候...')
}

const clearOldLogs = async () => {
  try {
    await ElMessageBox.confirm('确定要清理30天前的日志吗？', '提示', { type: 'warning' })
    ElMessage.success('旧日志已清理')
  } catch (e) {}
}

const exportUsers = () => {
  ElMessage.info('用户数据导出中...')
}

const editUser = (row) => {
  isEditingUser.value = true
  Object.assign(newUser, {
    username: row.username,
    name: row.name,
    email: row.email,
    role: row.role,
    password: ''
  })
  showUserDialog.value = true
}

const resetPassword = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要重置用户「${row.name}」的密码吗？`, '提示', { type: 'warning' })
    ElMessage.success('密码已重置为默认值')
  } catch (e) {}
}

const deleteUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除用户「${row.name}」吗？此操作不可恢复。`, '危险操作', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'error'
    })
    users.value = users.value.filter(u => u.username !== row.username)
    ElMessage.success('用户已删除')
  } catch (e) {}
}

const addUser = () => {
  if (!newUser.username || !newUser.name) {
    ElMessage.warning('请填写用户名和姓名')
    return
  }
  if (!isEditingUser.value && !newUser.password) {
    ElMessage.warning('请输入初始密码')
    return
  }

  if (isEditingUser.value) {
    const idx = users.value.findIndex(u => u.username === newUser.username)
    if (idx !== -1) {
      users.value[idx] = {
        ...users.value[idx],
        name: newUser.name,
        email: newUser.email,
        role: newUser.role
      }
    }
    ElMessage.success('用户信息已更新')
  } else {
    const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#165dff', '#722ed1']
    users.value.push({
      ...newUser,
      roleText: newUser.role === 'admin' ? '管理员' : newUser.role === 'operator' ? '运维工程师' : '只读用户',
      status: 'active',
      statusText: '活跃',
      lastLogin: '-',
      avatarColor: colors[Math.floor(Math.random() * colors.length)]
    })
    ElMessage.success('用户添加成功')
  }

  showUserDialog.value = false
  isEditingUser.value = false
  Object.assign(newUser, { username: '', name: '', email: '', role: 'operator', password: '' })
}

// 定时更新运行时长
let uptimeTimer = null
onMounted(() => {
  uptimeTimer = setInterval(() => {
    // 实际项目中会实时计算
  }, 60000)
})

onUnmounted(() => {
  if (uptimeTimer) clearInterval(uptimeTimer)
})
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.settings-page {
  height: calc(100vh - 140px);
  animation: fadeIn 0.3s ease;
}

.settings-container {
  display: flex;
  gap: $spacing-xl;
  height: 100%;
}

// ========== 左侧导航 ==========
.settings-nav {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: $bg-container;
  border-radius: $border-radius-lg;
  overflow: hidden;
  box-shadow: $shadow-sm;
}

.nav-header {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-xl;
  background: linear-gradient(135deg, rgba($primary, 0.08), rgba($primary, 0.02));
  border-bottom: 1px solid $border-light;

  .header-icon {
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, $primary, #4080ff);
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 20px;
  }

  .header-text {
    display: flex;
    flex-direction: column;

    .header-title {
      font-size: $font-size-lg;
      font-weight: $font-weight-semibold;
      color: $text-primary;
    }

    .header-subtitle {
      font-size: $font-size-xs;
      color: $text-secondary;
      font-family: 'Monaco', monospace;
    }
  }
}

.nav-list {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-md;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: $spacing-xs;
  position: relative;

  &:hover {
    background: $bg-page;

    .nav-icon {
      transform: scale(1.05);
    }
  }

  &.active {
    background: rgba($primary, 0.08);

    .nav-icon {
      transform: scale(1.1);
      box-shadow: 0 4px 12px rgba($primary, 0.3);
    }

    .nav-title {
      color: $primary;
    }
  }

  .nav-icon {
    width: 42px;
    height: 42px;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 18px;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .nav-text {
    flex: 1;

    .nav-title {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
      transition: color 0.2s;
    }

    .nav-desc {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }

  .nav-indicator {
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);

    .indicator-bar {
      width: 4px;
      height: 24px;
      background: $primary;
      border-radius: 2px 0 0 2px;
    }
  }
}

// 系统状态卡片
.system-status-card {
  padding: $spacing-lg;
  border-top: 1px solid $border-light;
  background: $bg-page;

  .status-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $spacing-md;

    span {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: $spacing-xs;
      font-size: $font-size-xs;
      color: $success;

      .status-dot {
        width: 6px;
        height: 6px;
        background: $success;
        border-radius: 50%;
        animation: pulse 2s infinite;
      }
    }
  }

  .status-body {
    .status-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: $spacing-xs 0;

      .status-label {
        display: flex;
        align-items: center;
        gap: $spacing-xs;
        font-size: $font-size-sm;
        color: $text-secondary;

        .el-icon {
          font-size: 14px;
        }
      }

      .status-value {
        font-size: $font-size-sm;
        color: $text-primary;
        font-weight: $font-weight-medium;
        font-family: 'Monaco', monospace;
      }
    }
  }
}

// ========== 右侧内容 ==========
.settings-content {
  flex: 1;
  overflow-y: auto;
  padding-right: $spacing-sm;
}

.content-section {
  animation: slideIn 0.3s ease;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-xl;

  .header-info {
    .section-title {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      margin: 0 0 $spacing-xs 0;
      font-size: $font-size-xl;
      font-weight: $font-weight-semibold;
      color: $text-primary;

      .el-icon {
        color: $primary;
      }
    }

    .section-desc {
      margin: 0;
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }

  .header-actions {
    display: flex;
    gap: $spacing-sm;
  }
}

// 设置卡片
.settings-card {
  background: $bg-container;
  border-radius: $border-radius-lg;
  margin-bottom: $spacing-lg;
  overflow: hidden;
  box-shadow: $shadow-sm;
  border: 1px solid $border-light;

  .card-header {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    padding: $spacing-lg;
    background: $bg-page;
    border-bottom: 1px solid $border-light;

    &.with-actions {
      justify-content: space-between;
    }

    .card-icon {
      width: 40px;
      height: 40px;
      border-radius: $border-radius-md;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 18px;
      flex-shrink: 0;
    }

    .card-title {
      display: flex;
      flex-direction: column;

      span:first-child {
        font-size: $font-size-md;
        font-weight: $font-weight-medium;
        color: $text-primary;
      }

      .card-subtitle {
        font-size: $font-size-xs;
        color: $text-secondary;
        font-family: 'Monaco', monospace;
      }
    }

    .card-actions {
      margin-left: auto;
    }
  }

  .card-body {
    padding: $spacing-xl;

    &.no-padding {
      padding: 0;
    }
  }
}

// 表单
.settings-form {
  max-width: 600px;

  :deep(.el-form-item) {
    margin-bottom: $spacing-lg;
  }

  :deep(.el-form-item__label) {
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: $spacing-sm;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-lg;

  &.half {
    max-width: 400px;
  }
}

.form-actions {
  display: flex;
  gap: $spacing-md;
  margin-top: $spacing-xl;
  padding-top: $spacing-lg;
  border-top: 1px solid $border-light;
}

.input-with-unit {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .unit {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.field-hint {
  margin-top: $spacing-xs;
  font-size: $font-size-xs;
  color: $text-secondary;
}

// 时区选项
.timezone-option {
  display: flex;
  justify-content: space-between;

  .tz-offset {
    color: $text-secondary;
    font-size: $font-size-xs;
  }
}

.input-hint {
  color: $text-placeholder;
  font-size: $font-size-xs;
}

// Logo 上传
.logo-upload-section {
  display: flex;
  align-items: center;
  gap: $spacing-xl;
}

.logo-preview-area {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
}

.logo-preview {
  width: 80px;
  height: 80px;
  background: $bg-page;
  border: 2px dashed $border;
  border-radius: $border-radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-placeholder;
  transition: all 0.2s ease;

  &.has-logo {
    border-style: solid;
    border-color: $primary;
  }
}

.logo-info {
  .logo-name {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin-bottom: $spacing-xs;
  }

  .logo-tagline {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.upload-actions {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;

  .upload-hint {
    margin: 0;
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

// 数据源类型网格
.source-type-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-md;
}

.source-type-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-lg;
  background: $bg-page;
  border: 2px solid $border-light;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: $primary;
    transform: translateY(-2px);
  }

  &.active {
    border-color: $primary;
    background: rgba($primary, 0.05);
    box-shadow: 0 4px 12px rgba($primary, 0.15);
  }

  .type-icon-wrapper {
    position: relative;

    .type-icon {
      width: 48px;
      height: 48px;
      background: linear-gradient(135deg, $primary, #4080ff);
      border-radius: $border-radius-md;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 24px;
    }

    .type-check {
      position: absolute;
      right: -8px;
      top: -8px;
      width: 20px;
      height: 20px;
      background: $primary;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 12px;
    }
  }

  .type-name {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-primary;
  }

  .type-desc {
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

// 存储规则
.storage-rules {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  padding: $spacing-lg;
  background: $bg-page;
  border-radius: $border-radius-md;
  transition: all 0.2s ease;

  &:hover {
    background: rgba($primary, 0.03);
  }

  .rule-header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    min-width: 120px;

    .rule-name {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }
  }

  .rule-info {
    flex: 1;

    .rule-desc {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-bottom: $spacing-xs;
    }

    .rule-progress {
      display: flex;
      align-items: center;
      gap: $spacing-sm;

      .progress-bar {
        flex: 1;
        height: 4px;
        background: $border-light;
        border-radius: 2px;
        overflow: hidden;

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, $success, #85ce61);
          border-radius: 2px;
          transition: width 0.3s ease;
        }
      }

      .progress-text {
        font-size: $font-size-xs;
        color: $text-secondary;
        min-width: 50px;
      }
    }
  }
}

// 告警级别卡片
.level-cards {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.level-card {
  padding: $spacing-md;
  background: $bg-page;
  border: 2px solid $border-light;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: $primary;
  }

  &.active {
    border-color: $primary;
    background: rgba($primary, 0.03);
  }

  .level-indicator {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    border-radius: 2px 0 0 2px;
  }

  .level-content {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    position: relative;
  }

  .level-icon {
    width: 40px;
    height: 40px;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 18px;
    flex-shrink: 0;
  }

  .level-info {
    flex: 1;

    .level-name {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .level-desc {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }

  .level-check {
    width: 24px;
    height: 24px;
    background: $primary;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 14px;
  }
}

// 阈值配置
.threshold-section {
  margin-top: $spacing-xl;
  padding: $spacing-lg;
  background: $bg-page;
  border-radius: $border-radius-md;

  .threshold-title {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: $text-primary;
    margin-bottom: $spacing-lg;

    .el-icon {
      color: $primary;
    }
  }
}

.threshold-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-xl;
}

.threshold-item {
  .threshold-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $spacing-sm;

    .threshold-label {
      font-size: $font-size-sm;
      color: $text-secondary;
    }

    .threshold-value {
      font-size: $font-size-md;
      font-weight: $font-weight-bold;
      color: $text-primary;
      font-family: 'Monaco', monospace;
    }
  }

  .threshold-range {
    display: flex;
    justify-content: space-between;
    font-size: $font-size-xs;
    color: $text-placeholder;
    margin-top: $spacing-xs;
  }
}

// 通知渠道列表
.channel-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.channel-item {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  padding: $spacing-lg;
  background: $bg-page;
  border: 2px solid $border-light;
  border-radius: $border-radius-md;
  transition: all 0.2s ease;

  &:hover {
    border-color: $primary;
  }

  &.active {
    border-color: $primary;
    background: rgba($primary, 0.03);
  }

  .channel-icon {
    width: 44px;
    height: 44px;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 20px;
    flex-shrink: 0;
  }

  .channel-info {
    flex: 1;

    .channel-name {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
      margin-bottom: 2px;
    }

    .channel-desc {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }

  .channel-status {
    .el-tag {
      font-size: $font-size-xs;
    }
  }
}

// 用户相关
.user-cell {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  .user-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-weight: $font-weight-bold;
    font-size: $font-size-sm;
    flex-shrink: 0;
  }

  .user-info {
    .user-name {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .user-email {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }
}

.mono-text {
  font-family: 'Monaco', monospace;
  font-size: $font-size-sm;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  font-size: $font-size-sm;
  color: $text-primary;

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.active { background: $success; }
    &.inactive { background: $text-placeholder; }
  }
}

.last-login-cell {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  font-size: $font-size-sm;
  color: $text-secondary;

  .el-icon {
    font-size: 14px;
  }
}

.action-buttons {
  display: flex;
  gap: $spacing-xs;
}

// 日志相关
.log-filters {
  :deep(.el-form-item) {
    margin-bottom: 0;
  }
}

.log-time {
  font-size: $font-size-sm;
  color: $text-secondary;
  font-family: 'Monaco', monospace;
}

.log-message {
  font-size: $font-size-sm;
  color: $text-primary;

  &.log-error {
    color: $danger;
  }

  &.log-warning {
    color: $warning;
  }
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-lg;
  border-top: 1px solid $border-light;

  .footer-info {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

// 安全设置
.policy-toggles {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  margin-top: $spacing-lg;
}

.policy-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md $spacing-lg;
  background: $bg-page;
  border: 2px solid $border-light;
  border-radius: $border-radius-md;
  transition: all 0.2s ease;

  &.active {
    border-color: $primary;
    background: rgba($primary, 0.03);

    .policy-icon {
      background: $primary;
      color: #fff;
    }
  }

  .policy-icon {
    width: 36px;
    height: 36px;
    background: $bg-container;
    border-radius: $border-radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $text-secondary;
    font-size: 16px;
    transition: all 0.2s ease;
  }

  .policy-info {
    flex: 1;

    .policy-name {
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }

    .policy-desc {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }
}

.lockout-toggle {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  .toggle-hint {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.animate-in {
  animation: slideDown 0.3s ease;
}

// 用户对话框
.user-dialog {
  :deep(.el-dialog__header) {
    padding: $spacing-lg;
    border-bottom: 1px solid $border-light;
  }

  :deep(.el-dialog__body) {
    padding: $spacing-xl;
  }
}

.user-form {
  :deep(.el-form-item) {
    margin-bottom: $spacing-lg;
  }
}

.role-option {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  width: 100%;
  justify-content: space-between;
}

// ========== 动画 ==========
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { 
    opacity: 0;
    transform: translateX(20px);
  }
  to { 
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideDown {
  from { 
    opacity: 0;
    transform: translateY(-10px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

// ========== 响应式 ==========
@include respond-to('xl') {
  .source-type-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .threshold-grid {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}

@include respond-to('lg') {
  .settings-container {
    flex-direction: column;
  }

  .settings-nav {
    width: 100%;
    max-height: 250px;
  }

  .nav-list {
    display: flex;
    overflow-x: auto;
    gap: $spacing-xs;
    padding: $spacing-sm;

    .nav-item {
      flex-shrink: 0;
      margin-bottom: 0;

      .nav-text {
        display: none;
      }
    }
  }

  .system-status-card {
    display: none;
  }
}
</style>