import React, { useState } from 'react';
import axios from 'axios';
import '../App.css';

const API_URL = process.env.REACT_APP_API_URL || window.__API_URL__ || 'https://language-agnostic-chatbot-1.onrender.com';
const LANG_OPTIONS = [
  { code: 'auto', label: 'Auto detect' },
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi' },
  { code: 'gu', label: 'Gujarati' },
  // add more as needed
];

const Chatbot = () => {
  const [messages, setMessages] = useState([{ sender: 'bot', text: "Hello! Ask about circulars, admissions, exams..." }]);
  const [input, setInput] = useState('');
  const [lang, setLang] = useState('auto');

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    try {
      const resp = await axios.post(`${API_URL}/ask_bot`, { query: input, language: lang });
      const botText = resp.data.response || 'No response from server.';
      const source = resp.data.source;
      let botMessageText = botText;
      if (source && source.title) {
        botMessageText += `\n\n(Source: ${source.title})`;
      }
      setMessages((prev) => [...prev, { sender: 'bot', text: botMessageText }]);
    } catch (err) {
      console.error('Error fetching bot response:', err);
      setMessages((prev) => [...prev, { sender: 'bot', text: 'Sorry, cannot connect to server.' }]);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">University Assistant</div>
      <div style={{ padding: '8px 12px' }}>
        <label>
          Language:
          <select value={lang} onChange={(e) => setLang(e.target.value)} style={{ marginLeft: 8 }}>
            {LANG_OPTIONS.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="chat-messages">
        {messages.map((m, idx) => (
          <div key={idx} className={`msg ${m.sender === 'user' ? 'user' : 'bot'}`}>
            <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
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
