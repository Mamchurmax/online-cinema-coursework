import { createBrowserRouter } from "react-router";

import { Layout } from "./components/Layout";
import { AuthPage } from "./pages/AuthPage";
import { CatalogPage } from "./pages/CatalogPage";
import { ErrorPage } from "./pages/ErrorPage";
import { TitlePage } from "./pages/TitlePage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <CatalogPage /> },
      { path: "titles/:titleId", element: <TitlePage /> },
      { path: "login", element: <AuthPage mode="login" /> },
      { path: "register", element: <AuthPage mode="register" /> },
    ],
  },
]);
