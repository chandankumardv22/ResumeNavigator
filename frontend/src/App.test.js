import { render, screen } from '@testing-library/react';
import App from './App';

test('renders PathFinder branding', () => {
  render(<App />);
  expect(screen.getAllByText(/PathFinder/i).length).toBeGreaterThan(0);
});
