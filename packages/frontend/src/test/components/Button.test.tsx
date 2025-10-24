import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

describe('Button Component Tests', () => {
  it('should render a button element', () => {
    const { container } = render(<button>Test Button</button>)
    const button = container.querySelector('button')
    expect(button).toBeInTheDocument()
  })

  it('should handle click events', async () => {
    let clicked = false
    const handleClick = () => {
      clicked = true
    }

    render(<button onClick={handleClick}>Click Me</button>)
    const button = screen.getByText('Click Me')
    
    await userEvent.click(button)
    expect(clicked).toBe(true)
  })

  it('should be disabled when disabled prop is set', () => {
    render(<button disabled>Disabled Button</button>)
    const button = screen.getByText('Disabled Button')
    expect(button).toBeDisabled()
  })
})
