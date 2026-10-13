type RequestIdStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>

export class RequestTimeoutError extends Error {
  constructor() {
    super('The request exceeded its browser time limit.')
    this.name = 'RequestTimeoutError'
  }
}

export async function withAbortTimeout<T>(
  timeoutMs: number,
  operation: (signal: AbortSignal) => Promise<T>,
): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const timeout = globalThis.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  try {
    return await operation(controller.signal)
  } catch (error: unknown) {
    if (timedOut) throw new RequestTimeoutError()
    throw error
  } finally {
    globalThis.clearTimeout(timeout)
  }
}

export function getOrCreatePendingRequestId(
  storage: RequestIdStorage | null,
  key: string,
  createId: () => string,
): string {
  if (storage) {
    try {
      const storedId = storage.getItem(key)
      if (storedId) return storedId
    } catch {
      storage = null
    }
  }

  const requestId = createId()
  if (storage) {
    try {
      storage.setItem(key, requestId)
    } catch {
      return requestId
    }
  }
  return requestId
}

export function clearPendingRequestId(storage: RequestIdStorage | null, key: string): void {
  if (!storage) return
  try {
    storage.removeItem(key)
  } catch {
    return
  }
}
