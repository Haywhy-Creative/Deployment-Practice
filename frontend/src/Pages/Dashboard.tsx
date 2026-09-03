import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../api';
import { fetchWithAuth } from '../apiClient';

interface UserProfile {
  id: number;
  username: string;
  email: string;
}

interface DirectoryUser {
  id: number;
  username: string;
  email: string;
  is_verified: boolean;
}

interface PaginationMeta {
  current_page: number;
  total_pages: number;
  total_items: number;
  per_page: number;
  has_next: boolean;
  has_prev: boolean;
}

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  
  // Profile State
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loadingProfile, setLoadingProfile] = useState<boolean>(true);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Directory Table & Controls State
  const [directoryUsers, setDirectoryUsers] = useState<DirectoryUser[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(1);
  const [loadingDirectory, setLoadingDirectory] = useState<boolean>(false);

  // 1️⃣ Fetch Logged-In User Profile
  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        const response = await fetchWithAuth(`${API_BASE_URL}/api/auth/me`, {
          method: 'GET',
        });

        if (response.status === 403) {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          navigate('/verify-otp');
          return;
        }

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.message || 'Failed to fetch user details');
        }

        setUser(data.user);
      } catch (err: any) {
        setProfileError(err.message || 'An error occurred while fetching user data');
      } finally {
        setLoadingProfile(false);
      }
    };

    fetchUserProfile();
  }, [navigate]);

  // 2️⃣ Debounce Search Input (300ms delay)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1); // Reset to Page 1 on new search term
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  // 3️⃣ Fetch Directory Items (Pagination + Search + Filter)
  const fetchDirectory = useCallback(async () => {
    setLoadingDirectory(true);
    
    const queryParams = new URLSearchParams({
      page: page.toString(),
      per_page: '5',
      search: debouncedSearch,
      status: status
    });

    try {
      const response = await fetchWithAuth(
        `${API_BASE_URL}/api/dashboard/users?${queryParams.toString()}`,
        { method: 'GET' }
      );

      const data = await response.json();

      if (response.ok) {
        setDirectoryUsers(data.users);
        setPagination(data.pagination);
      }
    } catch (err: any) {
      console.error('Failed to load user directory:', err);
    } finally {
      setLoadingDirectory(false);
    }
  }, [page, debouncedSearch, status]);

  useEffect(() => {
    if (user) {
      fetchDirectory();
    }
  }, [fetchDirectory, user]);

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('pendingVerificationEmail');
    window.location.href = '/login';
  };

  if (loadingProfile) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <p style={styles.statusText}>Loading user profile...</p>
        </div>
      </div>
    );
  }

  if (profileError) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.errorMessage}>{profileError}</div>
          <button onClick={handleLogout} style={styles.button}>
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.dashboardWrapper}>
        
        {/* User Profile Header Card */}
        <div style={styles.card}>
          <div style={styles.header}>
            <h2 style={styles.title}>Welcome Back</h2>
            <span style={styles.badge}>Protected Session</span>
          </div>

          {user && (
            <div style={styles.profileContainer}>
              <div style={styles.infoRow}>
                <span style={styles.label}>User ID</span>
                <span style={styles.value}>#{user.id}</span>
              </div>

              <div style={styles.infoRow}>
                <span style={styles.label}>Username</span>
                <span style={styles.value}>{user.username}</span>
              </div>

              <div style={styles.infoRow}>
                <span style={styles.label}>Email Address</span>
                <span style={styles.value}>{user.email}</span>
              </div>

              <div style={{ ...styles.infoRow, borderBottom: 'none' }}>
                <span style={styles.label}>Status</span>
                <span style={styles.verifiedBadge}>✓ Verified Account</span>
              </div>
            </div>
          )}

          <button onClick={handleLogout} style={styles.logoutButton}>
            Log Out
          </button>
        </div>

        {/* Directory Card (Pagination, Search, Filter) */}
        <div style={styles.directoryCard}>
          <h3 style={styles.directoryTitle}>System User Directory</h3>

          {/* Controls Bar */}
          <div style={styles.controlsRow}>
            <input
              type="text"
              placeholder="Search username or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={styles.searchInput}
            />

            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1); // Reset to Page 1 when changing filter
              }}
              style={styles.selectInput}
            >
              <option value="all">All Accounts</option>
              <option value="verified">Verified Only</option>
              <option value="unverified">Unverified Only</option>
            </select>
          </div>

          {/* Directory Table */}
          {loadingDirectory ? (
            <p style={styles.statusText}>Updating directory records...</p>
          ) : (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr style={styles.tableHeaderRow}>
                    <th style={styles.th}>ID</th>
                    <th style={styles.th}>Username</th>
                    <th style={styles.th}>Email</th>
                    <th style={styles.th}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {directoryUsers.length > 0 ? (
                    directoryUsers.map((item) => (
                      <tr key={item.id} style={styles.tableRow}>
                        <td style={styles.td}>#{item.id}</td>
                        <td style={styles.td}>{item.username}</td>
                        <td style={styles.td}>{item.email}</td>
                        <td style={styles.td}>
                          <span style={item.is_verified ? styles.statusVerified : styles.statusPending}>
                            {item.is_verified ? 'Verified' : 'Pending'}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} style={{ ...styles.td, textAlign: 'center', color: '#718096' }}>
                        No user records match your criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {pagination && (
            <div style={styles.paginationRow}>
              <button
                onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
                disabled={!pagination.has_prev || loadingDirectory}
                style={{
                  ...styles.pageButton,
                  opacity: !pagination.has_prev || loadingDirectory ? 0.5 : 1,
                  cursor: !pagination.has_prev || loadingDirectory ? 'not-allowed' : 'pointer',
                }}
              >
                Previous
              </button>

              <span style={styles.paginationInfo}>
                Page <strong>{pagination.current_page}</strong> of <strong>{pagination.total_pages || 1}</strong>
                <span style={{ color: '#a0aec0', marginLeft: '6px' }}>
                  ({pagination.total_items} total)
                </span>
              </span>

              <button
                onClick={() => setPage((prev) => prev + 1)}
                disabled={!pagination.has_next || loadingDirectory}
                style={{
                  ...styles.pageButton,
                  opacity: !pagination.has_next || loadingDirectory ? 0.5 : 1,
                  cursor: !pagination.has_next || loadingDirectory ? 'not-allowed' : 'pointer',
                }}
              >
                Next
              </button>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
   justifyContent: 'center',
    minHeight: 'calc(100vh - 60px)',
    backgroundColor: '#f4f6f8',
    fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
    padding: '30px 20px',
  },
  dashboardWrapper: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '24px',
    width: '100%',
    maxWidth: '800px',
    margin: '0 auto',
  },
  card: {
    backgroundColor: '#ffffff',
    padding: '28px',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
    width: '100%',
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    color: '#1a1a1a',
    fontSize: '22px',
  },
  badge: {
    backgroundColor: '#e6fffa',
    color: '#234e52',
    fontSize: '12px',
    fontWeight: 600,
    padding: '4px 8px',
    borderRadius: '4px',
    border: '1px solid #b2f5ea',
  },
  profileContainer: {
    backgroundColor: '#f8fafc',
    borderRadius: '6px',
    padding: '16px',
    marginBottom: '20px',
    border: '1px solid #e2e8f0',
  },
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 0',
    borderBottom: '1px solid #edf2f7',
  },
  label: {
    fontSize: '14px',
    color: '#718096',
    fontWeight: 500,
  },
  value: {
    fontSize: '14px',
    color: '#2d3748',
    fontWeight: 600,
  },
  verifiedBadge: {
    fontSize: '13px',
    color: '#2f855a',
    backgroundColor: '#c6f6d5',
    padding: '2px 8px',
    borderRadius: '4px',
    fontWeight: 600,
  },
  directoryCard: {
    backgroundColor: '#ffffff',
    padding: '28px',
    borderRadius: '8px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
    width: '100%',
    boxSizing: 'border-box',
  },
  directoryTitle: {
    margin: '0 0 16px 0',
    fontSize: '18px',
    color: '#2d3748',
  },
  controlsRow: {
    display: 'flex',
    gap: '12px',
    marginBottom: '20px',
  },
  searchInput: {
    flex: 1,
    padding: '10px 14px',
    fontSize: '14px',
    border: '1px solid #cbd5e0',
    borderRadius: '6px',
    outline: 'none',
  },
  selectInput: {
    padding: '10px 14px',
    fontSize: '14px',
    border: '1px solid #cbd5e0',
    borderRadius: '6px',
    backgroundColor: '#ffffff',
    outline: 'none',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
  },
  tableHeaderRow: {
    backgroundColor: '#f7fafc',
    borderBottom: '2px solid #e2e8f0',
  },
  th: {
    padding: '12px',
    fontSize: '13px',
    fontWeight: 600,
    color: '#4a5568',
  },
  tableRow: {
    borderBottom: '1px solid #edf2f7',
  },
  td: {
    padding: '12px',
    fontSize: '14px',
    color: '#2d3748',
  },
  statusVerified: {
    fontSize: '12px',
    color: '#276749',
    backgroundColor: '#c6f6d5',
    padding: '2px 8px',
    borderRadius: '4px',
    fontWeight: 600,
  },
  statusPending: {
    fontSize: '12px',
    color: '#9c4221',
    backgroundColor: '#feebc8',
    padding: '2px 8px',
    borderRadius: '4px',
    fontWeight: 600,
  },
  paginationRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '20px',
    paddingTop: '16px',
    borderTop: '1px solid #edf2f7',
  },
  pageButton: {
    padding: '8px 16px',
    backgroundColor: '#3182ce',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
  },
  paginationInfo: {
    fontSize: '14px',
    color: '#4a5568',
  },
  statusText: {
    textAlign: 'center',
    color: '#4a5568',
    fontSize: '15px',
    margin: '16px 0',
  },
  errorMessage: {
    backgroundColor: '#fed7d7',
    color: '#c53030',
    padding: '12px',
    borderRadius: '6px',
    fontSize: '14px',
    marginBottom: '16px',
    textAlign: 'center',
  },
  button: {
    width: '100%',
    padding: '12px',
    backgroundColor: '#3182ce',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '15px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  logoutButton: {
    width: '100%',
    padding: '12px',
    backgroundColor: '#e53e3e',
    color: '#ffffff',
    border: 'none',
    borderRadius: '6px',
    fontSize: '15px',
    fontWeight: '600',
    cursor: 'pointer',
  },
};

export default Dashboard;