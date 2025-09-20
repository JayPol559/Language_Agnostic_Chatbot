import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Chatbot from './components/Chatbot';
import Admin from './components/Admin';
import './App.css';

// Optional basename for deployments under a subpath. Example: REACT_APP_BASENAME=/user-app
const basename = process.env.REACT_APP_BASENAME || '/';

function App() {
  // If you plan to host admin on a different domain, set REACT_APP_ADMIN_URL in frontend .env and use an <a> tag.
  const adminUrl = process.env.REACT_APP_ADMIN_URL || null;

  return (
    <Router basename={basename}>
      <div className="app-container">
        <nav className="nav-bar">
          <Link to="/" className="nav-link">Chatbot</Link>
          {adminUrl ? (
            // If adminUrl is provided, open admin in that domain
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
