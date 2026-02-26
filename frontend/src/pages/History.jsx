import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { getHistory } from '../api/client';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';

function History() {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();
    const { user } = useAuth();

    const handleDelete = async (e, sessionId) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this clinical report? This action cannot be undone.")) return;

        try {
            await api.delete(`/api/history/${sessionId}`);
            setHistory(prev => prev.filter(item => item.session_id !== sessionId));
        } catch (err) {
            console.error("Delete error:", err);
            alert("Failed to delete report.");
        }
    };

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const res = await getHistory();
                setHistory(res.data);
            } catch (err) {
                console.error('History fetch error:', err);
                setError('Failed to load history. Please ensure you are logged in.');
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, []);

    const formatDate = (isoStr) => {
        const d = new Date(isoStr);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div className="min-h-screen bg-main">
            <Navbar />

            <main className="max-w-6xl mx-auto px-6 py-12" style={{ paddingTop: 100 }}>
                <header className="mb-12">
                    <h1 className="text-4xl font-extrabold mb-2 tracking-tight">📜 Report History</h1>
                    <p className="text-muted text-lg">Your past persistent fracture analyses and AI consults.</p>
                </header>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 glass">
                        <div className="loading loading-spinner loading-lg text-accent mb-4"></div>
                        <p className="text-muted">Retrieving your clinical archive...</p>
                    </div>
                ) : error ? (
                    <div className="alert alert-error glass border-red-500/30">
                        <span>{error}</span>
                    </div>
                ) : history.length === 0 ? (
                    <div className="glass p-12 text-center">
                        <div className="text-6xl mb-6 opacity-20">📂</div>
                        <h2 className="text-xl font-bold mb-2">No Reports Found</h2>
                        <p className="text-muted mb-8">You haven't completed any analyses yet.</p>
                        <button className="btn btn-primary" onClick={() => navigate('/upload')}>
                            Start First Analysis
                        </button>
                    </div>
                ) : (
                    <div className="grid gap-6">
                        {history.map((item) => (
                            <div
                                key={item.session_id}
                                className="glass group hover:bg-white/[0.05] transition-all duration-500 cursor-pointer border border-white/5 mb-6 relative overflow-hidden"
                                onClick={() => navigate(`/report/${item.session_id}`)}
                                style={{
                                    borderRadius: '28px',
                                    boxShadow: '0 10px 40px -10px rgba(0,0,0,0.4)',
                                    background: 'rgba(255, 255, 255, 0.02)',
                                    paddingLeft: '8px'
                                }}
                            >
                                {/* Subtle Interior Glow */}
                                <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-accent/40 to-accent2/40 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                                <div className="flex items-center p-6 gap-8">
                                    {/* Thumbnail - Inset, Spaced, and Perfectly Styled */}
                                    <div
                                        className="w-24 h-24 flex-shrink-0 relative border border-white/10 group-hover:border-accent/30 transition-all duration-700 shadow-[0_8px_30px_rgb(0,0,0,0.5)]"
                                        style={{
                                            borderRadius: '22px',
                                            overflow: 'hidden',
                                            backgroundColor: '#000',
                                            padding: '2px' // Creates a tiny subtle border gap
                                        }}
                                    >
                                        <div className="w-full h-full overflow-hidden" style={{ borderRadius: '20px' }}>
                                            {item.xray_url ? (
                                                <img
                                                    src={item.xray_url}
                                                    alt="X-ray preview"
                                                    className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-110"
                                                />
                                            ) : (
                                                <div className="w-full h-full flex flex-col items-center justify-center bg-white/5 text-muted">
                                                    <span className="text-xl opacity-30">📂</span>
                                                </div>
                                            )}
                                        </div>
                                        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent pointer-events-none" />
                                    </div>

                                    {/* Content - Sophisticated Typography & Layout */}
                                    <div className="flex-grow min-w-0">
                                        <div className="flex justify-between items-center mb-2">
                                            <div className="flex items-center gap-3">
                                                <h3 className="text-xl font-extrabold text-white tracking-tight truncate group-hover:text-accent transition-colors duration-300">
                                                    {item.report_name || "Untitled Case"}
                                                </h3>
                                                <span className="hidden sm:inline-block px-2 py-0.5 rounded-md bg-white/5 text-[9px] text-muted font-bold uppercase tracking-widest border border-white/5">
                                                    Verified
                                                </span>
                                            </div>
                                            <div className="text-[10px] font-black text-accent/80 tracking-widest uppercase bg-accent/5 px-3 py-1.5 rounded-xl border border-accent/10">
                                                {formatDate(item.created_at)}
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-4 mb-3">
                                            <div className="flex items-center gap-1.5">
                                                <span className="w-1.5 h-1.5 rounded-full bg-success" />
                                                <span className="text-[11px] font-mono text-success/80 font-bold">L-DRMP Persisted</span>
                                            </div>
                                            <div className="w-px h-3 bg-white/10" />
                                            <div className="text-[11px] text-white/30 font-mono">
                                                Ref: {item.session_id.slice(0, 8).toUpperCase()}
                                            </div>
                                        </div>

                                        <p className="text-[0.9rem] text-white/40 line-clamp-1 italic font-medium tracking-wide">
                                            {item.summary && item.summary !== "No summary available"
                                                ? item.summary
                                                : "Diagnostic engine has successfully finalized the fracture reconstruction and clinical summary."}
                                        </p>
                                    </div>

                                    {/* Action - Arrow & Delete */}
                                    <div className="flex flex-col gap-2 items-center justify-center">
                                        <div className="hidden lg:flex items-center justify-center w-10 h-10 rounded-2xl bg-white/5 group-hover:bg-accent/20 border border-white/5 group-hover:border-accent/40 transition-all duration-500">
                                            <span className="text-accent text-lg group-hover:translate-x-0.5 transition-transform duration-300">→</span>
                                        </div>
                                        <button
                                            onClick={(e) => handleDelete(e, item.session_id)}
                                            className="w-10 h-10 rounded-2xl flex items-center justify-center bg-white/5 hover:bg-danger/20 border border-white/5 hover:border-danger/40 transition-all opacity-0 group-hover:opacity-100"
                                            title="Delete Report"
                                        >
                                            <span className="text-danger-400 text-sm">🗑️</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}

export default History;
