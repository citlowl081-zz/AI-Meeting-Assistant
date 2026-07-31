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
          <!-- 导出纯对话：转写完成后即可用 -->
          <el-dropdown @command="handleExportTranscript" v-if="canExportTranscript">
            <el-button>
              导出对话 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="transcript-md">
                  <el-icon><Document /></el-icon> 对话 Markdown
                </el-dropdown-item>
                <el-dropdown-item command="transcript-pdf">
                  <el-icon><Printer /></el-icon> 对话 PDF
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 导出完整纪要：摘要生成完成后才可用 -->
          <el-dropdown @command="handleExportFull" v-if="meeting?.status === 'completed'">
            <el-button type="primary">
              导出纪要 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="full-md">
                  <el-icon><Document /></el-icon> 纪要 Markdown
                </el-dropdown-item>
                <el-dropdown-item command="full-pdf">
                  <el-icon><Printer /></el-icon> 纪要 PDF
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 语音转写按钮：上传后/失败后/已有转写时可重新转写 -->
          <el-button
            type="primary"
            :loading="loading && actionType === 'transcribe'"
            :disabled="!canTranscribe"
            @click="doTranscribe"
          >
            <el-icon><Microphone /></el-icon> {{ meeting?.status === 'transcribed' || meeting?.status === 'completed' ? '重新转写' : '语音转写' }}
          </el-button>

          <!-- 生成AI纪要按钮：转写完成后可生成 -->
          <el-button
            type="success"
            :loading="loading && actionType === 'summarize'"
            :disabled="!canSummarize"
            @click="doSummarize"
          >
            <el-icon><MagicStick /></el-icon> {{ meeting?.status === 'completed' ? '重新生成纪要' : '生成AI纪要' }}
          </el-button>
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
            <!-- 说话人名称管理工具栏 -->
            <div v-if="transcript?.speakers?.length" class="speaker-toolbar">
              <span class="speaker-toolbar-title">说话人名称：</span>
              <template v-for="spk in transcript.speakers" :key="spk">
                <el-popover
                  :visible="editingSpeaker === spk"
                  placement="bottom"
                  :width="220"
                  trigger="click"
                >
                  <template #reference>
                    <el-tag
                      size="small"
                      effect="dark"
                      :color="getSpeakerColor(spk)"
                      class="speaker-editable-tag"
                      @click="editingSpeaker = spk"
                      style="cursor: pointer;"
                    >
                      {{ getSpeakerName(spk) }}
                      <el-icon style="margin-left: 4px;"><EditPen /></el-icon>
                    </el-tag>
                  </template>
                  <div style="display: flex; gap: 8px;">
                    <el-input
                      v-model="speakerEditValue"
                      size="small"
                      placeholder="输入名称"
                      @keyup.enter="saveSpeakerName(spk)"
                    />
                    <el-button type="primary" size="small" @click="saveSpeakerName(spk)">确定</el-button>
                  </div>
                </el-popover>
              </template>
              <el-button text size="small" type="primary" @click="resetSpeakerNames" v-if="hasCustomNames">
                恢复默认
              </el-button>
            </div>

            <div v-if="transcript?.segments?.length" style="margin-top: 12px;">
              <div
                v-for="seg in transcript.segments"
                :key="seg.sequence || seg.id"
                class="transcript-segment"
              >
                <div class="segment-header">
                  <el-tag
                    size="small"
                    effect="dark"
                    :color="getSpeakerColor(seg.speaker)"
                  >{{ getSpeakerName(seg.speaker) }}</el-tag>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { Loading, EditPen, Microphone, MagicStick } from '@element-plus/icons-vue'
import AppLayout from '../components/AppLayout.vue'
import {
  getMeetingDetail,
  getTranscript,
  transcribeMeeting,
  summarizeMeeting,
  getMeetingSummary,
  exportMinutes,
  getSpeakerMapping,
  updateSpeakerMapping,
} from '../api/meeting'

const route = useRoute()
const router = useRouter()
const meetingId = computed(() => Number(route.params.id))

const loading = ref(false)
const actionType = ref('')  // 当前正在执行的操作类型 'transcribe' | 'summarize'
const meeting = ref(null)
const activeTab = ref('transcript')

// 是否可以转写：已上传/失败/已转写/已完成 状态下都可以
const canTranscribe = computed(() => {
  if (!meeting.value) return false
  return ['uploaded', 'failed', 'transcribed', 'completed'].includes(meeting.value.status)
})

// 是否可以生成纪要：已转写/已完成 状态下可以
const canSummarize = computed(() => {
  if (!meeting.value) return false
  return ['transcribed', 'completed'].includes(meeting.value.status)
})

// 是否可以导出纯对话：已转写/已完成 状态下可以
const canExportTranscript = computed(() => {
  if (!meeting.value) return false
  return ['transcribed', 'summarizing', 'completed'].includes(meeting.value.status)
})

// 转写数据
const transcript = ref(null)
// 完整纪要数据（摘要 + 待办 + 发言人总结）
const minutesData = ref(null)

// ============================================================
// 说话人名称管理
// ============================================================
// 说话人名称映射 { speaker1: "张医生", speaker2: "李家属" }
const speakerMapping = ref({})
// 当前正在编辑的说话人
const editingSpeaker = ref(null)
const speakerEditValue = ref('')
// 是否有自定义名称
const hasCustomNames = computed(() => Object.keys(speakerMapping.value).length > 0)

