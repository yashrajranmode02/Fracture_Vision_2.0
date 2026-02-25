import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHistory } from '../api/client';
import Navbar from '../components/Navbar';

function History() {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

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

            <main className="max-w-6xl mx-auto px-6 py-12">
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
                        <div className="text-6xl mb-6Opacity-20">📂</div>
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
                                className="glass group hover:bg-white/[0.04] transition-all cursor-pointer overflow-hidden border border-white/5"
                                onClick={() => navigate(`/report/${item.session_id}`)}
                            >
                                <div className="flex flex-col md:flex-row">
                                    <div className="w-full md:w-48 h-48 bg-black/50 overflow-hidden flex-shrink-0">
                                        {item.xray_url ? (
                                            <img src={item.xray_url} alt="X-ray preview" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-muted">No Image</div>
                                        )}
                                    </div>
                                    <div className="p-6 flex-grow">
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <div className="text-xs font-mono text-accent mb-1 tracking-widest uppercase">
                                                    {formatDate(item.created_at)}
                                                </div>
                                                <h3 className="text-xl font-bold text-white mb-1">
                                                    {item.report_name}
                                                </h3>
                                                <div className="text-xs text-muted font-mono">
                                                    ID: {item.session_id.slice(0, 8)}...
                                                </div>
                                            </div>
                                            <span className="badge badge-outline text-muted">GLB Model Saved</span>
                                        </div>

                                        <div className="bg-white/5 rounded-lg p-4 mb-4">
                                            <p className="text-sm italic text-muted line-clamp-2">
                                                "{item.summary}"
                                            </p>
                                        </div>

                                        <div className="flex justify-end">
                                            <button className="btn btn-sm btn-ghost text-accent group-hover:translate-x-1 transition-transform">
                                                View Full Report →
                                            </button>
                                        </div>
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
