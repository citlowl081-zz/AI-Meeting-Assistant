<template>
  <AppLayout>
    <div class="page-container">
      <h2 style="margin-bottom: 20px;">上传会议录音</h2>

      <el-card shadow="hover">
        <el-form
          ref="formRef"
          :model="uploadForm"
          :rules="rules"
          label-position="top"
          size="large"
        >
          <!-- 会议标题 -->
          <el-form-item label="会议标题" prop="title">
            <el-input
              v-model="uploadForm.title"
              placeholder="请输入会议标题，如：2024年Q4产品规划会议"
              maxlength="255"
              show-word-limit
            />
          </el-form-item>

          <!-- 文件上传区域 -->
          <el-form-item label="音频/视频文件" prop="file">
            <el-upload
              ref="uploadRef"
              class="upload-area"
              drag
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :before-upload="beforeUpload"
              accept=".mp3,.wav,.m4a,.mp4,.aac,.flac,.ogg,.wma"
            >
              <el-icon class="upload-icon" :size="64"><UploadFilled /></el-icon>
              <div class="upload-text">
                <p>将文件拖拽到此处，或<em>点击上传</em></p>
                <p class="upload-hint">
                  支持 mp3, wav, m4a, mp4 等格式，最大 6GB
                </p>
              </div>
            </el-upload>
          </el-form-item>

          <!-- 选中文件的信息显示 -->
          <div v-if="selectedFile" class="file-info-card">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="文件名">
                {{ selectedFile.name }}
              </el-descriptions-item>
              <el-descriptions-item label="文件大小">
                {{ formatFileSize(selectedFile.size) }}
              </el-descriptions-item>
              <el-descriptions-item label="文件类型">
                {{ getFileExtension(selectedFile.name).toUpperCase() }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 上传进度条 -->
          <div v-if="uploading" style="margin-bottom: 16px;">
            <el-progress
              :percentage="uploadPercent"
              :status="uploadPercent === 100 ? 'success' : ''"
              :stroke-width="16"
              text-inside
            />
          </div>

          <!-- 提交按钮 -->
          <el-form-item>
            <el-button
              type="primary"
              :loading="uploading"
              :disabled="!selectedFile"
              @click="handleUpload"
              size="large"
            >
              <el-icon><Upload /></el-icon>
              {{ uploading ? '上传中...' : '开始上传' }}
            </el-button>
            <el-button @click="$router.back()" size="large">返回</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup>
/**
 * 会议上传页面
 * 支持拖拽上传，实时显示进度，上传成功后自动跳转详情页
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, Upload } from '@element-plus/icons-vue'
import AppLayout from '../components/AppLayout.vue'
import { uploadMeeting } from '../api/meeting'

const router = useRouter()
const formRef = ref(null)
const uploadRef = ref(null)

// 表单数据
const uploadForm = reactive({ title: '' })
// 选中的文件
const selectedFile = ref(null)
// 上传状态
const uploading = ref(false)
const uploadPercent = ref(0)

// 最大文件大小 6GB
const MAX_SIZE = 6 * 1024 * 1024 * 1024

const rules = {
  title: [
    { required: true, message: '请输入会议标题', trigger: 'blur' },
    { min: 1, max: 255, message: '标题长度1-255个字符', trigger: 'blur' },
  ],
}

/**
 * 文件选择变化
 */
const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

/**
 * 文件移除
 */
const handleFileRemove = () => {
  selectedFile.value = null
}

/**
 * 上传前校验（格式和大小）
 */
const beforeUpload = (file) => {
  const ext = file.name.split('.').pop()?.toLowerCase()
  const allowed = ['mp3', 'wav', 'm4a', 'mp4', 'aac', 'flac', 'ogg', 'wma']
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的格式 .${ext}，仅支持: ${allowed.join(', ')}`)
    return false
  }
  if (file.size > MAX_SIZE) {
    ElMessage.error('文件大小超过 6GB 限制')
    return false
  }
  return true
}

/**
 * 格式化文件大小显示
 */
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

/**
 * 获取文件扩展名
 */
const getFileExtension = (filename) => {
  return filename.split('.').pop()?.toLowerCase() || ''
}

/**
 * 处理上传
 */
const handleUpload = async () => {
  // 校验表单
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (!selectedFile.value) {
    ElMessage.error('请选择要上传的文件')
    return
  }

  // 构建 FormData
  const formData = new FormData()
  formData.append('title', uploadForm.title)
  formData.append('file', selectedFile.value)

  uploading.value = true
  uploadPercent.value = 0

  try {
    const result = await uploadMeeting(formData, (percent) => {
      // 更新上传进度
      uploadPercent.value = percent
    })

    ElMessage.success('文件上传成功！')

    // 跳转到会议详情页
    router.push(`/meetings/${result.id}`)
  } catch (error) {
    // 错误已在拦截器处理
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.upload-area {
  width: 100%;
}

.upload-icon {
  color: #C0C4CC;
  margin-bottom: 8px;
}

.upload-text p {
  font-size: 14px;
  color: #606266;
  line-height: 1.8;
}

.upload-hint {
  color: #C0C4CC !important;
  font-size: 12px !important;
}

.file-info-card {
  margin-bottom: 20px;
}
</style>