// 说话人颜色列表（不同说话人不同颜色）
const speakerColors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#17B3A3', '#9B59B6', '#34495E']

/**
 * 获取说话人的显示名称（优先使用自定义名，否则用原始标签）
 */
const getSpeakerName = (speaker) => {
  return speakerMapping.value[speaker] || speaker
}

/**
 * 获取说话人对应的颜色
 */
const getSpeakerColor = (speaker) => {
  // 从speaker标签中提取数字（如 speaker1 → 1）
  const match = speaker.match(/\d+/)
  const idx = match ? (parseInt(match[0]) - 1) % speakerColors.length : 0
  return speakerColors[idx]
}

/**
 * 保存说话人名称
 */
const saveSpeakerName = async (speaker) => {
  const name = speakerEditValue.value.trim()
  if (!name) {
    editingSpeaker.value = null
    return
  }
  // 更新本地映射
  speakerMapping.value = { ...speakerMapping.value, [speaker]: name }
  editingSpeaker.value = null

  // 保存到后端
  try {
    await updateSpeakerMapping(meetingId.value, speakerMapping.value)
  } catch {
    // 错误已在拦截器处理
  }
}

/**
 * 恢复默认说话人名称
 */
const resetSpeakerNames = () => {
  speakerMapping.value = {}
  editingSpeaker.value = null
  updateSpeakerMapping(meetingId.value, {}).catch(() => {})
}

/**
 * 加载说话人名称映射
 */
const loadSpeakerMapping = async () => {
  try {
    const result = await getSpeakerMapping(meetingId.value)
    speakerMapping.value = result.mapping || {}
  } catch {
    speakerMapping.value = {}
  }
}

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
 * 触发语音转写
 */
const doTranscribe = async () => {
  loading.value = true
  actionType.value = 'transcribe'
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
    actionType.value = ''
  }
}

/**
 * 触发AI纪要生成
 */
const doSummarize = async () => {
  loading.value = true
  actionType.value = 'summarize'
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
    actionType.value = ''
  }
}

/**
 * 导出纯对话（转写后即可用）
 */
const handleExportTranscript = async (command) => {
  const format = command === 'transcript-pdf' ? 'pdf' : 'md'
  const ext = format === 'pdf' ? 'pdf' : 'md'
  await doExport(format, 'transcript', `${meeting.value?.title || '会议'}_对话记录.${ext}`)
}

/**
 * 导出完整纪要（摘要生成后才可用）
 */
const handleExportFull = async (command) => {
  const format = command === 'full-pdf' ? 'pdf' : 'md'
  const ext = format === 'pdf' ? 'pdf' : 'md'
  await doExport(format, 'full', `${meeting.value?.title || '会议'}_会议纪要.${ext}`)
}

/**
 * 通用导出逻辑
 */
const doExport = async (format, exportType, filename) => {
  try {
    ElMessage.info(`正在导出${exportType === 'transcript' ? '对话' : '纪要'} ${format.toUpperCase()}...`)
    const blob = await exportMinutes(meetingId.value, format, exportType)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    // 延迟清理，确保下载触发
    setTimeout(() => {
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    }, 200)
    ElMessage.success(`${format.toUpperCase()} 导出成功`)
  } catch {
    ElMessage.error('导出失败，请稍后重试')
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

// 轮询定时器
let pollTimer = null

/**
 * 开始轮询会议状态（转写中/摘要生成中时）
 */
const startPolling = () => {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    const status = meeting.value?.status
    // 处理中则刷新状态
    if (status === 'transcribing' || status === 'summarizing') {
      await loadMeeting()
    }
    // 转写完成 → 加载转写结果
    if (meeting.value?.status === 'transcribed' && status === 'transcribing') {
      await loadTranscript()
      stopPolling()
    }
    // 摘要完成 → 加载纪要
    if (meeting.value?.status === 'completed' && status === 'summarizing') {
      await loadSummary()
      stopPolling()
    }
    // 失败 → 停止轮询
    if (meeting.value?.status === 'failed') {
      stopPolling()
    }
    // 稳定状态 → 停止轮询
    if (!['transcribing', 'summarizing'].includes(meeting.value?.status)) {
      stopPolling()
    }
  }, 5000) // 每5秒轮询一次
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  await loadMeeting()
  await loadSpeakerMapping()
  // 根据当前状态决定加载哪些数据
  if (meeting.value?.status === 'completed') {
    await loadSummary()
  } else if (meeting.value?.status === 'transcribed' || meeting.value?.status === 'summarizing') {
    await loadTranscript()
  }
  // 处理中则开始轮询
  if (['transcribing', 'summarizing'].includes(meeting.value?.status)) {
    startPolling()
  }
})

// 监听会议状态变化
watch(() => meeting.value?.status, (newStatus) => {
  if (newStatus === 'completed') {
    loadSummary()
    stopPolling()
  } else if (newStatus === 'transcribed') {
    loadTranscript()
    stopPolling()
  } else if (newStatus === 'transcribing' || newStatus === 'summarizing') {
    startPolling()
  }
})

// 组件卸载时清理定时器
onUnmounted(() => stopPolling())
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

/* 说话人名称工具栏 */
.speaker-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #F5F7FA;
  border-radius: 8px;
  flex-wrap: wrap;
}

.speaker-toolbar-title {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.speaker-editable-tag {
  transition: transform 0.2s;
}

.speaker-editable-tag:hover {
  transform: scale(1.05);
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
