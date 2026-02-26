import { useRef, useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { submitLandmarks } from '../api/client';
import Navbar from '../components/Navbar';

const LABELS = ['ulna head', 'ulna tail', 'radius head', 'radius tail'];
const COLORS = ['#00d4ff', '#7c3aed', '#10b981', '#f59e0b'];
const INSTRUCTIONS = [
    'Click to mark: Ulna Head',
    'Click to mark: Ulna Tail',
    'Click to mark: Radius Head',
    'Click to mark: Radius Tail',
];

export default function Landmarks() {
    const { state } = useLocation();
    const navigate = useNavigate();
    const canvasRef = useRef(null);
    const imgRef = useRef(null);
    const [dots, setDots] = useState([]);
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState('');
    const [imgReady, setImgReady] = useState(false);

    if (!state?.sessionId) {
        navigate('/upload');
        return null;
    }

    const { sessionId, imageB64, width, height } = state;
    const scale = Math.min(1, 700 / width);
    const dw = Math.round(width * scale);
    const dh = Math.round(height * scale);

    useEffect(() => {
        const img = new Image();
        img.onload = () => {
            imgRef.current = img;
            setImgReady(true);
        };
        img.src = imageB64;
    }, [imageB64]);

    useEffect(() => {
        if (!imgReady || !canvasRef.current) return;
        const ctx = canvasRef.current.getContext('2d');
        ctx.clearRect(0, 0, dw, dh);
        ctx.drawImage(imgRef.current, 0, 0, dw, dh);
        dots.forEach((d, i) => {
            ctx.beginPath();
            ctx.arc(d.x, d.y, 8, 0, Math.PI * 2);
            ctx.fillStyle = COLORS[i];
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 11px Inter,sans-serif';
            ctx.fillText(LABELS[i], d.x + 11, d.y + 4);
        });
    }, [dots, imgReady, dw, dh]);

    const handleCanvasClick = (e) => {
        if (dots.length >= 4) return;
        const rect = canvasRef.current.getBoundingClientRect();
        const x = (e.clientX - rect.left) * (dw / rect.width);
        const y = (e.clientY - rect.top) * (dh / rect.height);
        setDots(prev => [...prev, { x, y }]);
    };

    const undo = () => setDots(prev => prev.slice(0, -1));

    const handleSubmit = async () => {
        if (dots.length !== 4) return;
        setLoading(true); setErr('');
        try {
            const landmarks = LABELS.map((label, i) => ({
                label,
                x: dots[i].x / scale,
                y: dots[i].y / scale,
            }));
            await submitLandmarks({ session_id: sessionId, landmarks, image_width: width, image_height: height });
            navigate('/processing', { state: { sessionId } });
        } catch (e) {
            setErr(e.response?.data?.detail || 'Failed to submit landmarks');
        } finally { setLoading(false); }
    };

    const currentLabel = LABELS[dots.length];

    return (
        <>
            <Navbar />
            <div style={{ paddingTop: 90, minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '90px 24px 40px' }}>
                <div style={{ width: '100%', maxWidth: 900 }}>
                    <div className="text-center mb-6">
                        <div className="badge" style={{ marginBottom: 12 }}>Step 2 of 4</div>
                        <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 6 }}>Bone Structure Analysis</h1>
                        <p className="text-secondary">Please precisely mark the 4 key anatomical points on the X-ray</p>
                    </div>

                    {/* Instruction */}
                    <div className="glass" style={{ padding: '14px 20px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
                        {dots.length < 4 ? (
                            <>
                                <div style={{ width: 14, height: 14, borderRadius: '50%', background: COLORS[dots.length], flexShrink: 0 }} />
                                <span style={{ fontWeight: 600 }}>
                                    {dots.length + 1}/4 — {INSTRUCTIONS[dots.length]}
                                </span>
                            </>
                        ) : (
                            <span style={{ color: 'var(--success)', fontWeight: 600 }}>✓ All 4 landmarks placed! Ready to submit.</span>
                        )}
                    </div>

                    {/* Canvas */}
                    <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
                        <div style={{ position: 'relative', borderRadius: 14, overflow: 'hidden', border: '1px solid var(--border)', boxShadow: 'var(--shadow-glow)' }}>
                            <canvas
                                ref={canvasRef}
                                width={dw} height={dh}
                                onClick={handleCanvasClick}
                                style={{ display: 'block', cursor: dots.length < 4 ? 'crosshair' : 'default', maxWidth: '100%' }}
                            />
                        </div>
                    </div>

                    {/* Landmark chips */}
                    <div className="flex gap-3 justify-center flex-wrap mb-6">
                        {LABELS.map((lbl, i) => (
                            <div key={lbl} style={{
                                padding: '6px 14px', borderRadius: 20, fontSize: '0.8rem', fontWeight: 600,
                                background: dots[i] ? 'rgba(16,185,129,0.15)' : 'var(--bg-card)',
                                border: `1px solid ${dots[i] ? 'rgba(16,185,129,0.4)' : 'var(--border)'}`,
                                color: dots[i] ? 'var(--success)' : 'var(--text-muted)',
                                display: 'flex', alignItems: 'center', gap: 6,
                            }}>
                                {dots[i] ? '✓' : <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i], display: 'inline-block' }} />}
                                <span style={{ textTransform: 'capitalize' }}>{lbl}</span>
                            </div>
                        ))}
                    </div>

                    {err && <div className="alert alert-error mb-4">{err}</div>}

                    <div className="flex justify-center gap-4">
                        <button className="btn btn-secondary" onClick={undo} disabled={dots.length === 0}>
                            ← Undo
                        </button>
                        <button className="btn btn-primary btn-lg" onClick={handleSubmit}
                            disabled={dots.length !== 4 || loading}>
                            {loading ? <><div className="spinner" />Starting pipeline…</> : 'Run AI Analysis →'}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}
