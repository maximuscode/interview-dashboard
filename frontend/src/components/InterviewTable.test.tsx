import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { InterviewTable } from './InterviewTable'
import type { InterviewSummary } from '../lib/types'

const items: InterviewSummary[] = [
  {
    id: 'i1',
    candidate_name: 'Ada Lovelace',
    candidate_email: 'ada@example.com',
    position: 'Backend Engineer',
    interview_date: '2026-01-10',
    overall_score: 90,
    band: 'strong',
    reviewed: false,
  },
]

function renderTable() {
  return render(
    <MemoryRouter>
      <InterviewTable items={items} search="" />
    </MemoryRouter>,
  )
}

describe('InterviewTable responsiveness', () => {
  it('renders both a desktop table and a mobile card list', () => {
    // Columns do not fit a phone, so the same rows render twice and CSS picks
    // one. Both must exist, or one breakpoint shows nothing at all.
    const { container } = renderTable()
    expect(container.querySelector('table')).not.toBeNull()
    expect(container.querySelector('ul')).not.toBeNull()
  })

  it('hides the table below md and the cards at md and above', () => {
    const { container } = renderTable()
    const table = container.querySelector('table')!
    const cards = container.querySelector('ul')!

    expect(table.className).toContain('hidden')
    expect(table.className).toContain('md:table')
    expect(cards.className).toContain('md:hidden')
  })

  it('shows the same candidate in both layouts', () => {
    const { container } = renderTable()
    const table = container.querySelector('table')!
    const cards = container.querySelector('ul')!

    expect(within(table).getByText('Ada Lovelace')).toBeInTheDocument()
    expect(within(cards).getByText('Ada Lovelace')).toBeInTheDocument()
  })

  it('links to the detail page from both layouts', () => {
    renderTable()
    const links = screen.getAllByRole('link', { name: /Ada Lovelace/ })
    expect(links).toHaveLength(2)
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/interviews/i1')
    }
  })

  it('keeps the active filters in the detail link', () => {
    render(
      <MemoryRouter>
        <InterviewTable items={items} search="?min_score=80" />
      </MemoryRouter>,
    )
    expect(screen.getAllByRole('link', { name: /Ada Lovelace/ })[0]).toHaveAttribute(
      'href',
      '/interviews/i1?min_score=80',
    )
  })
})

describe('mobile layout details', () => {
  it('keeps the score badge from being squeezed by a long name', () => {
    const { container } = renderTable()
    const cards = container.querySelector('ul')!
    expect(cards.querySelector('.shrink-0')).not.toBeNull()
  })
})
