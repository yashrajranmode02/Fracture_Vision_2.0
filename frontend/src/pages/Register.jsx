import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authRegister } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Register() {
    const { register: authRegister } = useAuth();
    const navigate = useNavigate();
    const [form, setForm] = useState({ name: '', email: '', password: '' });
    const [err, setErr] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);

    const handle = async (e) => {
        e.preventDefault();
        setErr(''); setLoading(true);
        console.log("[Register] Attempting sign-up for:", form.email, "Name:", form.name);
        try {
            await authRegister(form.email, form.password, form.name);
            setSuccess(true);
        } catch (e) {
            console.error("[Register] Error:", e);
            setErr(e.message || 'Registration failed');
        } finally { setLoading(false); }
    };

    if (success) {
        return (
            <div className="page-center">
                <div className="glass text-center" style={{ width: '100%', maxWidth: 440, padding: '48px 40px' }}>
                    <div style={{ fontSize: '3.5rem', marginBottom: 20 }}>📧</div>
                    <h1 style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: 12 }}>Check your email</h1>
                    <p className="text-secondary mb-8">
                        We've sent a verification link to <strong>{form.email}</strong>.
                        Please confirm your email to activate your clinical account.
                    </p>
                    <Link to="/login" className="btn btn-primary w-full" style={{ justifyContent: 'center' }}>
                        Back to Login
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="page-center">
            <div className="glass" style={{ width: '100%', maxWidth: 440, padding: '48px 40px' }}>
                <div className="text-center mb-8">
                    <div style={{ fontSize: '2rem', marginBottom: 12 }}>⬡</div>
                    <h1 style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: 6 }}>Create account</h1>
                    <p className="text-secondary text-sm">Start analyzing fractures in minutes</p>
                </div>
                <form onSubmit={handle} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    {err && <div className="alert alert-error">{err}</div>}
                    <div className="form-group">
                        <label className="form-label">Full Name</label>
                        <input className="form-input" type="text" placeholder="Dr. Jane Doe" required
                            value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Email</label>
                        <input className="form-input" type="email" placeholder="you@example.com" required
                            value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input className="form-input" type="password" placeholder="min. 8 characters" required minLength={6}
                            value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
                    </div>
                    <button className="btn btn-primary w-full" style={{ justifyContent: 'center', marginTop: 4 }} disabled={loading}>
                        {loading ? <><div className="spinner" />Creating account…</> : 'Create account →'}
                    </button>
                </form>
                <p className="text-center text-sm mt-6" style={{ color: 'var(--text-secondary)' }}>
                    Already have an account? <Link to="/login" className="text-accent">Sign in</Link>
                </p>
            </div>
        </div>
    );
}
