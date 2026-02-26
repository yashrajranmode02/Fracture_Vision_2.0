import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { openProgressStream } from '../api/client';
import Navbar from '../components/Navbar';

const STEP_LABELS = [
    '',
    '3D Model Initialization',
    'Anatomical Segmentation',
    'Fracture Detection',
    'Geometry Reconstruction',
    'Cloud Synchronization',
    'AI Risk Assessment',
    'Diagnostic Finalized',
];

export default function Processing() {
    const { state } = useLocation();
    const navigate = useNavigate();
    const [steps, setSteps] = useState([]);
    const [currentMsg, setCurrentMsg] = useState('Initializing…');
    const [status, setStatus] = useState('running'); // running | done | error

    if (!state?.sessionId) { navigate('/upload'); return null; }
    const { sessionId } = state;

    useEffect(() => {
        const es = openProgressStream(sessionId);

        es.onmessage = (e) => {
            const ev = JSON.parse(e.data);
            setCurrentMsg(ev.message);
            setStatus(ev.status);

            if (ev.step > 0) {
                setSteps(prev => {
                    const next = [...prev];
                    const existing = next.find(s => s.step === ev.step);
                    if (!existing) {
                        next.push({ step: ev.step, label: ev.message, status: ev.status });
                    } else {
                        existing.status = ev.status;
                        existing.label = ev.message;
                    }
                    // Mark all previous steps as done
                    return next.map(s => s.step < ev.step ? { ...s, status: 'done' } : s);
                });
            }

            if (ev.status === 'done') {
                es.close();
                // Mark final step as done
                setSteps(prev => prev.map(s => ({ ...s, status: 'done' })));
                setTimeout(() => navigate('/report', { state: { sessionId } }), 1200);
            }
            if (ev.status === 'error') es.close();
        };

        es.onerror = () => {
            setStatus('error');
            setCurrentMsg('Connection to backend lost. Is the server running?');
            es.close();
        };

        return () => es.close();
    }, [sessionId]);

    const allStepNums = [1, 2, 3, 4, 5, 6, 7];

    return (
        <>
            <Navbar />
            <div className="page-center" style={{ paddingTop: 100, alignItems: 'flex-start' }}>
                <div style={{ width: '100%', maxWidth: 640 }}>
                    <div className="text-center mb-8">
                        <div className="badge" style={{ marginBottom: 12 }}>Step 3 of 4</div>
                        <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 8 }}>
                            {status === 'error' ? '⚠️ Pipeline Error' : status === 'done' ? '✅ Analysis Complete!' : 'Running AI Pipeline…'}
                        </h1>
                        <p className="text-secondary">{currentMsg}</p>
                    </div>

                    {/* Step list */}
                    <div className="steps-list">
                        {allStepNums.map(n => {
                            const ev = steps.find(s => s.step === n);
                            const done = ev && ev.status !== 'running';
                            const active = ev && ev.status === 'running';
                            const isErr = ev && ev.status === 'error';
                            return (
                                <div key={n} className={`step-item ${active ? 'active' : ''} ${done && !isErr ? 'done' : ''} ${isErr ? 'error' : ''}`}>
                                    <div className="step-icon">
                                        {active ? <div className="spinner" style={{ width: 16, height: 16 }} /> :
                                            done && !isErr ? '✓' :
                                                isErr ? '✕' : n}
                                    </div>
                                    <div>
                                        <div className="step-label" style={{ fontWeight: 600 }}>{STEP_LABELS[n]}</div>
                                        {ev && ev.label !== STEP_LABELS[n] && (
                                            <div className="text-xs text-muted mt-1" style={{ opacity: 0.8 }}>{ev.label}</div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {status === 'error' && (
                        <div className="mt-6 text-center">
                            <button className="btn btn-secondary" onClick={() => navigate('/upload')}>
                                ← Try again
                            </button>
                        </div>
                    )}

                    {status === 'done' && (
                        <div className="mt-6 text-center">
                            <button className="btn btn-primary btn-lg" onClick={() => navigate('/report', { state: { sessionId } })}>
                                View Report →
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}
