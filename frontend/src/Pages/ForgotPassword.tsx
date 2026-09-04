import React, { useState, useEffect, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../api';

export const ForgotPassword: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1); // 1 = Request Code, 2 = Enter Code & Reset Password
  const [email, setEmail] = useState<string>('');
  const [otp, setOtp] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // ⏱️ Countdown Timer State (10 minutes = 600 seconds)
  const [timeLeft, setTimeLeft] = useState<number>(600);
  const [canResend, setCanResend] = useState<boolean>(false);

  // Live Timer Countdown Effect
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (step === 2 && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      setCanResend(true);
    }
    return () => clearInterval(timer);
  }, [step, timeLeft]);

  // Helper to format seconds into MM:SS format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Step 1: Request or Resend Password Reset OTP
  const handleRequestOTP = async (e?: FormEvent<HTMLFormElement>) => {
    if (e) e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      // ✅ Using API_BASE_URL
      const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      // Handle non-JSON or HTML error responses from the server gracefully
      let data;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        throw new Error('Server error (500). Please check backend logs.');
      }

      if (!response.ok) {
        throw new Error(data.message || 'Failed to send request');
      }

      setSuccess('Verification code sent! Please check your email inbox.');
      setStep(2);

      // Reset timer back to 10 minutes on successful send/resend
      setTimeLeft(600);
      setCanResend(false);
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Confirm OTP & Set New Password
  const handleResetPassword = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (timeLeft === 0) {
      setError('The verification code has expired. Please click "Resend Code".');
      return;
    }

    setLoading(true);

    try {
      // ✅ Using API_BASE_URL
      const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp, new_password: newPassword }),
      });

      const data = await response.json();

      if (!response.ok) throw new Error(data.message || 'Password reset failed');

      setSuccess('Password reset successfully! Redirecting to login...');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err: any) {
      setError(err.message || 'Invalid code or details');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>{step === 1 ? 'Forgot Password' : 'Reset Password'}</h2>

        {error && <div style={styles.errorMessage}>{error}</div>}
        {success && <div style={styles.successMessage}>{success}</div>}

        {step === 1 ? (
          <form onSubmit={handleRequestOTP}>
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
            <button type="submit" disabled={loading} style={styles.button}>
              {loading ? 'Sending Code...' : 'Send Verification Code'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleResetPassword}>
            {/* ⏱️ COUNTDOWN TIMER & RESEND BANNER */}
            <div style={styles.timerContainer}>
              {timeLeft > 0 ? (
                <p style={styles.timerText}>
                  Code expires in: <span style={styles.timerCount}>{formatTime(timeLeft)}</span>
                </p>
              ) : (
                <p style={styles.expiredText}>Code has expired!</p>
              )}

              <button
                type="button"
                onClick={() => handleRequestOTP()}
                disabled={!canResend || loading}
                style={{
                  ...styles.resendBtn,
                  opacity: canResend && !loading ? 1 : 0.5,
                  cursor: canResend && !loading ? 'pointer' : 'not-allowed',
                }}
              >
                {loading ? 'Sending...' : 'Resend Code'}
              </button>
            </div>

            <div style={styles.inputGroup}>
              <label style={styles.label}>Verification Code (OTP)</label>
              <input
                type="text"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                required
                maxLength={6}
                style={{ ...styles.input, textAlign: 'center', letterSpacing: '4px' }}
                placeholder="123456"
              />
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.label}>New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                style={styles.input}
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={loading || timeLeft === 0}
              style={{
                ...styles.button,
                opacity: timeLeft === 0 ? 0.6 : 1,
                cursor: timeLeft === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Updating Password...' : 'Reset Password'}
            </button>
          </form>
        )}

        <p style={styles.footerText}>
          Remember your password?{' '}
          <Link to="/login" style={styles.link}>
            Back to Login
          </Link>
        </p>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: { display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: '#f4f6f8', fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif' },
  card: { backgroundColor: '#ffffff', padding: '32px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)', width: '100%', maxWidth: '400px' },
  title: { margin: '0 0 20px 0', textAlign: 'center', fontSize: '24px', color: '#1a1a1a' },
  inputGroup: { marginBottom: '16px' },
  label: { display: 'block', marginBottom: '6px', fontSize: '14px', color: '#4a5568', fontWeight: 500 },
  input: { width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #cbd5e0', fontSize: '14px', boxSizing: 'border-box' },
  button: { width: '100%', padding: '12px', marginTop: '8px', backgroundColor: '#3182ce', color: '#ffffff', border: 'none', borderRadius: '6px', fontSize: '16px', fontWeight: '600', cursor: 'pointer' },
  errorMessage: { backgroundColor: '#fed7d7', color: '#c53030', padding: '10px', borderRadius: '6px', fontSize: '14px', marginBottom: '16px' },
  successMessage: { backgroundColor: '#c6f6d5', color: '#2f855a', padding: '10px', borderRadius: '6px', fontSize: '14px', marginBottom: '16px' },
  footerText: { marginTop: '20px', textAlign: 'center', fontSize: '14px', color: '#718096' },
  link: { color: '#3182ce', textDecoration: 'none', fontWeight: 600 },
  timerContainer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', padding: '8px 12px', backgroundColor: '#edf2f7', borderRadius: '6px' },
  timerText: { margin: 0, fontSize: '13px', color: '#4a5568' },
  timerCount: { fontWeight: 'bold', color: '#e53e3e' },
  expiredText: { margin: 0, fontSize: '13px', color: '#e53e3e', fontWeight: 'bold' },
  resendBtn: { backgroundColor: 'transparent', border: 'none', color: '#3182ce', fontWeight: 600, fontSize: '13px', padding: 0 },
};

export default ForgotPassword;