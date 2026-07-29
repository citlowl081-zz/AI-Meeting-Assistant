/**
 * 会议相关 API 接口
 * 包含上传、列表、详情、转写、摘要、导出等
 */
import api from './index'

/**
 * 上传会议音频/视频文件
 * @param {FormData} formData - 包含 title 和 file 字段
 * @param {Function} onProgress - 上传进度回调 (0-100)
 * @returns {Promise} 会议信息
 */
export function uploadMeeting(formData, onProgress) {
  return api.post('/meetings/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        onProgress(percent)
      }
    },
  })
}

/**
 * 获取会议列表（分页）
 * @param {Object} params - { page, page_size, status }
 * @returns {Promise} { total, page, page_size, items }
 */
export function getMeetingList(params = {}) {
  return api.get('/meetings', { params })
}

/**
 * 获取会议详情
 * @param {number} id - 会议ID
 * @returns {Promise} 会议详细信息
 */
export function getMeetingDetail(id) {
  return api.get(`/meetings/${id}`)
}

/**
 * 删除会议
 * @param {number} id - 会议ID
 * @returns {Promise}
 */
export function deleteMeeting(id) {
  return api.delete(`/meetings/${id}`)
}

/**
 * 触发语音转写（ASR）
 * @param {number} id - 会议ID
 * @returns {Promise} { message, segments_count }
 */
export function transcribeMeeting(id) {
  return api.post(`/meetings/${id}/transcribe`)
}

/**
 * 获取转写结果
 * @param {number} id - 会议ID
 * @returns {Promise} { meeting_id, speakers, segments, full_text }
 */
export function getTranscript(id) {
  return api.get(`/meetings/${id}/transcript`)
}

/**
 * 生成 AI 会议纪要
 * @param {number} id - 会议ID
 * @returns {Promise} { message }
 */
export function summarizeMeeting(id) {
  return api.post(`/meetings/${id}/summarize`)
}

/**
 * 获取会议完整纪要
 * @param {number} id - 会议ID
 * @returns {Promise} { meeting_id, title, transcript, summary, action_items, speaker_summaries }
 */
export function getMeetingSummary(id) {
  return api.get(`/meetings/${id}/summary`)
}

/**
 * 导出会议纪要
 * @param {number} id - 会议ID
 * @param {string} format - 导出格式 'md' 或 'pdf'
 * @returns {Promise} Blob 文件流
 */
export async function exportMinutes(id, format = 'md') {
  const response = await api.get(`/meetings/${id}/export`, {
    params: { format },
    responseType: 'blob',
  })
  return response
}
