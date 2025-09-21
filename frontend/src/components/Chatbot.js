import React, { useState } from 'react';
import axios from 'axios';
import '../App.css';

// Prefer build-time env REACT_APP_API_URL; if not available, use runtime window.__API_URL__;
// As a final fallback we keep your Render URL.
const API_URL = process.env.REACT_APP_API_URL || window.__API_URL__ || 'https://language-agnostic-chatbot-1.onrender.com';

const Chatbot = () => {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: "Hello! I'm here to help. Ask about circulars, admissions, exams..." }
  ]);
  const [input, setInput] = useState('');

  const handleSend = async () => {
    if (input.trim() === '') return;

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      const resp = await axios.post(`${API_URL}/ask_bot`, { query: input });
      const botMessage = { sender: 'bot', text: resp?.data?.response || 'No response from server.' };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error('Error fetching bot response:', err);
      const errorMessage = { sender: 'bot', text: 'Sorry, I am unable to connect to the server.' };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">University Assistant</div>
      <div className="chat-messages">
        {messages.map((m, idx) => (
          <div key={idx} className={`msg ${m.sender === 'user' ? 'user' : 'bot'}`}>
            <div>{m.text}</div>
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question..." />
        <button onClick={handleSend} className="chat-send-btn">Send</button>
      </div>
    </div>
  );
};

export default Chatbot;
