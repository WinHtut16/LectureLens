import { http, HttpResponse } from 'msw'

export const BASE = 'http://localhost:8000/api/v1'

export const MOCK_USER = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'test@example.com',
  created_at: '2026-01-01T00:00:00Z',
}

export const MOCK_TOKEN = 'mock.jwt.token'

export const MOCK_RECORDING_READY = {
  id: '00000000-0000-0000-0000-000000000011',
  title: 'finished.mp3',
  status: 'ready' as const,
  duration_seconds: 1800,
  error_message: null,
  created_at: '2026-01-01T09:00:00Z',
}

export const MOCK_RECORDING_QUEUED = {
  id: '00000000-0000-0000-0000-000000000010',
  title: 'lecture.mp3',
  status: 'queued' as const,
  duration_seconds: null,
  error_message: null,
  created_at: '2026-01-01T10:00:00Z',
}

export const MOCK_SEGMENTS = [
  {
    id: 'seg-1',
    segment_index: 0,
    start_seconds: 0,
    end_seconds: 30,
    text: 'Hello welcome to today',
    speaker_label: null,
  },
  {
    id: 'seg-2',
    segment_index: 1,
    start_seconds: 30,
    end_seconds: 60,
    text: 'We will cover gradient descent',
    speaker_label: null,
  },
]

export const MOCK_SEGMENTS_WITH_SPEAKERS = [
  {
    id: 'seg-1',
    segment_index: 0,
    start_seconds: 0,
    end_seconds: 30,
    text: 'Hello welcome to today',
    speaker_label: 'Speaker 1',
  },
  {
    id: 'seg-2',
    segment_index: 1,
    start_seconds: 30,
    end_seconds: 60,
    text: 'We will cover gradient descent',
    speaker_label: 'Speaker 2',
  },
  {
    id: 'seg-3',
    segment_index: 2,
    start_seconds: 60,
    end_seconds: 90,
    text: 'Any questions so far?',
    speaker_label: 'Speaker 1',
  },
]

export const MOCK_SEARCH_RESULTS = {
  results: [
    {
      segment_id: 'seg-2',
      start_seconds: 30,
      end_seconds: 60,
      text: 'We will cover gradient descent',
      score: 0.92,
      speaker_label: 'Speaker 2',
    },
    {
      segment_id: 'seg-3',
      start_seconds: 60,
      end_seconds: 90,
      text: 'Any questions so far?',
      score: 0.75,
      speaker_label: 'Speaker 1',
    },
  ],
  query_time_ms: 312,
}

export const handlers = [
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string }
    if (body.email === MOCK_USER.email && body.password === 'correct-password') {
      return HttpResponse.json({ token: MOCK_TOKEN, user: MOCK_USER })
    }
    return HttpResponse.json(
      { error: { code: 'invalid_credentials', message: 'Invalid email or password' } },
      { status: 401 },
    )
  }),

  http.post(`${BASE}/auth/signup`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string }
    return HttpResponse.json(
      { token: MOCK_TOKEN, user: { ...MOCK_USER, email: body.email } },
      { status: 201 },
    )
  }),

  http.get(`${BASE}/recordings`, () => {
    return HttpResponse.json([MOCK_RECORDING_READY, MOCK_RECORDING_QUEUED])
  }),

  http.get(`${BASE}/recordings/:id`, ({ params }) => {
    if (params.id === MOCK_RECORDING_READY.id) {
      return HttpResponse.json({
        ...MOCK_RECORDING_READY,
        source_type: 'upload',
        source_url: null,
        segments: MOCK_SEGMENTS,
      })
    }
    return HttpResponse.json(
      { error: { code: 'not_found', message: 'Not found' } },
      { status: 404 },
    )
  }),

  http.get(`${BASE}/recordings/:id/status`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: 'queued',
      error_message: null,
    })
  }),

  http.post(`${BASE}/recordings`, () => {
    return HttpResponse.json(
      { id: '00000000-0000-0000-0000-000000000099', title: 'new.mp3', status: 'queued' },
      { status: 201 },
    )
  }),

  http.post(`${BASE}/recordings/:id/search`, async ({ request }) => {
    const body = (await request.json()) as { query: string; k?: number; speaker_label?: string }
    if (!body.query.trim()) {
      return HttpResponse.json(
        { error: { code: 'validation_error', message: 'Query cannot be empty' } },
        { status: 400 },
      )
    }
    return HttpResponse.json(MOCK_SEARCH_RESULTS)
  }),
]
