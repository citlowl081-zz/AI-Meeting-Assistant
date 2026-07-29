<template>
  <AppLayout>
    <div class="page-container">
      <div class="page-header">
        <h2>会议列表</h2>
        <el-button type="primary" @click="$router.push('/upload')">
          <el-icon><Upload /></el-icon> 上传新会议
        </el-button>
      </div>

      <!-- 筛选栏 -->
      <el-card shadow="hover" style="margin-bottom: 16px;">
        <el-form :inline="true" :model="filterForm">
          <el-form-item label="状态筛选">
            <el-select
              v-model="filterForm.status"
              placeholder="全部状态"
              clearable
              @change="handleFilter"
            >
              <el-option label="全部" value="" />
              <el-option label="已上传" value="uploaded" />
              <el-option label="转写中" value="transcribing" />
              <el-option label="已转写" value="transcribed" />
              <el-option label="生成中" value="summarizing" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 会议表格 -->
      <el-card shadow="hover">
        <el-table
          :data="meetings"
          v-loading="loading"
          empty-text="暂无会议记录"
        >
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="title" label="会议标题" min-width="220">
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
          <el-table-column label="文件大小" width="120">
            <template #default="{ row }">
              {{ formatFileSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">
                {{ statusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="$router.push(`/meetings/${row.id}`)">
                查看
              </el-button>
              <el-button text type="danger" size="small" @click="handleDelete(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div style="margin-top: 16px; display: flex; justify-content: flex-end;">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[5, 10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="loadMeetings"
            @current-change="loadMeetings"
          />
        </div>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup>
/**
 * 会议列表页面
 * 支持状态筛选、分页浏览、删除操作
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import AppLayout from '../components/AppLayout.vue'
import { getMeetingList, deleteMeeting } from '../api/meeting'

const loading = ref(false)
const meetings = ref([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const filterForm = reactive({ status: '' })

/**
 * 加载会议列表
 */
const loadMeetings = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filterForm.status) params.status = filterForm.status

    const result = await getMeetingList(params)
    meetings.value = result.items || []
    total.value = result.total || 0
  } catch {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}

/**
 * 状态筛选
 */
const handleFilter = () => {
  page.value = 1
  loadMeetings()
}

/**
 * 删除会议
 */
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除会议「${row.title}」吗？删除后数据无法恢复。`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  try {
    await deleteMeeting(row.id)
    ElMessage.success('删除成功')
    loadMeetings()
  } catch {
    // 错误已在拦截器处理
  }
}

const formatDate = (d) => (d ? new Date(d).toLocaleString('zh-CN') : '-')

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

const statusType = (s) => {
  const m = { uploaded: 'info', transcribing: 'warning', transcribed: '', summarizing: 'warning', completed: 'success', failed: 'danger' }
  return m[s] || 'info'
}

const statusText = (s) => {
  const m = { uploaded: '已上传', transcribing: '转写中', transcribed: '已转写', summarizing: '生成中', completed: '已完成', failed: '失败' }
  return m[s] || s
}

onMounted(loadMeetings)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
}
</style>
