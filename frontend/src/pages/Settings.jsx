import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';
import { useNavigate } from 'react-router-dom';

const Settings = () => {
    const { user, logout } = useAuth();
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const fetchProfile = async () => {
            if (!user) return;
            try {
                // Using the centralized api client which already handles the token
                const res = await api.get('/api/auth/me');
                setName(res.data.name || '');
            } catch (err) {
                console.error("Error fetching profile:", err);
            }
        };
        fetchProfile();
    }, [user]);

    const handleUpdate = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage('');
        try {
            await api.patch('/api/auth/profile', { name });
            setMessage('Profile updated successfully!');
            setTimeout(() => setMessage(''), 3000);
        } catch (err) {
            console.error("Update error:", err);
            setMessage('Failed to update profile.');
        } finally {
            setLoading(false);
        }
    };

    if (!user) return null;

    return (
        <div className="container pt-32 pb-20 max-w-2xl">
            <div className="glass p-10 rounded-3xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-5">
                    <span className="text-9xl">⚙️</span>
                </div>

                <h1 className="text-4xl font-black mb-2 tracking-tight">Account Settings</h1>
                <p className="text-muted mb-10">Manage your clinical profile and account preferences.</p>

                <form onSubmit={handleUpdate} className="space-y-8">
                    <div className="form-group">
                        <label className="form-label">Full Name</label>
                        <input
                            type="text"
                            className="form-input"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Dr. Alex Smith"
                            required
                        />
                    </div>

                    <div className="form-group opacity-60">
                        <label className="form-label">Email Address</label>
                        <input
                            type="email"
                            className="form-input cursor-not-allowed"
                            value={user.email}
                            disabled
                        />
                        <p className="text-[10px] uppercase font-bold tracking-widest mt-2 text-accent/60">
                            Email cannot be changed after clinical verification
                        </p>
                    </div>

                    {message && (
                        <div className={`p-4 rounded-xl text-sm font-bold ${message.includes('success') ? 'bg-success/10 text-success border border-success/20' : 'bg-danger/10 text-danger border border-danger/20'}`}>
                            {message}
                        </div>
                    )}

                    <div className="flex gap-4 pt-4">
                        <button
                            type="submit"
                            className="btn btn-primary flex-grow justify-center"
                            disabled={loading}
                        >
                            {loading ? 'Saving...' : 'Update Profile'}
                        </button>
                        <button
                            type="button"
                            onClick={logout}
                            className="btn btn-secondary border-danger/20 text-danger hover:bg-danger/5 hover:border-danger/40"
                        >
                            Log Out
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default Settings;
