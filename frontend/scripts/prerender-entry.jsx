import { StrictMode } from "react";
import { renderToString } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StaticRouter } from "react-router";
import { AppContent } from "../src/App";
import { AppErrorBoundary } from "../src/components/AppErrorBoundary";

export function renderHome() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } },
  });
  return renderToString(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <AppErrorBoundary>
          <StaticRouter location="/">
            <AppContent />
          </StaticRouter>
        </AppErrorBoundary>
      </QueryClientProvider>
    </StrictMode>,
  );
}
