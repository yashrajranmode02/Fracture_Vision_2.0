import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { chatWithAi } from '../api/client';

export default function ChatWindow({ sessionId, onClose }) {
    const [messages, setMessages] = useState([
        { role: 'assistant', text: 'Hello! I am your Clinical AI Assistant. I can answer questions about your fracture analysis or general forearm orthopedics. How can I help?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = input.trim();
        setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
        setInput('');
        setLoading(true);

        try {
            const res = await chatWithAi(userMsg, sessionId);
            setMessages(prev => [...prev, { role: 'assistant', text: res.data.answer }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', text: 'Error: Could not reach the clinical assistant. Please try again later.' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-window glass">
            <div className="chat-header">
                <h3>Clinical AI Assistant</h3>
                <button className="btn-close" onClick={onClose}>&times;</button>
            </div>

            <div className="chat-messages" ref={scrollRef}>
                {messages.map((m, i) => (
                    <div key={i} className={`message ${m.role}`}>
                        <div className="message-bubble">
                            <ReactMarkdown>{m.text}</ReactMarkdown>
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="message assistant">
                        <div className="message-bubble thinking">
                            Thinking...
                        </div>
                    </div>
                )}
            </div>

            <form className="chat-input" onSubmit={handleSend}>
                <input
                    type="text"
                    placeholder="Ask a question..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={loading}
                />
                <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
                    Send
                </button>
            </form>
        </div>
    );
}
