import { api } from './client'

export interface ChatMessage {
  role:    'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  device_id: string
  message:   string
  history?:  ChatMessage[]
}

export interface ChatResponse {
  reply:      string
  model:      string
  context_pm25?: number
}

export interface PredictResponse {
  device_id:   string
  predictions: { hour: number; pm25: number }[]
  model:       string
}

export const aiApi = {
  chat: (payload: ChatRequest) =>
    api.post<ChatResponse>('/api/ai/chat', payload),

  predict: (deviceId: string) =>
    api.get<PredictResponse>(`/api/ai/predict/${deviceId}`),
}
