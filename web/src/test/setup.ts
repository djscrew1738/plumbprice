import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

expect.extend(matchers)



// jsdom doesn't implement matchMedia — provide a no-op stub
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// jsdom doesn't implement IndexedDB — stub the minimum surface for Dexie
const fakeIdbFactory = {
  open: vi.fn(() => {
    const req = {
      onsuccess: null as ((this: IDBOpenDBRequest, ev: Event) => unknown) | null,
      onerror: null as ((this: IDBOpenDBRequest, ev: Event) => unknown) | null,
      onupgradeneeded: null as ((this: IDBOpenDBRequest, ev: IDBVersionChangeEvent) => unknown) | null,
      result: {
        createObjectStore: vi.fn(),
        transaction: vi.fn(() => ({
          objectStore: vi.fn(() => ({
            get: vi.fn(() => ({ result: undefined })),
            put: vi.fn(),
            delete: vi.fn(),
            clear: vi.fn(),
            getAll: vi.fn(() => ({ result: [] })),
            openCursor: vi.fn(() => ({ result: null })),
          })),
        })),
        objectStoreNames: { contains: vi.fn(() => true) },
      },
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }
    // Simulate async open success
    queueMicrotask(() => {
      if (req.onsuccess) {
        req.onsuccess.call(req as unknown as IDBOpenDBRequest, new Event('success'))
      }
    })
    return req
  }),
  deleteDatabase: vi.fn(),
  databases: vi.fn(() => Promise.resolve([])),
}
Object.defineProperty(window, 'indexedDB', {
  writable: true,
  value: fakeIdbFactory,
})

// jsdom doesn't implement URL.createObjectURL / revokeObjectURL
if (typeof window !== 'undefined' && !window.URL.createObjectURL) {
  Object.defineProperty(window.URL, 'createObjectURL', {
    writable: true,
    value: vi.fn(() => 'blob:mock'),
  })
  Object.defineProperty(window.URL, 'revokeObjectURL', {
    writable: true,
    value: vi.fn(),
  })
}

afterEach(() => {
  cleanup()
})
