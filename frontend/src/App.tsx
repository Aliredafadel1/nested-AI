import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "react-hot-toast"

import { AppLayout } from "./components/layout/AppLayout"
import { AuthLayout } from "./components/layout/AuthLayout"

import { LoginPage } from "./pages/LoginPage"
import { RegisterPage } from "./pages/RegisterPage"
import { OnboardingPage } from "./pages/OnboardingPage"
import { FeedPage } from "./pages/FeedPage"
import { ListingDetailPage } from "./pages/ListingDetailPage"
import { AgentPage } from "./pages/AgentPage"
import { ContractsPage } from "./pages/ContractsPage"
import { RoommatePage } from "./pages/RoommatePage"
import { LandlordDashboard } from "./pages/LandlordDashboard"
import { NotificationsPage } from "./pages/NotificationsPage"
import { ErrorBoundary } from "./components/shared/ErrorBoundary"

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
      <BrowserRouter>
        <ErrorBoundary>
          <Routes>
            <Route path="/login" element={<AuthLayout />}>
              <Route index element={<LoginPage />} />
            </Route>
            <Route path="/register" element={<AuthLayout />}>
              <Route index element={<RegisterPage />} />
            </Route>
            <Route element={<AppLayout />}>
              <Route path="/onboarding" element={<OnboardingPage />} />
              <Route path="/listings" element={<FeedPage />} />
              <Route path="/listings/:id" element={<ListingDetailPage />} />
              <Route path="/agent" element={<AgentPage />} />
              <Route path="/contracts" element={<ContractsPage />} />
              <Route path="/roommate" element={<RoommatePage />} />
              <Route path="/dashboard" element={<LandlordDashboard />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route index element={<Navigate to="/listings" replace />} />
              <Route path="*" element={<Navigate to="/listings" replace />} />
            </Route>
          </Routes>
        </ErrorBoundary>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
