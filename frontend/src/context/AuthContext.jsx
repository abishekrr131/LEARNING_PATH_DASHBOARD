import React, { createContext, useContext, useState, useEffect } from "react";
import { authApi, profileApi, setAuthToken, getAuthToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      const data = await profileApi.get();
      setProfile(data);
      setUser({
        id: data.user_id,
        email: data.email,
        name: data.name,
      });
      return data;
    } catch (err) {
      setUser(null);
      setProfile(null);
      setAuthToken(null);
      return null;
    }
  };

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      fetchProfile().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const loginWithGoogle = async (idToken) => {
    setLoading(true);
    try {
      const data = await authApi.loginWithGoogle(idToken);
      if (!data?.access_token) {
        throw new Error("No access token received from authentication server.");
      }
      setAuthToken(data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("palp_refresh_token", data.refresh_token);
      }

      // If user object returned by backend, populate session immediately
      if (data.user) {
        setUser({
          id: data.user.id,
          email: data.user.email,
          name: data.user.name,
          target_id: data.user.target_id,
          role: data.user.role,
        });
        setProfile(data.user);
        return { success: true, profile: data.user, user: data.user };
      }

      // Fallback: fetch profile from /me
      const userProfile = await fetchProfile();
      return { success: true, profile: userProfile };
    } catch (err) {
      setAuthToken(null);
      localStorage.removeItem("palp_refresh_token");
      setUser(null);
      setProfile(null);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setAuthToken(null);
    localStorage.removeItem("palp_refresh_token");
    setUser(null);
    setProfile(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        loading,
        isAuthenticated: !!user,
        loginWithGoogle,
        logout,
        refreshProfile: fetchProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
