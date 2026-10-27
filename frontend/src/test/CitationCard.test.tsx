import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CitationCard } from '../components/CitationCard';
import { Citation } from '../types';

describe('CitationCard Component', () => {
  const mockCitation: Citation = {
    document_id: 'doc-uuid-1234',
    filename: 'quarterly_report.pdf',
    page_number: 7,
    excerpt: 'Total revenue grew by 14% year-over-year according to GAAP metrics.',
    chunk_id: 'chunk-999',
  };

  it('renders filename, page number, and text excerpt accurately', () => {
    const handleOpenPdf = vi.fn();
    render(<CitationCard citation={mockCitation} onOpenPdf={handleOpenPdf} />);

    expect(screen.getByText('quarterly_report.pdf')).toBeInTheDocument();
    expect(screen.getByText(/p\.\s*7/)).toBeInTheDocument();
    expect(screen.getByText(/"Total revenue grew by 14% year-over-year according to GAAP metrics\."/)).toBeInTheDocument();
  });

  it('calls onOpenPdf with documentId, pageNumber, and filename on click', () => {
    const handleOpenPdf = vi.fn();
    render(<CitationCard citation={mockCitation} onOpenPdf={handleOpenPdf} />);

    fireEvent.click(screen.getByText('quarterly_report.pdf'));

    expect(handleOpenPdf).toHaveBeenCalledTimes(1);
    expect(handleOpenPdf).toHaveBeenCalledWith('doc-uuid-1234', 7, 'quarterly_report.pdf');
  });
});
