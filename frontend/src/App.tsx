import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionProvider } from "@/store/sessionStore";
import { AppShell } from "@/components/layout/AppShell";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 10_000 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionProvider>
        <AppShell />
      </SessionProvider>
    </QueryClientProvider>
  );
}
