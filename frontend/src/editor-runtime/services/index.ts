import axios from './config'

// export const SERVER_URL = 'http://localhost:5000'
export const SERVER_URL = '/api'

interface AIPPTOutlinePayload {
  content: string
  language: string
  model: string
}

interface AIPPTPayload {
  content: string
  language: string
  style?: string
  model?: string
  generateFromUploadedFile?: boolean
  generateFromWebSearch?: boolean
  sessionId?: string
}


export default {
  getMockData(filename: string): Promise<any> {
    return axios.get(`./mocks/${filename}.json`)
  },

  getFileData(filename: string): Promise<any> {
    return axios.get(`${SERVER_URL}/data/${filename}.json`)
  },

  getTemplates(): Promise<any> {
    return axios.get(`${SERVER_URL}/templates`)
  },

  AIPPT_Outline({
    content,
    language,
    model,
  }: AIPPTOutlinePayload): Promise<any> {
    return fetch(`${SERVER_URL}/tools/aippt_outline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        content,
        language,
        model,
        stream: true,
      }),
    })
  },

  AIPPT_Content({
    content,
    language,
    style,
    model,
    generateFromUploadedFile,
    generateFromWebSearch,
    sessionId,
  }: AIPPTPayload): Promise<any> {
    return fetch(`${SERVER_URL}/tools/ppt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        content,
        language,
        model,
        style,
        stream: true,
        generateFromUploadedFile,
        generateFromWebSearch,
        sessionId,
      }),
    })
  },

  AIPPT_Outline_From_File(file: File, user_id: string, language: string): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', user_id)
    formData.append('language', language)
    return fetch(`${SERVER_URL}/tools/outline_from_file`, {
      method: 'POST',
      headers: {
        'Accept': 'text/event-stream',
      },
      body: formData,
    })
  },

  /**
   * 统一的大纲生成 API
   * - content 必填：主题模式
   * - content + file：混合模式（以文档为主，主题作为补充上下文）
   */
  AIPPT_Outline_Unified({
    content,
    file,
    language = '中文',
    userId = 'default_user',
  }: {
    content?: string
    file?: File
    language?: string
    userId?: string
  }): Promise<Response> {
    const formData = new FormData()
    if (content) {
      formData.append('content', content)
    }
    if (file) {
      formData.append('file', file)
    }
    formData.append('language', language)
    formData.append('user_id', userId)

    return fetch(`${SERVER_URL}/tools/outline`, {
      method: 'POST',
      headers: {
        'Accept': 'text/event-stream',
      },
      body: formData,
    })
  },
}
