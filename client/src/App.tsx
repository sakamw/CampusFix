import { Suspense } from "react";
import PublicIssues from "./pages/PublicIssues";
import { Toaster } from "./components/ui/toaster";
import { Toaster as Sonner } from "./components/ui/sonner";
import { TooltipProvider } from "./components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import { ThemeProvider } from "./contexts/ThemeContext";
import { UserSettingsProvider } from "./contexts/UserSettingsContext";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Login from "./pages/Login";
import ForgotPassword from "./pages/ForgotPassword";
import Dashboard from "./pages/Dashboard";
import MyIssues from "./pages/MyIssues";
import ReportIssue from "./pages/ReportIssue";
import IssueDetails from "./pages/IssueDetails";
import EditIssue from "./pages/EditIssue";
import Settings from "./pages/Settings";

import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <AuthProvider>
        <UserSettingsProvider>
          <ThemeProvider>
            <TooltipProvider>
              <Toaster />
              <Sonner />
              <Routes>
                <Route path="/" element={<Navigate to="/login" replace />} />
                <Route path="/login" element={<Login />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />

                {/* Student Routes */}
                <Route element={<DashboardLayout />}>
                  <Route
                    path="/dashboard"
                    element={
                      <ProtectedRoute>
                        <Dashboard />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/report"
                    element={
                      <ProtectedRoute>
                        <ReportIssue />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/issues"
                    element={
                      <ProtectedRoute>
                        <MyIssues />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/issues/:id"
                    element={
                      <ProtectedRoute>
                        <IssueDetails />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/issues/:id/edit"
                    element={
                      <ProtectedRoute>
                        <Suspense fallback={<div>Loading...</div>}>
                          <EditIssue />
                        </Suspense>
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/settings"
                    element={
                      <ProtectedRoute>
                        <Settings />
                      </ProtectedRoute>
                    }
                  />
                </Route>

                {/* Public Issues Route - must be above the catch-all */}
                <Route element={<DashboardLayout />}>
                  <Route
                    path="/public-issues"
                    element={
                      <ProtectedRoute>
                        <PublicIssues />
                      </ProtectedRoute>
                    }
                  />
                </Route>

                {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                <Route path="*" element={<NotFound />} />
              </Routes>
            </TooltipProvider>
          </ThemeProvider>
        </UserSettingsProvider>
      </AuthProvider>
    </BrowserRouter>
  </QueryClientProvider>
);

export default App;
