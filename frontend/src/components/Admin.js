import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL;

const Admin = () => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setMessage('');
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/admin/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setMessage(response.data.message);
      setFile(null); // Reset file input
    } catch (error) {
      console.error('File upload failed:', error);
      setMessage('File upload failed. Please try again.');
    }
  };

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1>Admin Panel</h1>
        <p>Upload a PDF document to add to the knowledge base.</p>
      </div>
      <div className="admin-content">
        <input type="file" onChange={handleFileChange} accept=".pdf" />
        <button onClick={handleUpload} disabled={!file} className="upload-btn">
          Upload
        </button>
        {message && <p className="status-message">{message}</p>}
      </div>
    </div>
  );
};

export default Admin;
