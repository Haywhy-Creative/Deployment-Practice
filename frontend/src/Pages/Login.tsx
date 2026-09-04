import React, { useState, type ChangeEvent, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../api'; // ✅ Steps up out of pages/ into src/ to find api.ts

interface LoginFormData {
  email: string;
  password: string;
}

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<LoginFormData>({
    email: '',
    password: '',
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { email, password } = formData;

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      // 1️⃣ Catch 403 status (Unverified Account) and redirect to OTP screen
      if (res.status === 403) {
        localStorage.setItem('pendingVerificationEmail', email);
        navigate('/verify-otp');
        return;
      }

      if (!res.ok) {
        throw new Error(data.message || 'Invalid email or password');
      }

      const accessToken = data.access_token || data.token;
      const refreshToken = data.refresh_token;

      if (accessToken) {
        localStorage.setItem('accessToken', accessToken);
      }
      if (refreshToken) {
        localStorage.setItem('refreshToken', refreshToken);
      }

      window.location.href = '/dashboard';
    } catch (err: any) {
      setError(err.message || 'Something went wrong during login');
    } finally {
      setLoading(false);
    }
  };

  
  return (
    <div style={styles.container}>
      <form onSubmit={handleSubmit} style={styles.card}>
        <h2 style={styles.title}>Welcome Back</h2>

        {error && <div style={styles.errorMessage}>{error}</div>}

        <div style={styles.inputGroup}>
          <label style={styles.label}>Email Address</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            autoComplete="email"
            required
            style={styles.input}
            placeholder="john@example.com"
          />
        </div>

        <div style={styles.inputGroup}>
          <div style={styles.labelRow}>
            <label style={styles.label}>Password</label>
            {/* 2️⃣ Added Forgot Password Link */}
            <Link to="/forgot-password" style={styles.forgotLink}>
              Forgot?
            </Link>
          </div>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            autoComplete="current-password"
            required
            style={styles.input}
            placeholder="••••••••"
          />
        </div>

        <button type="submit" disabled={loading} style={styles.button}>
          {loading ? 'Authenticating...' : 'Sign In'}
        </button>

        <p style={styles.footerText}>
          Don't have an account?{' '}
          <Link to="/register" style={styles.link}>
            Register
          </Link>
        </p>
      </form>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: 'calc(100vh - 60px)',
    backgroundColor: '#f4f6f8',
    fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
  },
  card: {
    backgroundColor: '#ffffff',
    padding: '32px',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
    width: '100%',
    maxWidth: '400px',
  },
  title: {
    margin: '0 0 24px 0',
    color: '#1a1a1a',
    textAlign: 'center',
    fontSize: '24px',
  },
  inputGroup: {
    marginBottom: '16px',
  },
  labelRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    color: '#4a5568',
    fontWeight: 500,
  },
  forgotLink: {
    fontSize: '12px',
    color: '#3182ce',
    textDecoration: 'none',
    fontWeight: 500,
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #cbd5e0',
    fontSize: '14px',
    boxSizing: 'border-box',
    outline: 'none',
  },
  button: {
    width: '100%',
    padding: '12px',
    marginTop: '8px',
    backgroundColor: '#3182ce',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  errorMessage: {
    backgroundColor: '#fed7d7',
    color: '#c53030',
    padding: '10px',
    borderRadius: '6px',
    fontSize: '14px',
    marginBottom: '16px',
  },
  footerText: {
    marginTop: '20px',
    textAlign: 'center',
    fontSize: '14px',
    color: '#718096',
  },
  link: {
    color: '#3182ce',
    textDecoration: 'none',
    fontWeight: 600,
  },
};

export default Login;