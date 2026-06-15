export type RecordingStatus =
  | 'queued'
  | 'transcribing'
  | 'diarizing'
  | 'embedding'
  | 'ready'
  | 'failed'

export type SourceType = 'upload' | 'youtube'

export interface User {
  id: string
  email: string
  created_at: string
}

export interface AuthResponse {
  token: string
  user: User
}

export interface Segment {
  id: string
  start_seconds: number
  end_seconds: number
  text: string
  speaker_label: string | null
  segment_index: number
}

export interface RecordingListItem {
  id: string
  title: string
  status: RecordingStatus
  duration_seconds: number | null
  error_message: string | null
  created_at: string
}

export interface RecordingDetailResponse {
  id: string
  title: string
  source_type: SourceType
  source_url: string | null
  status: RecordingStatus
  duration_seconds: number | null
  error_message: string | null
  created_at: string
  segments: Segment[]
}

export interface RecordingStatusResponse {
  id: string
  status: RecordingStatus
  error_message: string | null
}

export interface RecordingCreatedResponse {
  id: string
  title: string
  status: RecordingStatus
}
