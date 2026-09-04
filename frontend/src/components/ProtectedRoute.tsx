import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';

interface ProtectedRouteProps {
  redirectPath?: string;
  children?: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  redirectPath = '/login',
  children,
}) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // 1. Show loading screen while AuthContext initializes on app load/refresh
  if (isLoading) {
    return (
      <div style={styles.loadingContainer}>
        <p style={styles.loadingText}>Verifying session...</p>
      </div>
    );
  }

  // 2. Redirect unauthenticated users and preserve intended location
  if (!isAuthenticated) {
    return <Navigate to={redirectPath} state={{ from: location }} replace />;
  }

  // 3. Render children or nested routes via Outlet
  return children ? <>{children}</> : <Outlet />;
};

const styles: { [key: string]: React.CSSProperties } = {
  loadingContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f4f6f8',
  },
  loadingText: {
    fontSize: '16px',
    color: '#4a5568',
    fontWeight: 500,
  },
};

export default ProtectedRoute;