// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EstimatorRoute from './page'

const pendingWorkspace = new Promise(() => {})

vi.mock('@/components/estimator/EstimatorPage', () => ({
  EstimatorPage: function MockEstimatorPage() {
    throw pendingWorkspace
  },
}))

describe('Estimator route', () => {
  it('shows skeleton loaders while the pricing workspace suspends', () => {
    render(<EstimatorRoute />)

    // Check for skeleton elements that indicate loading state
    expect(document.querySelector('.skeleton')).toBeInTheDocument()
  })
})
