import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const Settings = () => {
    const { user, signOut } = useAuth();
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const fetchProfile = async () => {
            if (!user) return;
            try {
                const token = sessionStorage.getItem('sb-access-token');
                const res = await axios.get('http://localhost:8000/api/auth/me', {
                    headers: { Authorization: `Bearer ${token}` }
                });
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
            const token = sessionStorage.getItem('sb-access-token');
            await axios.patch('http://localhost:8000/api/auth/profile', { name }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setMessage('Profile updated successfully!');
            // Update local user name if possible or just refresh
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
                            onClick={signOut}
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
