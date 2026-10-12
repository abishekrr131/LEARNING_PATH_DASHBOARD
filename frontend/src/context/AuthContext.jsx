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
      setAuthToken(data.access_token);
      localStorage.setItem("palp_refresh_token", data.refresh_token);
      const userProfile = await fetchProfile();
      return { success: true, profile: userProfile };
    } catch (err) {
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
