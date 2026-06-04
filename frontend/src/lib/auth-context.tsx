import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import type { UserOut } from "./api/auth";

interface AuthState {
  user: UserOut | null;
  token: string | null;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  setAuth: (token: string, user: UserOut) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, token: null, isLoading: true });

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const userStr = localStorage.getItem("user");
    if (token && userStr) {
      try {
        setState({ user: JSON.parse(userStr), token, isLoading: false });
      } catch {
        setState({ user: null, token: null, isLoading: false });
      }
    } else {
      setState({ user: null, token: null, isLoading: false });
    }
  }, []);

  const setAuth = (token: string, user: UserOut) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", JSON.stringify(user));
    setState({ user, token, isLoading: false });
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setState({ user: null, token: null, isLoading: false });
  };

  return <AuthContext.Provider value={{ ...state, setAuth, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
