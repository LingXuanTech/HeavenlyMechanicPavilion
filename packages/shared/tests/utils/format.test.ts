import { describe, it, expect } from 'vitest'

import { formatCurrency, formatDate, formatPercent } from '../../src/utils/format'

describe('format utilities', () => {
  it('formats currency values', () => {
    const formatted = formatCurrency(1234.56, 'USD', 'en-US')
    expect(formatted).toBe('$1,234.56')
  })

  it('formats percentages with precision', () => {
    const formatted = formatPercent(0.12345)
    expect(formatted).toBe('12.35%')
  })

  it('formats dates consistently', () => {
    const formatted = formatDate('2024-03-15', 'en-US')
    expect(formatted).toBe('Mar 15, 2024')
  })
})
