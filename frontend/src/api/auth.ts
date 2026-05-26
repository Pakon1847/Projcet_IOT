import { api } from './client'

export interface LoginPayload { username: string; password: string }
export interface RegisterPayload { username: string; email: string; password: string }
export interface TokenResponse { access_token: string; token_type: string }
export interface UserInfo {
  id: number
  username: string
  email: string
  is_admin: boolean
}

export const authApi = {
  login: (data: LoginPayload) =>
    api.post<TokenResponse>('/api/auth/login', data, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),

  register: (data: RegisterPayload) =>
    api.post<UserInfo>('/api/auth/register', data),

  me: () => api.get<UserInfo>('/api/auth/me'),
}
