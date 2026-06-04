import { createFileRoute, Navigate } from "@tanstack/react-router";
export const Route = createFileRoute("/register")({ component: () => <Navigate to="/login" /> });
