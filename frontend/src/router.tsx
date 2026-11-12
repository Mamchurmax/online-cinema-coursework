import { createBrowserRouter } from "react-router";

import { Layout } from "./components/Layout";
import { AuthPage } from "./pages/AuthPage";
import { CatalogPage } from "./pages/CatalogPage";
import { ErrorPage } from "./pages/ErrorPage";
import { HistoryPage } from "./pages/HistoryPage";
import { TitlePage } from "./pages/TitlePage";

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
      { path: "login", element: <AuthPage mode="login" /> },
      { path: "register", element: <AuthPage mode="register" /> },
    ],
  },
]);
