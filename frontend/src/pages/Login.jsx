import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authLogin } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [form, setForm] = useState({ email: '', password: '' });
    const [err, setErr] = useState('');
    const [loading, setLoading] = useState(false);

    const handle = async (e) => {
        e.preventDefault();
        setErr(''); setLoading(true);
        try {
            await login(form.email, form.password);
            navigate('/upload');
        } catch (e) {
            if (e.message?.includes('Email not confirmed')) {
                setErr('Please verify your email address. Check your inbox for a confirmation link.');
            } else {
                setErr(e.message || 'Login failed');
            }
        } finally { setLoading(false); }
    };

    return (
        <div className="page-center">
            <div className="glass" style={{ width: '100%', maxWidth: 440, padding: '48px 40px' }}>
                <div className="text-center mb-8">
                    <div style={{ fontSize: '2rem', marginBottom: 12 }}>⬡</div>
                    <h1 style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: 6 }}>Welcome back</h1>
                    <p className="text-secondary text-sm">Sign in to your FractureVision account</p>
                </div>
                <form onSubmit={handle} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    {err && <div className="alert alert-error">{err}</div>}
                    <div className="form-group">
                        <label className="form-label">Email</label>
                        <input className="form-input" type="email" placeholder="you@example.com" required
                            value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input className="form-input" type="password" placeholder="••••••••" required
                            value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
                    </div>
                    <button className="btn btn-primary w-full" style={{ justifyContent: 'center', marginTop: 4 }} disabled={loading}>
                        {loading ? <><div className="spinner" />Signing in…</> : 'Sign in →'}
                    </button>
                </form>
                <p className="text-center text-sm mt-6" style={{ color: 'var(--text-secondary)' }}>
                    Don't have an account? <Link to="/register" className="text-accent">Sign up</Link>
                </p>
            </div>
        </div>
    );
}
