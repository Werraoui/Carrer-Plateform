import { api } from "./client";

export interface UserOut {
  id: number;
  name: string;
  email: string;
  level?: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type?: string;
  user: UserOut;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const { data } = await api.post<TokenResponse>("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function register(
  name: string,
  email: string,
  password: string,
  level?: string
): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/register", { name, email, password, level });
  return data;
}

export async function getMe(): Promise<UserOut> {
  const { data } = await api.get<UserOut>("/auth/me");
  return data;
}
