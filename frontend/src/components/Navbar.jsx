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
                            <span className="text-secondary text-sm" style={{ marginRight: 8 }}>
                                {user?.name}
                            </span>
                            <Link to="/history" className="btn btn-ghost btn-sm" style={{ marginRight: 8 }}>History</Link>
                            <Link to="/upload" className="btn btn-primary btn-sm">New Analysis</Link>
                            <button className="btn btn-ghost btn-sm" onClick={handleLogout}>Sign out</button>
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
