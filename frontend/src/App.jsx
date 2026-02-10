import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, Send, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

function App() {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState(null); // 'success', 'error'
    const [uploadMessage, setUploadMessage] = useState('');
    const [stats, setStats] = useState(null);

    const [question, setQuestion] = useState('');
    const [chatHistory, setChatHistory] = useState([]);
    const [querying, setQuerying] = useState(false);

    const chatEndRef = useRef(null);

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [chatHistory]);

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setUploadStatus(null);
            setUploadMessage('');
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);
        setUploadStatus(null);
        setUploadMessage('Processing PDF... this may take a moment.');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload-pdf', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Upload failed');
            }

            const data = await response.json();
            setStats(data);
            setUploadStatus('success');
            setUploadMessage(`Successfully processed ${data.filename} (${data.num_chunks} chunks).`);
            setFile(null); // Clear file input after success
        } catch (error) {
            console.error('Upload Error:', error);
            setUploadStatus('error');
            setUploadMessage(error.message);
        } finally {
            setUploading(false);
        }
    };

    const handleQuery = async (e) => {
        e.preventDefault();
        if (!question.trim() || querying) return;

        const userQuestion = question;
        setQuestion('');
        setQuerying(true);

        // Add user message immediately
        setChatHistory(prev => [...prev, { role: 'user', content: userQuestion }]);

        try {
            const response = await fetch(`/api/query?question=${encodeURIComponent(userQuestion)}`, {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error('Query failed');
            }

            const data = await response.json();

            setChatHistory(prev => [...prev, {
                role: 'assistant',
                content: data.answer,
                sources: data.sources
            }]);

        } catch (error) {
            setChatHistory(prev => [...prev, {
                role: 'assistant',
                content: "Sorry, I encountered an error answering your question. Please try again."
            }]);
        } finally {
            setQuerying(false);
        }
    };

    return (
        <div className="container">
            <header className="header">
                <h1>Enterprise RAG System</h1>
                <p>Production-Grade Document Intelligence</p>
            </header>

            <div className="layout">
                <aside className="card upload-section">
                    <h2>Document Ingestion</h2>
                    <div className={`dropzone ${file ? 'active' : ''}`}>
                        <FileText size={48} color={file ? '#2563eb' : '#94a3b8'} />
                        <div>
                            {file ? (
                                <p><strong>{file.name}</strong></p>
                            ) : (
                                <p>Select a PDF document</p>
                            )}
                        </div>
                        <input
                            type="file"
                            accept=".pdf"
                            onChange={handleFileChange}
                            style={{ display: 'none' }}
                            id="file-upload"
                        />
                        <label htmlFor="file-upload" className="btn" style={{ display: 'inline-block', width: 'auto', marginBottom: '0' }}>
                            Browse Files
                        </label>
                    </div>

                    {file && (
                        <button
                            className="btn"
                            onClick={handleUpload}
                            disabled={uploading}
                            style={{ marginTop: '1rem' }}
                        >
                            {uploading ? (
                                <span className="loading-dots">Processing<span className="dot"></span><span className="dot"></span></span>
                            ) : (
                                <>
                                    <Upload size={18} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
                                    Upload & Process
                                </>
                            )}
                        </button>
                    )}

                    {uploadStatus && (
                        <div style={{
                            marginTop: '1rem',
                            padding: '1rem',
                            borderRadius: '0.5rem',
                            backgroundColor: uploadStatus === 'success' ? '#dcfce7' : '#fee2e2',
                            color: uploadStatus === 'success' ? '#166534' : '#991b1b',
                            display: 'flex',
                            alignItems: 'start',
                            gap: '0.5rem'
                        }}>
                            {uploadStatus === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                            <div>
                                <strong>{uploadStatus === 'success' ? 'Success' : 'Error'}</strong>
                                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.9rem' }}>{uploadMessage}</p>
                            </div>
                        </div>
                    )}

                    {stats && (
                        <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid #e2e8f0', fontSize: '0.9rem', color: '#64748b' }}>
                            <p>Last processed: <strong>{stats.filename}</strong></p>
                            <p>Chunks generated: <strong>{stats.num_chunks}</strong></p>
                        </div>
                    )}
                </aside>

                <main className="card chat-section">
                    <h2>Knowledge Base Chat</h2>

                    <div className="chat-messages">
                        {chatHistory.length === 0 ? (
                            <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '2rem' }}>
                                <AlertCircle size={48} style={{ margin: '0 auto 1rem auto', display: 'block', opacity: 0.5 }} />
                                <p>Upload a document to start chatting.</p>
                            </div>
                        ) : (
                            chatHistory.map((msg, idx) => (
                                <div key={idx} className={`message ${msg.role}`}>
                                    <div className="message-content">{msg.content}</div>
                                    {msg.sources && msg.sources.length > 0 && (
                                        <div className="sources">
                                            <strong>Sources:</strong>
                                            {msg.sources.map((src, i) => (
                                                <div key={i} style={{ marginTop: '0.25rem', fontStyle: 'italic' }}>
                                                    "{src.substring(0, 150)}..."
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    <form onSubmit={handleQuery} className="input-area">
                        <input
                            type="text"
                            className="input-field"
                            placeholder="Ask a question about your documents..."
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            disabled={querying}
                        />
                        <button type="submit" className="btn" style={{ width: 'auto' }} disabled={querying || !question.trim()}>
                            {querying ? <Loader2 className="spin" size={20} /> : <Send size={20} />}
                        </button>
                    </form>
                </main>
            </div>
        </div>
    );
}

export default App;
