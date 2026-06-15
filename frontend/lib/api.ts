import type {
  AuthResponse,
  RecordingCreatedResponse,
  RecordingDetailResponse,
  RecordingListItem,
  RecordingStatusResponse,
  SearchResponse,
} from '@/lib/types'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {},
): Promise<T> {
  const { token, body, ...rest } = options
  const headers: Record<string, string> = {}

  if (!(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    body,
    headers: { ...headers, ...(rest.headers as Record<string, string> | undefined) },
  })

  if (res.status === 204) return undefined as T

  if (!res.ok) {
    let message = `HTTP ${res.status}`
    let code: string | undefined
    try {
      const err = (await res.json()) as { error?: { message?: string; code?: string } }
      message = err.error?.message ?? message
      code = err.error?.code
    } catch {
      // use default message
    }
    throw new ApiError(res.status, message, code)
  }

  return res.json() as Promise<T>
}

export function signup(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function getRecordings(token: string): Promise<RecordingListItem[]> {
  return request<RecordingListItem[]>('/recordings', { token })
}

export function getRecording(token: string, id: string): Promise<RecordingDetailResponse> {
  return request<RecordingDetailResponse>(`/recordings/${id}`, { token })
}

export function getRecordingStatus(token: string, id: string): Promise<RecordingStatusResponse> {
  return request<RecordingStatusResponse>(`/recordings/${id}/status`, { token })
}

export function uploadRecording(token: string, file: File): Promise<RecordingCreatedResponse> {
  const form = new FormData()
  form.append('file', file)
  return request<RecordingCreatedResponse>('/recordings', {
    method: 'POST',
    body: form,
    token,
  })
}

export function searchRecording(
  token: string,
  id: string,
  query: string,
  k = 10,
  speakerLabel?: string | null,
): Promise<SearchResponse> {
  return request<SearchResponse>(`/recordings/${id}/search`, {
    method: 'POST',
    token,
    body: JSON.stringify({
      query,
      k,
      ...(speakerLabel != null ? { speaker_label: speakerLabel } : {}),
    }),
  })
}
