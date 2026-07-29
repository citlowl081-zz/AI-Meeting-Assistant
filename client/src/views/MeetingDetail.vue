<template>
  <AppLayout>
    <div class="page-container">
      <!-- 会议标题栏 + 操作按钮 -->
      <div class="detail-header">
        <div>
          <el-button text @click="$router.back()">
            <el-icon><ArrowLeft /></el-icon> 返回
          </el-button>
          <h2 style="display: inline; margin-left: 8px;">{{ meeting?.title || '会议详情' }}</h2>
        </div>
        <div class="header-actions">
          <el-dropdown @command="handleExport">
            <el-button type="primary" :disabled="meeting?.status !== 'completed'">
              导出纪要 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="md">
                  <el-icon><Document /></el-icon> 导出 Markdown
                </el-dropdown-item>
                <el-dropdown-item command="pdf">
                  <el-icon><Printer /></el-icon> 导出 PDF
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-dropdown @command="handleAction">
            <el-button type="success" v-if="meeting?.status === 'uploaded' || meeting?.status === 'failed'">
              处理 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  command="transcribe"
                  :disabled="!['uploaded', 'transcribed', 'completed', 'failed'].includes(meeting?.status)"
                >
                  语音转写
                </el-dropdown-item>
                <el-dropdown-item
                  command="summarize"
                  :disabled="!['transcribed', 'completed'].includes(meeting?.status)"
                >
                  生成AI纪要
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- 会议基本信息 -->
      <el-card shadow="hover" style="margin-bottom: 16px;">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(meeting?.status)" size="small">
              {{ statusText(meeting?.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="文件类型">
            {{ meeting?.file_type?.toUpperCase() || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="文件大小">
            {{ formatFileSize(meeting?.file_size) }}
          </el-descriptions-item>
          <el-descriptions-item label="原始文件名" :span="2">
            {{ meeting?.original_filename || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(meeting?.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
        <!-- 错误信息 -->
        <el-alert
          v-if="meeting?.status === 'failed' && meeting?.error_message"
          :title="`错误: ${meeting.error_message}`"
          type="error"
          show-icon
          :closable="false"
          style="margin-top: 12px;"
        />
      </el-card>

      <!-- 加载中 -->
      <div v-if="loading" style="text-align: center; padding: 60px;">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
        <p style="margin-top: 12px; color: #909399;">正在处理中，请稍候...</p>
      </div>

      <!-- Tab 切换：转写/摘要/要点/发言人总结 -->
      <el-card v-if="!loading" shadow="hover">
        <el-tabs v-model="activeTab" type="border-card">
          <!-- Tab 1: 语音转写 -->
          <el-tab-pane label="语音转写" name="transcript">
            <div v-if="transcript?.segments?.length">
              <div
                v-for="seg in transcript.segments"
                :key="seg.sequence || seg.id"
                class="transcript-segment"
              >
                <div class="segment-header">
                  <el-tag type="primary" size="small" effect="dark">{{ seg.speaker }}</el-tag>
                  <span class="segment-time">
                    {{ formatTime(seg.start_time) }} - {{ formatTime(seg.end_time) }}
                  </span>
                </div>
                <p class="segment-content">{{ seg.content }}</p>
              </div>
            </div>
            <el-empty v-else description="暂无转写结果，请先进行语音转写" />
          </el-tab-pane>

          <!-- Tab 2: 会议摘要 -->
          <el-tab-pane label="会议摘要" name="summary">
            <div v-if="minutesData?.summary?.full_summary" class="summary-content">
              <p>{{ minutesData.summary.full_summary }}</p>
              <div v-if="minutesData.summary.keywords" class="keywords-section">
                <el-tag
                  v-for="kw in keywordList"
                  :key="kw"
                  size="small"
                  type="success"
                  effect="plain"
                  style="margin-right: 8px; margin-top: 8px;"
                >
                  {{ kw }}
                </el-tag>
              </div>
            </div>
            <el-empty v-else description="暂无摘要，请先生成AI纪要" />
          </el-tab-pane>

          <!-- Tab 3: 待办事项 -->
          <el-tab-pane label="待办事项" name="actions">
            <el-table
              v-if="minutesData?.action_items?.length"
              :data="minutesData.action_items"
              empty-text="无待办事项"
            >
              <el-table-column type="index" label="序号" width="60" />
              <el-table-column prop="content" label="任务内容" min-width="260" />
              <el-table-column prop="responsible_person" label="负责人" width="140">
                <template #default="{ row }">
                  {{ row.responsible_person || '未指定' }}
                </template>
              </el-table-column>
              <el-table-column prop="deadline" label="截止时间" width="140">
                <template #default="{ row }">
                  {{ row.deadline || '未指定' }}
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
                    {{ row.status === 'completed' ? '已完成' : '进行中' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="暂无待办事项" />
          </el-tab-pane>

          <!-- Tab 4: 发言人总结 -->
          <el-tab-pane label="发言人总结" name="speakers">
            <div v-if="minutesData?.speaker_summaries?.length">
              <el-row :gutter="16">
                <el-col
                  v-for="sp in minutesData.speaker_summaries"
                  :key="sp.id || sp.speaker"
                  :xs="24" :sm="12"
                  style="margin-bottom: 16px;"
                >
                  <el-card shadow="hover">
                    <template #header>
                      <el-tag type="primary" effect="dark">{{ sp.speaker }}</el-tag>
                    </template>
                    <p>{{ sp.summary || '暂无总结' }}</p>
                  </el-card>
                </el-col>
              </el-row>
            </div>
            <el-empty v-else description="暂无发言人总结" />
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup>
/**
 * 会议详情/纪要展示页面
 * 核心页面，展示 Tab 切换的完整会议纪要内容
 * 支持触发转写、生成纪要、导出等操作
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import AppLayout from '../components/AppLayout.vue'
import {
  getMeetingDetail,
  getTranscript,
  transcribeMeeting,
  summarizeMeeting,
  getMeetingSummary,
  exportMinutes,
} from '../api/meeting'

const route = useRoute()
const router = useRouter()
const meetingId = computed(() => Number(route.params.id))

const loading = ref(false)
const meeting = ref(null)
const activeTab = ref('transcript')

// 转写数据
const transcript = ref(null)
// 完整纪要数据（摘要 + 待办 + 发言人总结）
const minutesData = ref(null)

// 关键词拆分为数组
const keywordList = computed(() => {
  const kws = minutesData.value?.summary?.keywords
  if (!kws) return []
  return kws.split(/[,，]/).map((k) => k.trim()).filter(Boolean)
})

/**
 * 加载会议基本信息
 */
const loadMeeting = async () => {
  try {
    meeting.value = await getMeetingDetail(meetingId.value)
  } catch {
    router.push('/meetings')
  }
}

/**
 * 加载转写结果
 */
const loadTranscript = async () => {
  try {
    transcript.value = await getTranscript(meetingId.value)
  } catch {
    // 可能还没有转写数据
  }
}

/**
 * 加载完整纪要
 */
const loadSummary = async () => {
  try {
    minutesData.value = await getMeetingSummary(meetingId.value)
    // 同时更新转写数据（纪要接口也返回转写）
    if (minutesData.value.transcript) {
      transcript.value = minutesData.value.transcript
    }
  } catch {
    // 可能还没有纪要数据
  }
}

/**
 * 处理操作（转写/生成摘要）
 */
const handleAction = async (command) => {
  if (command === 'transcribe') {
    await doTranscribe()
  } else if (command === 'summarize') {
    await doSummarize()
  }
}

/**
 * 触发语音转写
 */
const doTranscribe = async () => {
  loading.value = true
  ElMessage.info('正在提交语音转写任务，请稍候...')
  try {
    await transcribeMeeting(meetingId.value)
    // 重新加载会议状态和转写结果
    await loadMeeting()
    await loadTranscript()
    activeTab.value = 'transcript'
    ElNotification({
      title: '转写完成',
      message: '语音转写已完成，可在"语音转写"标签页查看结果',
      type: 'success',
    })
  } catch {
    await loadMeeting() // 刷新状态（可能失败）
  } finally {
    loading.value = false
  }
}

/**
 * 触发AI纪要生成
 */
const doSummarize = async () => {
  loading.value = true
  ElMessage.info('正在生成AI会议纪要，请稍候...')
  try {
    await summarizeMeeting(meetingId.value)
    await loadMeeting()
    await loadSummary()
    activeTab.value = 'summary'
    ElNotification({
      title: '纪要生成完成',
      message: 'AI会议纪要已生成，可查看摘要、待办事项和发言人总结',
      type: 'success',
    })
  } catch {
    await loadMeeting()
  } finally {
    loading.value = false
  }
}

/**
 * 导出纪要
 */
const handleExport = async (format) => {
  try {
    ElMessage.info(`正在导出 ${format.toUpperCase()} 文件...`)
    const blob = await exportMinutes(meetingId.value, format)
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${meeting.value?.title || '会议纪要'}_纪要.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success(`${format.toUpperCase()} 导出成功`)
  } catch {
    // 错误已在拦截器处理
  }
}

// 工具函数
const formatDate = (d) => (d ? new Date(d).toLocaleString('zh-CN') : '-')
const formatFileSize = (b) => {
  if (!b) return '-'
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1024 * 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(1)} MB`
  return `${(b / (1024 * 1024 * 1024)).toFixed(2)} GB`
}
const formatTime = (seconds) => {
  if (seconds == null) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
const statusType = (s) => {
  const m = { uploaded: 'info', transcribing: 'warning', transcribed: '', summarizing: 'warning', completed: 'success', failed: 'danger' }
  return m[s] || 'info'
}
const statusText = (s) => {
  const m = { uploaded: '已上传', transcribing: '转写中', transcribed: '已转写', summarizing: '生成中', completed: '已完成', failed: '失败' }
  return m[s] || s
}

onMounted(async () => {
  await loadMeeting()
  // 根据当前状态决定加载哪些数据
  if (meeting.value?.status === 'completed') {
    await loadSummary() // 包含转写数据
  } else if (meeting.value?.status === 'transcribed' || meeting.value?.status === 'summarizing') {
    await loadTranscript()
  }
})

// 监听会议状态变化，自动刷新数据
watch(() => meeting.value?.status, (newStatus) => {
  if (newStatus === 'completed') {
    loadSummary()
  } else if (newStatus === 'transcribed') {
    loadTranscript()
  }
})
</script>

<style scoped>
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.transcript-segment {
  margin-bottom: 16px;
  padding: 14px;
  background: #FAFAFA;
  border-radius: 8px;
  border-left: 3px solid #409EFF;
}

.segment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.segment-time {
  font-size: 12px;
  color: #909399;
}

.segment-content {
  line-height: 1.8;
  color: #303133;
}

.summary-content {
  line-height: 2;
  font-size: 15px;
  color: #303133;
  white-space: pre-wrap;
}

.keywords-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #EBEEF5;
}
</style>
