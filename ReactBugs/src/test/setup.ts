import '@testing-library/jest-dom'
import { afterEach, beforeEach, vi } from 'vitest'

// localStorage stub
const store: Record<string, string> = {}
beforeEach(() => {
  Object.keys(store).forEach((k) => delete store[k])
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v },
    removeItem: (k: string) => { delete store[k] },
    clear: () => { Object.keys(store).forEach((k) => delete store[k]) },
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})
