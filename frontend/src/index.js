import React from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

const rootElement = document.getElementById("root");
const tree = (
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
if (rootElement?.dataset.hydrate === "home" && window.location.pathname === "/") {
  hydrateRoot(rootElement, tree);
} else {
  createRoot(rootElement).render(tree);
}
