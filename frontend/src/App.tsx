import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./features/dashboard/DashboardPage";

const ModulesPage = lazy(() =>
  import("./features/modules/ModulesPage").then((module) => ({ default: module.ModulesPage })),
);
const PlaceholderPage = lazy(() =>
  import("./features/placeholders/PlaceholderPage").then((module) => ({
    default: module.PlaceholderPage,
  })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 300_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const lazyElement = (element: React.ReactNode) => (
  <Suspense fallback={<div className="p-4 text-sm">Loading…</div>}>{element}</Suspense>
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: "logs",
        element: lazyElement(
          <PlaceholderPage
            title="Activity Logs"
            description="System execution and scraping history will appear here."
          />,
        ),
      },
      {
        path: "modules",
        element: lazyElement(<ModulesPage />),
      },
      {
        path: "settings",
        element: lazyElement(
          <PlaceholderPage
            title="Settings"
            description="Notification and scheduling configuration will appear here."
          />,
        ),
      },
    ],
  },
]);

export function AppProviders() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
