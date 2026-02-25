import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';

const features = [
    { icon: '🩻', title: 'AI Fracture Detection', desc: 'YOLO-powered model detects ulna and radius fractures from X-ray with high accuracy.' },
    { icon: '🧠', title: 'LLM Risk Analysis', desc: 'Groq Llama-3.3 analyzes neurovascular structures at risk with clinical reasoning.' },
    { icon: '🦴', title: '3D Model Generation', desc: 'Real bone geometry is deformed to match the exact fracture angle and location.' },
    { icon: '⚡', title: 'Real-Time Pipeline', desc: 'Live step-by-step progress as your scan is analyzed — no black boxes.' },
];

const steps = [
    { n: '01', t: 'Upload X-Ray', d: 'Drop your forearm X-ray image.' },
    { n: '02', t: 'Mark Landmarks', d: 'Click 4 bone endpoints on the image — all in-browser.' },
    { n: '03', t: 'AI Analysis', d: 'Watch the pipeline detect, measure, and model your fracture live.' },
    { n: '04', t: 'View Report', d: 'Full 3D fractured model + clinical risk assessment.' },
];

export default function Landing() {
    return (
        <>
            <Navbar />
            <main style={{ paddingTop: 72 }}>
                {/* Hero */}
                <section style={{
                    minHeight: '90vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    textAlign: 'center', padding: '60px 24px', position: 'relative', overflow: 'hidden',
                }}>
                    {/* Background glow */}
                    <div style={{
                        position: 'absolute', top: '30%', left: '50%', transform: 'translate(-50%,-50%)',
                        width: 600, height: 600, borderRadius: '50%',
                        background: 'radial-gradient(circle, rgba(0,212,255,0.08) 0%, transparent 70%)',
                        pointerEvents: 'none',
                    }} />
                    <div style={{ maxWidth: 760, position: 'relative' }}>
                        <div className="badge" style={{ marginBottom: 28 }}>
                            ✦ AI-Powered Fracture Intelligence
                        </div>
                        <h1 style={{ fontSize: 'clamp(2.5rem,6vw,4.5rem)', fontWeight: 900, lineHeight: 1.1, marginBottom: 24, letterSpacing: '-0.03em' }}>
                            Detect &amp; Visualize<br />
                            <span className="gradient-text">Forearm Fractures</span><br />
                            in 3D
                        </h1>
                        <p style={{ fontSize: '1.15rem', color: 'var(--text-secondary)', marginBottom: 44, maxWidth: 560, margin: '0 auto 44px' }}>
                            Upload an X-ray, mark landmarks in your browser, and get an AI-generated 3D fractured bone model with full clinical risk analysis — in under a minute.
                        </p>
                        <div className="flex justify-center gap-4" style={{ flexWrap: 'wrap' }}>
                            <Link to="/register" className="btn btn-primary btn-lg">Start Free Analysis →</Link>
                            <Link to="/login" className="btn btn-secondary btn-lg">Sign In</Link>
                        </div>
                    </div>
                </section>

                {/* Features */}
                <section style={{ padding: '80px 24px', maxWidth: 1200, margin: '0 auto' }}>
                    <h2 style={{ textAlign: 'center', fontSize: '2rem', fontWeight: 800, marginBottom: 12 }}>
                        Why <span className="gradient-text">FractureVision</span>?
                    </h2>
                    <p style={{ textAlign: 'center', color: 'var(--text-secondary)', marginBottom: 56 }}>
                        End-to-end AI pipeline, from raw X-ray to 3D clinical report.
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 24 }}>
                        {features.map(f => (
                            <div key={f.title} className="glass" style={{ padding: 28 }}>
                                <div style={{ fontSize: '2rem', marginBottom: 14 }}>{f.icon}</div>
                                <h3 style={{ fontWeight: 700, marginBottom: 8 }}>{f.title}</h3>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.7 }}>{f.desc}</p>
                            </div>
                        ))}
                    </div>
                </section>

                {/* How it works */}
                <section style={{ padding: '80px 24px', background: 'rgba(255,255,255,0.015)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ maxWidth: 900, margin: '0 auto' }}>
                        <h2 style={{ textAlign: 'center', fontSize: '2rem', fontWeight: 800, marginBottom: 56 }}>
                            How it <span className="gradient-text">works</span>
                        </h2>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 32 }}>
                            {steps.map(s => (
                                <div key={s.n} style={{ textAlign: 'center' }}>
                                    <div style={{
                                        width: 56, height: 56, borderRadius: '50%', margin: '0 auto 16px',
                                        background: 'var(--accent-dim)', border: '1px solid var(--border-accent)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontWeight: 800, fontSize: '1rem', color: 'var(--accent)',
                                    }}>{s.n}</div>
                                    <h3 style={{ fontWeight: 700, marginBottom: 8 }}>{s.t}</h3>
                                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{s.d}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* CTA */}
                <section style={{ padding: '100px 24px', textAlign: 'center' }}>
                    <h2 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: 20 }}>
                        Ready to analyze your <span className="gradient-text">scan</span>?
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 36 }}>
                        No setup required. Works entirely in your browser.
                    </p>
                    <Link to="/register" className="btn btn-primary btn-lg">Get Started for Free →</Link>
                </section>

                <footer style={{ textAlign: 'center', padding: '24px', borderTop: '1px solid var(--border)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    © 2025 FractureVision — AI Fracture Analysis
                </footer>
            </main>
        </>
    );
}
