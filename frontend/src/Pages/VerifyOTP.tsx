import React, { useState, useEffect, type ChangeEvent, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../api';

export const VerifyOTP: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState<string>('');
  const [otp, setOtp] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    // Retrieve email stored during registration or standard login attempt
    const savedEmail = localStorage.getItem('pendingVerificationEmail');
    if (savedEmail) {
      setEmail(savedEmail);
    }
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      // ✅ Using API_BASE_URL
      const response = await fetch(`${API_BASE_URL}/api/auth/verify-registration`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, otp }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Verification failed');
      }

      setSuccess('Account verified successfully! Redirecting to login...');
      localStorage.removeItem('pendingVerificationEmail');

      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Invalid verification code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <form onSubmit={handleSubmit} style={styles.card}>
        <h2 style={styles.title}>Verify Email</h2>
        <p style={styles.subtitle}>
          Enter the 6-digit code sent to <strong>{email || 'your email'}</strong>
        </p>

        {error && <div style={styles.errorMessage}>{error}</div>}
        {success && <div style={styles.successMessage}>{success}</div>}

        {!email && (
          <div style={styles.inputGroup}>
            <label style={styles.label}>Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={styles.input}
              placeholder="john@example.com"
            />
          </div>
        )}

        <div style={styles.inputGroup}>
          <label style={styles.label}>Verification Code (OTP)</label>
          <input
            type="text"
            value={otp}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setOtp(e.target.value)}
            required
            maxLength={6}
            style={{ ...styles.input, textAlign: 'center', letterSpacing: '4px', fontSize: '18px' }}
            placeholder="123456"
          />
        </div>

        <button type="submit" disabled={loading} style={styles.button}>
          {loading ? 'Verifying...' : 'Verify Email'}
        </button>
      </form>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
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
  title: { margin: '0 0 8px 0', textAlign: 'center', fontSize: '24px', color: '#1a1a1a' },
  subtitle: { margin: '0 0 20px 0', textAlign: 'center', fontSize: '14px', color: '#718096' },
  inputGroup: { marginBottom: '16px' },
  label: { display: 'block', marginBottom: '6px', fontSize: '14px', color: '#4a5568', fontWeight: 500 },
  input: { width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #cbd5e0', fontSize: '14px', boxSizing: 'border-box' },
  button: { width: '100%', padding: '12px', marginTop: '8px', backgroundColor: '#3182ce', color: '#ffffff', border: 'none', borderRadius: '6px', fontSize: '16px', fontWeight: '600', cursor: 'pointer' },
  errorMessage: { backgroundColor: '#fed7d7', color: '#c53030', padding: '10px', borderRadius: '6px', fontSize: '14px', marginBottom: '16px' },
  successMessage: { backgroundColor: '#c6f6d5', color: '#2f855a', padding: '10px', borderRadius: '6px', fontSize: '14px', marginBottom: '16px' },
};

export default VerifyOTP;