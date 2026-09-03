import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';

import Login from './Pages/Login';
import Register from './Pages/register';
import Dashboard from './Pages/Dashboard';
import VerifyOTP from './Pages/VerifyOTP';
import ForgotPassword from './Pages/ForgotPassword';

import ProtectedRoute from './components/ProtectedRoute';

// Header component to react to route changes and update token state dynamically
const NavigationBar: React.FC = () => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('accessToken'));
  const location = useLocation();

  // Re-check token status whenever location changes
  useEffect(() => {
    setToken(localStorage.getItem('accessToken'));
  }, [location]);

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('pendingVerificationEmail');
    window.location.href = '/login';
  };

  return (
    <header style={styles.navHeader}>
      <nav style={styles.navContainer}>
        <span style={styles.brand}>AuthApp</span>
        <div style={styles.linkGroup}>
          {token ? (
            <>
              <Link to="/dashboard" style={styles.link}>
                Dashboard
              </Link>
              <button onClick={handleLogout} style={styles.logoutBtn}>
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" style={styles.link}>
                Login
              </Link>
              <Link to="/register" style={styles.link}>
                Register
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
};

export const App: React.FC = () => {
  return (
    <Router>
      <NavigationBar />

      <main>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-otp" element={<VerifyOTP />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />

          {/* Protected Routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
          </Route>

          {/* Root & Catch-all Redirects */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </main>
    </Router>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  navHeader: {
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    padding: '0 24px',
  },
  navContainer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    maxWidth: '1200px',
    height: '60px',
    margin: '0 auto',
    fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
  },
  brand: {
    fontWeight: 'bold',
    fontSize: '18px',
    color: '#2d3748',
  },
  linkGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  link: {
    textDecoration: 'none',
    color: '#3182ce',
    fontWeight: 500,
    fontSize: '14px',
  },
  logoutBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#e53e3e',
    fontWeight: 500,
    fontSize: '14px',
    cursor: 'pointer',
    padding: 0,
  },
};

export default App;