"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

/**
 * Global session manager that enforces authentication.
 * Redirects unauthenticated users to /auth if they try to access protected routes.
 */
export function SessionManager() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    const isAuthPage = pathname === "/auth";
    const isPublicPage = pathname === "/"; // Add other public routes if needed

    if (!token && !isAuthPage && !isPublicPage) {
      console.log("No session found. Redirecting to login...");
      router.push("/auth");
    }

    // If logged in and on auth page, redirect to home
    if (token && isAuthPage) {
      router.push("/");
    }
  }, [pathname, router]);

  return null; // This component doesn't render anything
}
