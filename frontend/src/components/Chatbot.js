import React, { useState } from 'react';
import axios from 'axios';
import '../App.css';

const API_URL = process.env.REACT_APP_API_URL || window.__API_URL__ || 'https://language-agnostic-chatbot-1.onrender.com'; // default to your render URL

const Chatbot = () => {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: "Hello! I'm here to help you with university circulars, notices, and information. What would you like to know?" }
  ]);
  const [input, setInput] = useState('');

  const handleSend = async () => {
    if (input.trim() === '') return;

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      const response = await axios.post(`${API_URL}/ask_bot`, { query: input });
      const botMessage = { sender: 'bot', text: response.data.response || 'No response from server.' };
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (error) {
      console.error('Error fetching bot response:', error);
      const errorMessage = { sender: 'bot', text: 'Sorry, I am unable to connect to the server.' };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
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
