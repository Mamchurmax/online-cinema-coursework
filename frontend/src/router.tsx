import { createBrowserRouter, Navigate } from "react-router";

import { Layout } from "./components/Layout";
import { AuthPage } from "./pages/AuthPage";
import { CatalogPage } from "./pages/CatalogPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { ErrorPage } from "./pages/ErrorPage";
import { FavoritesPage } from "./pages/FavoritesPage";
import { HistoryPage } from "./pages/HistoryPage";
import { PlansPage } from "./pages/PlansPage";
import { TitlePage } from "./pages/TitlePage";

// The admin panel is a separate chunk: regular viewers never download it.
const admin = (name: string) => async () => {
  const module = await import("./admin/routes");
  return { Component: module[name as keyof typeof module] };
};

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <CatalogPage /> },
      { path: "titles/:titleId", element: <TitlePage /> },
      {
        // The player (and hls.js, ~400 KB) is loaded only when someone starts watching.
        path: "watch/:titleId",
        lazy: async () => ({ Component: (await import("./pages/WatchPage")).WatchPage }),
      },
      { path: "history", element: <HistoryPage /> },
      { path: "favorites", element: <FavoritesPage /> },
      { path: "plans", element: <PlansPage /> },
      { path: "checkout", element: <CheckoutPage /> },
      {
        path: "admin",
        lazy: admin("AdminLayout"),
        children: [
          { index: true, element: <Navigate to="titles" replace /> },
          { path: "titles", lazy: admin("AdminTitlesPage") },
          { path: "titles/:titleId", lazy: admin("AdminTitleEditPage") },
          { path: "videos", lazy: admin("AdminVideosPage") },
          { path: "payments", lazy: admin("AdminPaymentsPage") },
          { path: "plans", lazy: admin("AdminPlansPage") },
          { path: "users", lazy: admin("AdminUsersPage") },
          { path: "ads", lazy: admin("AdminAdsPage") },
          { path: "reports", lazy: admin("AdminReportsPage") },
        ],
      },
      { path: "login", element: <AuthPage mode="login" /> },
      { path: "register", element: <AuthPage mode="register" /> },
    ],
  },
]);
