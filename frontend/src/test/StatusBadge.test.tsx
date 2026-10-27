import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../components/StatusBadge';

describe('StatusBadge Component', () => {
  it('renders Ready state correctly', () => {
    render(<StatusBadge status="ready" />);
    expect(screen.getByText('Ready')).toBeInTheDocument();
  });

  it('renders Indexing state correctly', () => {
    render(<StatusBadge status="processing" />);
    expect(screen.getByText('Indexing...')).toBeInTheDocument();
  });

  it('renders Queued state correctly', () => {
    render(<StatusBadge status="queued" />);
    expect(screen.getByText('Queued')).toBeInTheDocument();
  });

  it('renders Failed state with error message in tooltip', () => {
    render(<StatusBadge status="failed" errorMessage="Invalid PDF structure" />);
    const badge = screen.getByText('Failed');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute('title', 'Invalid PDF structure');
  });
});
