import axios from 'axios';
import { supabase } from './supabase';

// Use relative URLs so everything goes through the Vite dev proxy → localhost:8000
const api = axios.create({ baseURL: '' });

api.interceptors.request.use(async cfg => {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
        cfg.headers.Authorization = `Bearer ${session.access_token}`;
    }
    return cfg;
});

export const uploadXray = (file, reportName) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('report_name', reportName);
    return api.post('/api/upload', fd);
};

export const submitLandmarks = (payload) => api.post('/api/landmarks', payload);

export const getReport = (sessionId) => api.get(`/api/report/${sessionId}`);

// Model URL must be absolute for the <model-viewer> component
export const getModelUrl = (sessionId) =>
    `http://localhost:8000/api/model/${sessionId}`;

export const authRegister = (data) => api.post('/api/auth/register', data);
export const authLogin = (data) => api.post('/api/auth/login', data);
export const chatWithAi = (query, sessionId) => api.post('/api/chat', { query, session_id: sessionId });
export const getHistory = () => api.get('/api/history');

/** SSE — must be absolute URL (EventSource doesn't use axios) */
export const openProgressStream = (sessionId) =>
    new EventSource(`http://localhost:8000/api/progress/${sessionId}`);

export default api;
