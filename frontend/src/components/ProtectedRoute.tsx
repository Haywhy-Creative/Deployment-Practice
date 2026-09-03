import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

interface ProtectedRouteProps {
  redirectPath?: string;
}

// Helper to check if a JWT token is expired on the client side
const isTokenExpired = (token: string): boolean => {
  try {
    const payloadBase64 = token.split('.')[1];
    if (!payloadBase64) return true;
    const decodedPayload = JSON.parse(atob(payloadBase64));
    
    // exp is in seconds, Date.now() is in milliseconds
    if (decodedPayload.exp && decodedPayload.exp * 1000 < Date.now()) {
      return true;
    }
    return false;
  } catch (e) {
    return true; // Treat invalid tokens as expired/unauthenticated
  }
};

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  redirectPath = '/login',
}) => {
  const token = localStorage.getItem('accessToken');
  const location = useLocation();

  // 1️⃣ Verify token exists and is not expired locally
  if (!token || isTokenExpired(token)) {
    // Clear potentially expired tokens
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');

    // Redirect to login while saving the current location for post-login redirect
    return <Navigate to={redirectPath} state={{ from: location }} replace />;
  }

  // 2️⃣ Render child routes defined inside <Route element={<ProtectedRoute />}>
  return <Outlet />;
};

export default ProtectedRoute;