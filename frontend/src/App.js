import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Chatbot from './components/Chatbot';
import Admin from './components/Admin';
import './App.css';

// Use basename provided at build time:
// For GitHub Pages subpath builds, set REACT_APP_BASENAME when building
const basename = process.env.REACT_APP_BASENAME || '/';

function App() {
  // If you want admin served from separate domain, set REACT_APP_ADMIN_URL at build time
  const adminUrl = process.env.REACT_APP_ADMIN_URL || null;

  return (
    <Router basename={basename}>
      <div className="app-container">
        <nav className="nav-bar">
          <Link to="/" className="nav-link">Chatbot</Link>
          {adminUrl ? (
            <a className="nav-link" href={adminUrl}>Admin</a>
          ) : (
            <Link to="/admin" className="nav-link">Admin</Link>
          )}
        </nav>
        <Routes>
          <Route path="/" element={<Chatbot />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
