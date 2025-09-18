import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Chatbot from './Chatbot';
import Admin from './Admin';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <nav className="nav-bar">
          <Link to="/" className="nav-link">Chatbot</Link>
          <Link to="/admin" className="nav-link">Admin</Link>
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
