import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from './Tabs'

function ControlledTabs({ defaultTab = 'a' }: { defaultTab?: string }) {
  const [value, setValue] = useState(defaultTab)
  return (
    <TabsRoot value={value} onChange={setValue}>
      <TabsList>
        <TabsTrigger value="a">Tab A</TabsTrigger>
        <TabsTrigger value="b">Tab B</TabsTrigger>
        <TabsTrigger value="c" disabled>Tab C</TabsTrigger>
      </TabsList>
      <TabsContent value="a">Content A</TabsContent>
      <TabsContent value="b">Content B</TabsContent>
      <TabsContent value="c">Content C</TabsContent>
    </TabsRoot>
  )
}

import { useState } from 'react'

describe('Tabs', () => {
  it('renders the active tab content', () => {
    render(<ControlledTabs defaultTab="a" />)
    expect(screen.getByText('Content A')).toBeInTheDocument()
    expect(screen.queryByText('Content B')).not.toBeInTheDocument()
  })

  it('switches content when clicking a different tab', () => {
    render(<ControlledTabs defaultTab="a" />)
    fireEvent.click(screen.getByRole('tab', { name: 'Tab B' }))
    expect(screen.queryByText('Content A')).not.toBeInTheDocument()
    expect(screen.getByText('Content B')).toBeInTheDocument()
  })

  it('does not switch to a disabled tab when clicked', () => {
    render(<ControlledTabs defaultTab="a" />)
    fireEvent.click(screen.getByRole('tab', { name: 'Tab C' }))
    // Content should still be A because Tab C is disabled
    expect(screen.getByText('Content A')).toBeInTheDocument()
    expect(screen.queryByText('Content C')).not.toBeInTheDocument()
  })

  it('only the active tab is in the tab sequence', () => {
    render(<ControlledTabs defaultTab="a" />)
    const tabs = screen.getAllByRole('tab')
    expect(tabs[0]).toHaveAttribute('tabIndex', '0')
    expect(tabs[1]).toHaveAttribute('tabIndex', '-1')
    expect(tabs[2]).toHaveAttribute('tabIndex', '-1')
  })

  it('updates tabIndex after switching tabs', () => {
    render(<ControlledTabs defaultTab="a" />)
    fireEvent.click(screen.getByRole('tab', { name: 'Tab B' }))
    const tabs = screen.getAllByRole('tab')
    expect(tabs[0]).toHaveAttribute('tabIndex', '-1')
    expect(tabs[1]).toHaveAttribute('tabIndex', '0')
    expect(tabs[2]).toHaveAttribute('tabIndex', '-1')
  })
})
