<template>
  <AppLayout>
    <div class="page-container">
      <h2 style="margin-bottom: 20px;">仪表盘</h2>

      <!-- 统计卡片区 -->
      <el-row :gutter="16" style="margin-bottom: 24px;">
        <el-col :xs="24" :sm="8" v-for="card in statCards" :key="card.label">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" :style="{ background: card.color }">
                <el-icon :size="28" color="#fff"><component :is="card.icon" /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-number">{{ card.value }}</div>
                <div class="stat-label">{{ card.label }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 最近会议列表 -->
      <el-card shadow="hover">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600;">最近会议</span>
            <el-button type="primary" size="small" @click="$router.push('/upload')">
              <el-icon><Upload /></el-icon> 上传新会议
            </el-button>
          </div>
        </template>

        <el-table
          :data="recentMeetings"
          v-loading="loading"
          empty-text="暂无会议记录，点击上方按钮上传第一个会议"
        >
          <el-table-column prop="title" label="会议标题" min-width="200">
            <template #default="{ row }">
              <el-link type="primary" @click="$router.push(`/meetings/${row.id}`)">
                {{ row.title }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="file_type" label="文件类型" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.file_type?.toUpperCase() || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="140">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="$router.push(`/meetings/${row.id}`)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup>
/**
 * 仪表盘页面
 * 展示统计数据（总数/本月/处理中）和最近会议列表
 */
import { ref, onMounted, computed } from 'vue'
import { VideoCamera, DataAnalysis, Clock } from '@element-plus/icons-vue'
import AppLayout from '../components/AppLayout.vue'
import { getMeetingList } from '../api/meeting'

const loading = ref(false)
const meetings = ref([])

// 统计卡片数据
const statCards = computed(() => {
  const total = meetings.value.length
  // 计算本月新增会议数
  const now = new Date()
  const thisMonth = meetings.value.filter((m) => {
    if (!m.created_at) return false
    const d = new Date(m.created_at)
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
  }).length
  // 计算处理中的会议数
  const processing = meetings.value.filter(
    (m) => m.status === 'transcribing' || m.status === 'summarizing'
  ).length

  return [
    { label: '会议总数', value: total, icon: VideoCamera, color: '#409EFF' },
    { label: '本月新增', value: thisMonth, icon: DataAnalysis, color: '#67C23A' },
    { label: '处理中', value: processing, icon: Clock, color: '#E6A23C' },
  ]
})

// 最近5条会议记录
const recentMeetings = computed(() => meetings.value.slice(0, 5))

/**
 * 格式化日期
 */
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

/**
 * 会议状态 → Element Plus Tag 颜色映射
 */
const getStatusType = (status) => {
  const map = {
    uploaded: 'info',
    transcribing: 'warning',
    transcribed: '',
    summarizing: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

/**
 * 会议状态 → 中文显示
 */
const getStatusText = (status) => {
  const map = {
    uploaded: '已上传',
    transcribing: '转写中',
    transcribed: '已转写',
    summarizing: '生成中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

/**
 * 加载会议列表数据
 */
const loadMeetings = async () => {
  loading.value = true
  try {
    const result = await getMeetingList({ page: 1, page_size: 100 })
    meetings.value = result.items || []
  } catch {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadMeetings()
})
</script>

<style scoped>
.stat-card {
  margin-bottom: 16px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 2px;
}
</style>
