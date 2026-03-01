import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { MemoryRouter } from "react-router-dom";

function TestProviders({ children }: PropsWithChildren) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

export function renderWithProviders(ui: React.ReactElement) {
  return render(ui, { wrapper: TestProviders });
}
