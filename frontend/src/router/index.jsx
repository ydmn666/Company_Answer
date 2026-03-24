import { Navigate, Outlet, useLocation, useRoutes } from "react-router-dom";
import { WorkspaceLayout } from "../layouts/WorkspaceLayout";
import { HomeLandingPage } from "../pages/HomeLandingPage";
import { LoginPage } from "../pages/LoginPage";
import { ChatPage } from "../pages/ChatPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import { UploadPage } from "../pages/UploadPage";
import { useAuthStore } from "../store/auth";


function AuthGuard() {
  // 没登录时一律先回登录页。
  const token = useAuthStore((state) => state.token);
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}


function AdminGuard() {
  // 非管理员不能进入文档管理和上传页。
  const user = useAuthStore((state) => state.user);

  if (user?.role !== "admin") {
    return <Navigate to="/chat" replace />;
  }

  return <Outlet />;
}


function HomeRedirect() {
  // 登录后的默认落点按角色区分。
  const user = useAuthStore((state) => state.user);
  return <Navigate to={user?.role === "admin" ? "/documents" : "/chat"} replace />;
}


export function AppRouter() {
  // /welcome 是引导页，/login 是登录页，其余是登录后的业务页。
  return useRoutes([
    { path: "/", element: <Navigate to="/welcome" replace /> },
    { path: "/welcome", element: <HomeLandingPage /> },
    { path: "/login", element: <LoginPage /> },
    {
      element: <AuthGuard />,
      children: [
        {
          element: <WorkspaceLayout />,
          children: [
            { index: true, element: <HomeRedirect /> },
            { path: "/chat", element: <ChatPage /> },
            { path: "/documents", element: <DocumentsPage /> },
            {
              element: <AdminGuard />,
              children: [{ path: "/documents/upload", element: <UploadPage /> }],
            },
          ],
        },
      ],
    },
    { path: "*", element: <Navigate to="/welcome" replace /> },
  ]);
}
