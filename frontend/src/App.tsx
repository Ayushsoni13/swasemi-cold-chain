import React, { useState, useEffect } from 'react';
import type { User } from './types';
import { getMeApi } from './services/api';
import { Login } from './components/Login';
import { Dashboard } from './components/Dashboard';

export const App: React.FC = () => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('swasemi_token'));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Validate Token on App load
  useEffect(() => {
    async function initAuth() {
      if (token) {
        try {
          const userData = await getMeApi(token);
          setUser(userData);
        } catch (err) {
          console.warn('Stored JWT invalid or expired. Logging out.', err);
          localStorage.removeItem('swasemi_token');
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    }
    initAuth();
  }, [token]);

  const handleLoginSuccess = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
  };

  const handleLogout = () => {
    localStorage.removeItem('swasemi_token');
    setToken(null);
    setUser(null);
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0b0f19', color: '#94a3b8', fontFamily: 'var(--font-sans)' }}>
        Loading SWASEMI Cold-Chain Platform...
      </div>
    );
  }

  if (!token || !user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return <Dashboard user={user} token={token} onLogout={handleLogout} />;
};

export default App;
