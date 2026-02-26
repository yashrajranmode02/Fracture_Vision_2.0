import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Upload from './pages/Upload';
import Landmarks from './pages/Landmarks';
import Processing from './pages/Processing';
import Report from './pages/Report';
import History from './pages/History';
import Settings from './pages/Settings';

function RequireAuth({ children }) {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/upload" element={<RequireAuth><Upload /></RequireAuth>} />
          <Route path="/landmarks" element={<RequireAuth><Landmarks /></RequireAuth>} />
          <Route path="/processing" element={<RequireAuth><Processing /></RequireAuth>} />
          <Route path="/report" element={<RequireAuth><Report /></RequireAuth>} />
          <Route path="/report/:sessionId" element={<RequireAuth><Report /></RequireAuth>} />
          <Route path="/history" element={<RequireAuth><History /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
