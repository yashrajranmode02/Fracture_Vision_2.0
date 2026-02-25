import { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { getReport, getModelUrl } from '../api/client';
import Navbar from '../components/Navbar';
import ChatWindow from '../components/ChatWindow';

function RiskBar({ probability }) {
    const pct = Math.round(probability * 100);
    const color = pct >= 60 ? '#ef4444' : pct >= 40 ? '#f59e0b' : '#10b981';
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="risk-bar" style={{ width: 100 }}>
                <div className="risk-bar-fill" style={{ width: `${pct}%`, background: color }} />
            </div>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color }}>{pct}%</span>
        </div>
    );
}

function LocationTag({ location }) {
    const pct = Math.round(location * 100);
    const region = pct < 33 ? 'Proximal' : pct < 66 ? 'Mid-shaft' : 'Distal';
    return <span className="badge">{region} ({pct}%)</span>;
}

export default function Report() {
    const { sessionId: urlSessionId } = useParams();
    const { state } = useLocation();
    const navigate = useNavigate();
    const [report, setReport] = useState(null);
    const [err, setErr] = useState('');
    const [loading, setLoading] = useState(true);
    const [isChatOpen, setIsChatOpen] = useState(false);

    const sessionId = urlSessionId || state?.sessionId;

    if (!sessionId) {
        useEffect(() => { navigate('/upload'); }, []);
        return null;
    }
    const modelUrl = getModelUrl(sessionId);

    useEffect(() => {
        const poll = async () => {
            try {
                const { data } = await getReport(sessionId);
                setReport(data);
            } catch (e) {
                if (e.response?.status === 409) {
                    setTimeout(poll, 1500);
                } else {
                    setErr(e.response?.data?.detail || 'Failed to load report');
                }
            } finally { setLoading(false); }
        };
        poll();
    }, [sessionId]);

    if (loading) return (
        <>
            <Navbar />
            <div className="page-center">
                <div className="text-center">
                    <div className="spinner" style={{ width: 40, height: 40, margin: '0 auto 16px' }} />
                    <p className="text-secondary">Loading report…</p>
                </div>
            </div>
        </>
    );

    if (err) return (
        <>
            <Navbar />
            <div className="page-center">
                <div className="alert alert-error" style={{ maxWidth: 500 }}>{err}</div>
            </div>
        </>
    );

    const { fracture_data, risk_result } = report;

    return (
        <>
            <Navbar />
            <div style={{ paddingTop: 90, minHeight: '100vh', padding: '90px 24px 60px', maxWidth: 1000, margin: '0 auto' }}>
                <div className="flex justify-between items-center mb-8" style={{ flexWrap: 'wrap', gap: 12 }}>
                    <div>
                        <div className="badge mb-2">Step 4 of 4 — Complete</div>
                        <h1 style={{ fontSize: '2rem', fontWeight: 800 }}>{report.report_name}</h1>
                        <p className="text-secondary text-sm">Fracture Analysis Report</p>
                    </div>
                    <div className="flex gap-3">
                        <button className="btn btn-primary" onClick={() => setIsChatOpen(true)}>
                            💬 Ask AI Assistant
                        </button>
                        <Link to="/upload" className="btn btn-secondary">+ New Analysis</Link>
                    </div>
                </div>

                {/* 3D Viewer */}
                <div className="glass mb-6" style={{ padding: 28 }}>
                    <div className="flex justify-between items-center mb-4">
                        <h2 style={{ fontWeight: 700, fontSize: '1.1rem' }}>🦴 3D Fractured Bone Model</h2>
                        <a
                            href={report.model_url?.startsWith('http') ? report.model_url : `http://localhost:8000/api/model/download/${sessionId}`}
                            download
                            className="btn btn-sm btn-secondary"
                        >
                            📥 Download GLB
                        </a>
                    </div>
                    <div style={{ background: 'var(--bg-secondary)', borderRadius: 12, overflow: 'hidden', minHeight: 400 }}>
                        <model-viewer
                            src={report.model_url || modelUrl}
                            alt="Fractured forearm model"
                            auto-rotate
                            camera-controls
                            style={{ width: '100%', height: 420 }}
                            exposure="1"
                            shadow-intensity="1"
                        />
                    </div>
                    <p className="text-xs text-muted mt-3">Drag to rotate · Scroll to zoom · Double-click to reset</p>
                </div>

                {/* Fracture Data */}
                {fracture_data?.length > 0 && (
                    <div className="glass mb-6" style={{ padding: 28 }}>
                        <h2 style={{ fontWeight: 700, marginBottom: 16, fontSize: '1.1rem' }}>📊 Fracture Measurements</h2>
                        <div style={{ overflowX: 'auto' }}>
                            <table className="risk-table">
                                <thead>
                                    <tr>
                                        <th>Bone</th><th>Type</th><th>Location</th><th>Top Angle</th><th>Bottom Angle</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {fracture_data.map((f, i) => (
                                        <tr key={i}>
                                            <td style={{ fontWeight: 600, textTransform: 'capitalize' }}>{f.bone}</td>
                                            <td style={{ textTransform: 'capitalize' }}>{f.damage}</td>
                                            <td><LocationTag location={f.location} /></td>
                                            <td>{f.top_angle.toFixed(1)}°</td>
                                            <td>{f.bottom_angle.toFixed(1)}°</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Risk Analysis */}
                {risk_result ? (
                    risk_result.error ? (
                        <div className="alert alert-warning mb-6">
                            <strong>AI Risk Analysis Note:</strong> {risk_result.error}
                            <br /><small>Analysis results are currently unavailable for this session.</small>
                        </div>
                    ) : (
                        <>
                            <div className="glass mb-6" style={{ padding: 28 }}>
                                <h2 style={{ fontWeight: 700, marginBottom: 16, fontSize: '1.1rem' }}>⚠️ Neurovascular Risk Structures</h2>
                                <table className="risk-table">
                                    <thead>
                                        <tr><th>Structure</th><th>Risk Probability</th></tr>
                                    </thead>
                                    <tbody>
                                        {risk_result.damaged_structures.map((s, i) => (
                                            <tr key={i}>
                                                <td style={{ fontWeight: 500 }}>{s.name}</td>
                                                <td><RiskBar probability={s.probability} /></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            <div className="glass" style={{ padding: 28 }}>
                                <div className="flex justify-between items-start mb-4">
                                    <h2 style={{ fontWeight: 700, fontSize: '1.1rem' }}>🧠 Clinical Summary</h2>
                                    <button className="btn btn-sm btn-ghost text-accent" onClick={() => setIsChatOpen(true)}>
                                        Discuss with AI
                                    </button>
                                </div>
                                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8, fontSize: '0.95rem' }}>
                                    {risk_result.summary}
                                </p>
                            </div>
                        </>
                    )
                ) : (
                    <div className="alert alert-warning">
                        AI Risk analysis results are not yet available. Please ensure the pipeline completed successfully.
                    </div>
                )}
            </div>

            {isChatOpen && <ChatWindow sessionId={sessionId} onClose={() => setIsChatOpen(false)} />}
        </>
    );
}
