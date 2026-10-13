import assert from 'node:assert/strict'
import test from 'node:test'

import {
  clearPendingRequestId,
  getOrCreatePendingRequestId,
  RequestTimeoutError,
  withAbortTimeout,
} from '../src/api/requestReliability.ts'

class MemoryStorage {
  private values = new Map<string, string>()

  getItem(key: string) {
    return this.values.get(key) ?? null
  }

  setItem(key: string, value: string) {
    this.values.set(key, value)
  }

  removeItem(key: string) {
    this.values.delete(key)
  }
}

test('pending generation identity is reused until a valid response clears it', () => {
  const storage = new MemoryStorage()
  let created = 0
  const createId = () => `request_${++created}`

  assert.equal(getOrCreatePendingRequestId(storage, 'generation', createId), 'request_1')
  assert.equal(getOrCreatePendingRequestId(storage, 'generation', createId), 'request_1')

  clearPendingRequestId(storage, 'generation')

  assert.equal(getOrCreatePendingRequestId(storage, 'generation', createId), 'request_2')
})

test('request timeout aborts the operation and reports a timeout error', async () => {
  let observedAbort = false

  await assert.rejects(
    withAbortTimeout(10, (signal) => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => {
        observedAbort = true
        reject(new DOMException('aborted', 'AbortError'))
      }, { once: true })
    })),
    RequestTimeoutError,
  )

  assert.equal(observedAbort, true)
})
