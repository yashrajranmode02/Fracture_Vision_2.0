import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
    const { isLoggedIn, user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    return (
        <nav className="navbar">
            <div className="navbar-inner">
                <Link to="/" className="navbar-logo">
                    <span className="gradient-text">⬡ FractureVision</span>
                </Link>
                <div className="navbar-links">
                    {isLoggedIn ? (
                        <>
                            <Link to="/settings" className="flex items-center gap-2 group" style={{ marginRight: 16 }}>
                                <span className="text-sm font-bold group-hover:text-accent transition-colors">
                                    {user.user_metadata?.name || user.email.split('@')[0]}
                                </span>
                                <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent text-xs border border-accent/20 group-hover:border-accent group-hover:shadow-[0_0_15px_rgba(0,212,255,0.4)] transition-all">
                                    {user.email[0].toUpperCase()}
                                </div>
                            </Link>
                            <Link to="/history" className="btn btn-ghost btn-sm" style={{ marginRight: 8 }}>History</Link>
                            <Link to="/upload" className="btn btn-primary btn-sm">New Analysis</Link>
                            <button className="btn btn-ghost btn-sm" onClick={handleLogout} style={{ marginLeft: 8 }}>Sign out</button>
                        </>
                    ) : (
                        <>
                            <Link to="/login" className="btn btn-ghost btn-sm">Sign in</Link>
                            <Link to="/register" className="btn btn-primary btn-sm">Get started</Link>
                        </>
                    )}
                </div>
            </div>
        </nav>
    );
}
