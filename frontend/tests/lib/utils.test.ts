import { describe, test, expect } from 'vitest'
import { formatTimestamp, formatDuration, getStatusRefetchInterval } from '@/lib/utils'
import type { RecordingStatus } from '@/lib/types'

describe('formatTimestamp', () => {
  test('0 → "00:00"', () => expect(formatTimestamp(0)).toBe('00:00'))
  test('90 → "01:30"', () => expect(formatTimestamp(90)).toBe('01:30'))
  test('floors fractional seconds', () => expect(formatTimestamp(59.9)).toBe('00:59'))
  test('61:01 for 3661 seconds', () => expect(formatTimestamp(3661)).toBe('61:01'))
})

describe('formatDuration', () => {
  test('45 s → "0:45"', () => expect(formatDuration(45)).toBe('0:45'))
  test('90 s → "1:30"', () => expect(formatDuration(90)).toBe('1:30'))
  test('3661 s → "1:01:01"', () => expect(formatDuration(3661)).toBe('1:01:01'))
})

describe('getStatusRefetchInterval', () => {
  test.each<[RecordingStatus | undefined, number | false]>([
    ['ready',        false],
    ['failed',       false],
    [undefined,      false],
    ['queued',       3000],
    ['transcribing', 3000],
    ['diarizing',    3000],
    ['embedding',    3000],
  ])('status=%s → %s', (status, expected) => {
    expect(getStatusRefetchInterval(status)).toBe(expected)
  })
})
