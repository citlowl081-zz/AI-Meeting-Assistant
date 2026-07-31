<template>
  <AppLayout>
    <div class="page-container">
      <h2 style="margin-bottom: 20px;">仪表盘</h2>

      <!-- 统计卡片区 - 第一行: 核心数据 -->
      <el-row :gutter="16" style="margin-bottom: 16px;">
        <el-col :xs="12" :sm="6" v-for="card in topCards" :key="card.label">
          <el-card shadow="hover" class="stat-card" :style="{ borderTop: `3px solid ${card.color}` }">
            <div class="stat-content">
              <div class="stat-icon" :style="{ background: card.color }">
                <el-icon :size="24" color="#fff"><component :is="card.icon" /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-number" :style="{ color: card.color }">{{ card.value }}</div>
                <div class="stat-label">{{ card.label }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 统计卡片区 - 第二行: 状态明细 -->
      <el-row :gutter="16" style="margin-bottom: 24px;">
        <el-col :xs="12" :sm="4" v-for="card in statusCards" :key="card.label">
          <el-card shadow="hover" class="stat-card-sm" :style="{ borderLeft: `3px solid ${card.color}` }">
            <div class="stat-sm-content">
              <div class="stat-sm-number" :style="{ color: card.color }">{{ card.value }}</div>
              <div class="stat-sm-label">{{ card.label }}</div>
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
          <el-table-column prop="title" label="会议标题" min-width="220">
            <template #default="{ row }">
              <el-link type="primary" @click="$router.push(`/meetings/${row.id}`)">
                {{ row.title }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column label="文件大小" width="120">
            <template #default="{ row }">
              {{ formatFileSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120">
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
 * 第一行: 核心统计 - 会议总数、已完成、失败、处理中
 * 第二行: 状态明细 - 已上传、转写中、已转写、摘要生成中、已完成、失败
 */
import { ref, onMounted, computed } from 'vue'
import {
  VideoCamera, CircleCheck, CircleClose, Clock,
  Upload, UploadFilled, Microphone, Document, Loading, CircleCheckFilled
} from '@element-plus/icons-vue'
import AppLayout from '../components/AppLayout.vue'
import { getMeetingList, getDashboardStats } from '../api/meeting'

const loading = ref(false)
const meetings = ref([])
const stats = ref({
  total_meetings: 0,
  uploaded_count: 0,
  transcribing_count: 0,
  transcribed_count: 0,
  summarizing_count: 0,
  completed_count: 0,
  failed_count: 0,
})

// 第一行核心卡片
const topCards = computed(() => [
  { label: '会议总数', value: stats.value.total_meetings, icon: VideoCamera, color: '#409EFF' },
  { label: '已完成', value: stats.value.completed_count, icon: CircleCheckFilled, color: '#67C23A' },
  { label: '失败', value: stats.value.failed_count, icon: CircleClose, color: '#F56C6C' },
  { label: '处理中', value: stats.value.transcribing_count + stats.value.summarizing_count, icon: Loading, color: '#E6A23C' },
])

// 第二行状态明细
const statusCards = computed(() => [
  { label: '已上传', value: stats.value.uploaded_count, color: '#909399' },
  { label: '转写中', value: stats.value.transcribing_count, color: '#E6A23C' },
  { label: '已转写', value: stats.value.transcribed_count, color: '#17B3A3' },
  { label: '摘要生成中', value: stats.value.summarizing_count, color: '#9B59B6' },
  { label: '已完成', value: stats.value.completed_count, color: '#67C23A' },
  { label: '失败', value: stats.value.failed_count, color: '#F56C6C' },
])

const recentMeetings = computed(() => meetings.value.slice(0, 5))

const formatDate = (d) => (d ? new Date(d).toLocaleString('zh-CN') : '-')

const formatFileSize = (b) => {
  if (!b) return '-'
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1024 * 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(1)} MB`
  return `${(b / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

const getStatusType = (s) => {
  const m = { uploaded: 'info', transcribing: 'warning', transcribed: '', summarizing: 'warning', completed: 'success', failed: 'danger' }
  return m[s] || 'info'
}
const getStatusText = (s) => {
  const m = { uploaded: '已上传', transcribing: '转写中', transcribed: '已转写', summarizing: '生成中', completed: '已完成', failed: '失败' }
  return m[s] || s
}

const loadData = async () => {
  loading.value = true
  try {
    const [listResult, statsResult] = await Promise.all([
      getMeetingList({ page: 1, page_size: 100 }),
      getDashboardStats(),
    ])
    meetings.value = listResult.items || []
    stats.value = statsResult
  } catch {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.stat-card {
  margin-bottom: 16px;
}
.stat-card-sm {
  margin-bottom: 16px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
}

.stat-number {
  font-size: 26px;
  font-weight: 700;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

.stat-sm-content {
  text-align: center;
  padding: 4px 0;
}

.stat-sm-number {
  font-size: 24px;
  font-weight: 700;
}

.stat-sm-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
