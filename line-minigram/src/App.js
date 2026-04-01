import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';

const liffId = process.env.REACT_APP_LIFF_ID || '';

function App() {
  const [liffInitialized, setLiffInitialized] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [profile, setProfile] = useState(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState({ type: '', text: '' });

  // LIFF 初期化
  useEffect(() => {
    const initializeLiff = async () => {
      try {
        await liff.init({ liffId });
        setLiffInitialized(true);
        
        // ログイン状態確認
        if (liff.isLoggedIn()) {
          const profile = await liff.getProfile();
          setProfile(profile);
          setIsLoggedIn(true);
          
          // 購読状態確認
          checkSubscription(profile.userId);
        } else {
          setLoading(false);
        }
      } catch (error) {
        console.error('LIFF initialization failed:', error);
        setMessage({ type: 'error', text: 'アプリの起動に失敗しました' });
        setLoading(false);
      }
    };

    initializeLiff();
  }, []);

  // 購読状態確認
  const checkSubscription = async (userId) => {
    try {
      const response = await fetch('/api/line/check-subscription', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId }),
      });
      const data = await response.json();
      setIsSubscribed(data.subscribed);
    } catch (error) {
      console.error('Failed to check subscription:', error);
    }
    setLoading(false);
  };

  // LINE ログイン
  const handleLogin = () => {
    liff.login({ redirectUri: window.location.href });
  };

  // ログアウト
  const handleLogout = () => {
    liff.logout();
    window.location.reload();
  };

  // 購読開始
  const handleSubscribe = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/line/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: profile.userId,
          displayName: profile.displayName,
        }),
      });
      const data = await response.json();
      
      if (data.success) {
        setIsSubscribed(true);
        setMessage({ type: 'success', text: '登録完了！毎朝 9 時にお届けします' });
      } else {
        setMessage({ type: 'error', text: data.error || '登録に失敗しました' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: '通信エラーが発生しました' });
    }
    setLoading(false);
  };

  // 購読解除
  const handleUnsubscribe = async () => {
    if (!window.confirm('配信を停止しますか？')) return;
    
    setLoading(true);
    try {
      const response = await fetch('/api/line/unsubscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: profile.userId }),
      });
      const data = await response.json();
      
      if (data.success) {
        setIsSubscribed(false);
        setMessage({ type: 'success', text: '配信を停止しました' });
      } else {
        setMessage({ type: 'error', text: data.error || '解除に失敗しました' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: '通信エラーが発生しました' });
    }
    setLoading(false);
  };

  // ローディング表示
  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>読み込み中...</div>
      </div>
    );
  }

  // ログイン前
  if (!isLoggedIn) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <h1 style={styles.title}>📰 PR Times 配信</h1>
          <p style={styles.subtitle}>最新のプレスリリースを毎日お届け</p>
        </div>
        
        <div style={styles.card}>
          <div style={styles.features}>
            <div style={styles.featureItem}>
              <span style={styles.icon}>✅</span>
              <span>完全無料</span>
            </div>
            <div style={styles.featureItem}>
              <span style={styles.icon}>⏰</span>
              <span>毎日朝 9 時配信</span>
            </div>
            <div style={styles.featureItem}>
              <span style={styles.icon}>🔕</span>
              <span>ワンクリック解約</span>
            </div>
          </div>
          
          <button style={styles.loginButton} onClick={handleLogin}>
            LINE ではじめる
          </button>
        </div>
        
        {message.text && (
          <div style={{...styles.message, ...(message.type === 'error' ? styles.messageError : {})}}>
            {message.text}
          </div>
        )}
      </div>
    );
  }

  // ログイン後
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.userInfo}>
          <img src={profile.pictureUrl} alt="Profile" style={styles.profileImage} />
          <span style={styles.userName}>{profile.displayName}</span>
        </div>
        <button style={styles.logoutButton} onClick={handleLogout}>
          ログアウト
        </button>
      </div>

      <div style={styles.card}>
        <h2 style={styles.cardTitle}>
          {isSubscribed ? '✅ 配信中' : '📬 配信登録'}
        </h2>
        
        <p style={styles.description}>
          {isSubscribed 
            ? '現在、毎朝 9 時にプレスリリースを配信しています。' 
            : 'メールアドレス不要！LINE でプレスリリースを受け取りましょう。'}
        </p>

        {!isSubscribed ? (
          <button 
            style={styles.subscribeButton} 
            onClick={handleSubscribe}
            disabled={loading}
          >
            {loading ? '処理中...' : '無料で登録する'}
          </button>
        ) : (
          <button 
            style={styles.unsubscribeButton} 
            onClick={handleUnsubscribe}
            disabled={loading}
          >
            {loading ? '処理中...' : '配信を停止する'}
          </button>
        )}

        {message.text && (
          <div style={{
            ...styles.message, 
            marginTop: 16,
            ...(message.type === 'error' ? styles.messageError : {})
          }}>
            {message.text}
          </div>
        )}
      </div>

      <div style={styles.footer}>
        <p style={styles.footerText}>
          © 2024 PyPer. All rights reserved.
        </p>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    padding: 20,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 24,
    margin: 0,
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    margin: '8px 0 0 0',
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  profileImage: {
    width: 40,
    height: 40,
    borderRadius: '50%',
  },
  userName: {
    fontSize: 16,
    color: '#333',
  },
  logoutButton: {
    padding: '8px 16px',
    backgroundColor: '#fff',
    border: '1px solid #ddd',
    borderRadius: 20,
    fontSize: 12,
    cursor: 'pointer',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  cardTitle: {
    fontSize: 20,
    margin: '0 0 16px 0',
    color: '#333',
  },
  description: {
    fontSize: 14,
    color: '#666',
    lineHeight: 1.6,
    marginBottom: 24,
  },
  features: {
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
  },
  featureItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 14,
    color: '#555',
    marginBottom: 8,
  },
  icon: {
    fontSize: 16,
  },
  loginButton: {
    width: '100%',
    padding: '16px',
    backgroundColor: '#00C300',
    color: '#fff',
    border: 'none',
    borderRadius: 12,
    fontSize: 16,
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  subscribeButton: {
    width: '100%',
    padding: '16px',
    backgroundColor: '#00C300',
    color: '#fff',
    border: 'none',
    borderRadius: 12,
    fontSize: 16,
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  unsubscribeButton: {
    width: '100%',
    padding: '16px',
    backgroundColor: '#ff4444',
    color: '#fff',
    border: 'none',
    borderRadius: 12,
    fontSize: 16,
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  message: {
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#d4edda',
    color: '#155724',
    fontSize: 14,
    textAlign: 'center',
  },
  messageError: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    fontSize: 16,
    color: '#666',
  },
  footer: {
    marginTop: 40,
    textAlign: 'center',
  },
  footerText: {
    fontSize: 12,
    color: '#999',
    margin: 0,
  },
};

export default App;
