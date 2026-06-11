import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "react-hot-toast"

import { AppLayout } from "./components/layout/AppLayout"
import { AuthLayout } from "./components/layout/AuthLayout"
import { ErrorBoundary } from "./components/shared/ErrorBoundary"

import { LoginPage } from "./pages/LoginPage"
import { RegisterPage } from "./pages/RegisterPage"
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage"
import { ResetPasswordPage } from "./pages/ResetPasswordPage"
import { OnboardingPage } from "./pages/OnboardingPage"
import { FeedPage } from "./pages/FeedPage"
import { SavedListingsPage } from "./pages/SavedListingsPage"
import { ListingDetailPage } from "./pages/ListingDetailPage"
import { AgentPage } from "./pages/AgentPage"
import { ContractsPage } from "./pages/ContractsPage"
import { RoommatePage } from "./pages/RoommatePage"
import { LandlordDashboard } from "./pages/LandlordDashboard"
import { NotificationsPage } from "./pages/NotificationsPage"
import { ComparisonPage } from "./pages/ComparisonPage"
import { RelocationSimulatorPage } from "./pages/RelocationSimulatorPage"

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function Page({ children, title }: { children: React.ReactNode; title?: string }) {
  return <ErrorBoundary title={title}>{children}</ErrorBoundary>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<AuthLayout />}>
            <Route index element={<LoginPage />} />
          </Route>
          <Route path="/register" element={<AuthLayout />}>
            <Route index element={<RegisterPage />} />
          </Route>
          <Route path="/forgot-password" element={<AuthLayout />}>
            <Route index element={<ForgotPasswordPage />} />
          </Route>
          <Route path="/reset-password" element={<AuthLayout />}>
            <Route index element={<ResetPasswordPage />} />
          </Route>
          <Route element={<AppLayout />}>
            <Route path="/onboarding" element={<Page title="Could not load onboarding"><OnboardingPage /></Page>} />
            <Route path="/listings" element={<Page title="Could not load listings"><FeedPage /></Page>} />
            <Route path="/listings/:id" element={<Page title="Could not load listing"><ListingDetailPage /></Page>} />
            <Route path="/saved" element={<Page title="Could not load saved listings"><SavedListingsPage /></Page>} />
            <Route path="/agent" element={<Page title="Could not load AI chat"><AgentPage /></Page>} />
            <Route path="/contracts" element={<Page title="Could not load contracts"><ContractsPage /></Page>} />
            <Route path="/roommate" element={<Page title="Could not load roommate matches"><RoommatePage /></Page>} />
            <Route path="/dashboard" element={<Page title="Could not load dashboard"><LandlordDashboard /></Page>} />
            <Route path="/notifications" element={<Page title="Could not load notifications"><NotificationsPage /></Page>} />
            <Route path="/compare" element={<Page title="Could not load comparison"><ComparisonPage /></Page>} />
            <Route path="/simulator" element={<Page title="Could not load simulator"><RelocationSimulatorPage /></Page>} />
            <Route index element={<Navigate to="/listings" replace />} />
            <Route path="*" element={<Navigate to="/listings" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
