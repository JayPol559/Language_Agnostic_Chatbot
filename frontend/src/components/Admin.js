import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../App.css';

const API_URL = process.env.REACT_APP_API_URL || window.__API_URL__ || 'https://language-agnostic-chatbot-1.onrender.com';

const Admin = () => {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState('');
  const [uploadResults, setUploadResults] = useState([]);
  const [docs, setDocs] = useState([]);

  useEffect(() => {
    fetchDocs();
  }, []);

  const fetchDocs = async () => {
    try {
      const res = await axios.get(`${API_URL}/admin/docs`);
      setDocs(res.data.documents || []);
    } catch (err) {
      console.error('Failed to load docs', err);
    }
  };

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
    setMessage('');
    setUploadResults([]);
  };

  const handleUpload = async () => {
    if (!files || files.length === 0) {
      setMessage('Please select one or more PDF files.');
      return;
    }
    const formData = new FormData();
    files.forEach((f) => formData.append('file', f)); // append multiple files with same field name
    setMessage('Uploading...');
    try {
      const res = await axios.post(`${API_URL}/admin/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadResults(res.data.results || []);
      setMessage('Upload finished.');
      setFiles([]);
      fetchDocs();
    } catch (err) {
      console.error('Upload failed', err);
      setMessage('Upload failed. Check server logs.');
    }
  };

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1>Admin Panel</h1>
        <p>Upload one or more PDF documents to add to the knowledge base.</p>
      </div>
      <div className="admin-content">
        <input type="file" multiple accept=".pdf" onChange={handleFileChange} />
        <button onClick={handleUpload} disabled={!files.length} className="upload-btn">
          Upload
        </button>
        {message && <p className="status-message">{message}</p>}
        {uploadResults.length > 0 && (
          <div>
            <h3>Upload Results</h3>
            <ul>
              {uploadResults.map((r, idx) => (
                <li key={idx}>
                  {r.filename} — {r.processed ? 'Processed' : `Failed (${r.error || 'unknown'})`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div style={{ marginTop: 20 }}>
        <h2>Uploaded Documents</h2>
        <button onClick={fetchDocs}>Refresh list</button>
        <ul>
          {docs.map((d) => (
            <li key={d.id}>
              {d.title} — {d.status} — {new Date(d.created_at).toLocaleString()}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default Admin;
