import React, { useState } from 'react';
import './App.css';

function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email && password) {
      onLogin(true);
    } else {
      alert("Please enter both email and password");
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="brand-container">
          <svg className="brand-icon" xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <circle cx="12" cy="12" r="6"></circle>
            <circle cx="12" cy="12" r="2"></circle>
          </svg>
          <h1 className="brand-title">PathFinder</h1>
        </div>
        
        <p style={{ fontSize: '11px', color: '#94a3b8', fontWeight: '800', letterSpacing: '0.1em', marginBottom: '35px' }}>
          INTELLIGENT JOB RECOMMENDATION PORTAL
        </p>

        <form onSubmit={handleSubmit}>
          <div className="input-group" style={{ marginBottom: '25px', textAlign: 'left' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#64748b', textTransform: 'uppercase', marginBottom: '8px' }}>
              Email Address
            </label>
            <input 
              type="email" 
              placeholder="ENTER EMAIL" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              className="login-input"
            />
          </div>
          <div className="input-group" style={{ marginBottom: '35px', textAlign: 'left' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#64748b', textTransform: 'uppercase', marginBottom: '8px' }}>
              Password
            </label>
            <input 
              type="password" 
              placeholder="••••••••" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              className="login-input"
            />
          </div>
          <button type="submit" className="primary-btn">Sign In to Dashboard</button>
        </form>
      </div>
    </div>
  );
}

export default Login;