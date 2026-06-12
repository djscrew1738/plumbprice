import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  FadeIn,
  BlurFade,
  SlideUp,
  ScaleIn,
  Pressable,
  CountUp,
  StaggerContainer,
  StaggerItem,
  SlideIn,
  Pulse,
  HeightAuto,
  SmoothPresence,
  MOTION,
} from './Motion'

function setReducedMotion(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)' ? matches : false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

describe('MOTION constants', () => {
  it('exports expected durations and easing', () => {
    expect(MOTION.duration).toEqual({ fast: 0.15, normal: 0.2, slow: 0.35 })
    expect(MOTION.ease).toEqual([0.16, 1, 0.3, 1])
    expect(MOTION.spring).toEqual({ type: 'spring', damping: 28, stiffness: 320 })
  })
})

describe('Motion primitives', () => {
  it('FadeIn renders children', () => {
    render(<FadeIn>hello</FadeIn>)
    expect(screen.getByText('hello')).toBeInTheDocument()
  })

  it('BlurFade renders children', () => {
    render(<BlurFade>blurred</BlurFade>)
    expect(screen.getByText('blurred')).toBeInTheDocument()
  })

  it('SlideUp renders children', () => {
    render(<SlideUp>slide content</SlideUp>)
    expect(screen.getByText('slide content')).toBeInTheDocument()
  })

  it('ScaleIn renders children', () => {
    render(<ScaleIn>scale content</ScaleIn>)
    expect(screen.getByText('scale content')).toBeInTheDocument()
  })

  it('Pressable renders children', () => {
    render(<Pressable>pressable</Pressable>)
    expect(screen.getByText('pressable')).toBeInTheDocument()
  })

  it('CountUp formats initial value', () => {
    render(<CountUp value={1234} formatter={(n) => `$${n.toFixed(0)}`} />)
    expect(screen.getByText('$1234')).toBeInTheDocument()
  })

  it('StaggerContainer and StaggerItem render children', () => {
    render(
      <StaggerContainer>
        <StaggerItem>one</StaggerItem>
        <StaggerItem>two</StaggerItem>
      </StaggerContainer>,
    )
    expect(screen.getByText('one')).toBeInTheDocument()
    expect(screen.getByText('two')).toBeInTheDocument()
  })

  it('SlideIn renders children', () => {
    render(<SlideIn>drawer content</SlideIn>)
    expect(screen.getByText('drawer content')).toBeInTheDocument()
  })

  it('Pulse renders children', () => {
    render(<Pulse>pulse content</Pulse>)
    expect(screen.getByText('pulse content')).toBeInTheDocument()
  })

  it('HeightAuto renders children when open', () => {
    render(<HeightAuto open>accordion content</HeightAuto>)
    expect(screen.getByText('accordion content')).toBeInTheDocument()
  })

  it('HeightAuto hides children when closed', () => {
    const { container } = render(<HeightAuto open={false}>hidden content</HeightAuto>)
    expect(container.firstChild).toHaveStyle('overflow: hidden')
  })

  it('SmoothPresence renders children', () => {
    render(
      <SmoothPresence>
        <div>presence child</div>
      </SmoothPresence>,
    )
    expect(screen.getByText('presence child')).toBeInTheDocument()
  })
})

describe('Reduced motion', () => {
  it('CountUp jumps to target value when reduced motion is preferred', () => {
    setReducedMotion(true)
    const { rerender } = render(<CountUp value={100} formatter={(n) => n.toFixed(0)} />)
    expect(screen.getByText('100')).toBeInTheDocument()

    rerender(<CountUp value={500} formatter={(n) => n.toFixed(0)} />)
    expect(screen.getByText('500')).toBeInTheDocument()
  })

  it('StaggerContainer degrades gracefully under reduced motion', () => {
    setReducedMotion(true)
    render(
      <StaggerContainer>
        <StaggerItem>reduced one</StaggerItem>
      </StaggerContainer>,
    )
    expect(screen.getByText('reduced one')).toBeInTheDocument()
  })
})
