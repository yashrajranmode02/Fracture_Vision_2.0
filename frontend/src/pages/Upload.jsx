import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadXray } from '../api/client';
import Navbar from '../components/Navbar';

export default function Upload() {
    const navigate = useNavigate();
    const [dragging, setDragging] = useState(false);
    const [preview, setPreview] = useState(null);
    const [file, setFile] = useState(null);
    const [rotation, setRotation] = useState(0);
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState('');
    const [reportName, setReportName] = useState('');

    const handleFile = (f) => {
        if (!f || !f.type.startsWith('image/')) {
            setErr('Please upload a valid image file (JPG, PNG, etc.)');
            return;
        }
        setErr('');
        setFile(f);
        setPreview(URL.createObjectURL(f));
        setRotation(0);
    };

    const onDrop = useCallback((e) => {
        e.preventDefault();
        setDragging(false);
        handleFile(e.dataTransfer.files[0]);
    }, []);

    const onDragOver = (e) => { e.preventDefault(); setDragging(true); };
    const onDragLeave = () => setDragging(false);

    const rotate = () => setRotation((r) => (r + 90) % 360);

    const handleSubmit = async () => {
        if (!file || !reportName) return;
        setLoading(true); setErr('');
        try {
            // Apply rotation to a canvas and get a new blob/b64
            const img = new Image();
            img.src = preview;
            await new Promise((res) => (img.onload = res));

            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');

            if (rotation === 90 || rotation === 270) {
                canvas.width = img.height;
                canvas.height = img.width;
            } else {
                canvas.width = img.width;
                canvas.height = img.height;
            }

            ctx.translate(canvas.width / 2, canvas.height / 2);
            ctx.rotate((rotation * Math.PI) / 180);
            ctx.drawImage(img, -img.width / 2, -img.height / 2);

            const rotatedDataUrl = canvas.toDataURL('image/jpeg', 0.9);
            const res = await fetch(rotatedDataUrl);
            const rotatedBlob = await res.blob();
            const rotatedFile = new File([rotatedBlob], file.name, { type: 'image/jpeg' });

            const { data } = await uploadXray(rotatedFile, reportName);
            navigate('/landmarks', { state: { sessionId: data.session_id, imageB64: data.image_base64, width: data.width, height: data.height } });
        } catch (e) {
            setErr(e.response?.data?.detail || 'Upload failed. Is the backend running?');
        } finally { setLoading(false); }
    };

    return (
        <>
            <Navbar />
            <div className="page-center" style={{ paddingTop: 100 }}>
                <div style={{ width: '100%', maxWidth: 640 }}>
                    <div className="text-center mb-8">
                        <div className="badge" style={{ marginBottom: 16 }}>Step 1 of 4</div>
                        <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: 8 }}>Upload New X-Ray</h1>
                        <p className="text-secondary">Drag & drop your DICOM or Image file here to start the AI fracture detection process.</p>
                    </div>

                    <div className="glass mb-8" style={{ padding: 24, borderRadius: 20 }}>
                        <div className="form-group">
                            <label className="form-label">Analysis Name / Patient ID</label>
                            <input
                                className="form-input"
                                type="text"
                                placeholder="e.g. Patient #1234 or Left Radius Case"
                                value={reportName}
                                onChange={e => setReportName(e.target.value)}
                                style={{ background: 'rgba(0,0,0,0.2)' }}
                            />
                            <p className="text-xs text-secondary mt-2">Required to track this case in your history</p>
                        </div>
                    </div>

                    {/* Drop zone */}
                    <div
                        className="glass"
                        onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
                        onClick={() => !preview && document.getElementById('file-input').click()}
                        style={{
                            border: `2px dashed ${dragging ? 'var(--accent)' : preview ? 'var(--border)' : 'var(--border)'}`,
                            borderRadius: 20, padding: 40, textAlign: 'center',
                            cursor: preview ? 'default' : 'pointer',
                            transition: 'var(--transition)',
                            background: dragging ? 'var(--accent-dim)' : 'var(--bg-card)',
                            minHeight: 280, display: 'flex', flexDirection: 'column',
                            alignItems: 'center', justifyContent: 'center', gap: 16,
                            position: 'relative'
                        }}
                    >
                        <input id="file-input" type="file" accept="image/*" style={{ display: 'none' }}
                            onChange={e => handleFile(e.target.files[0])} />

                        {preview ? (
                            <>
                                <div style={{
                                    transition: 'transform 0.3s ease-out',
                                    transform: `rotate(${rotation}deg)`,
                                    maxHeight: 320, maxWidth: '100%',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}>
                                    <img src={preview} alt="Preview"
                                        style={{ maxHeight: 320, maxWidth: '100%', borderRadius: 12, objectFit: 'contain' }} />
                                </div>
                                <div className="flex gap-4 mt-4">
                                    <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); rotate(); }}>
                                        🔄 Rotate 90°
                                    </button>
                                    <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); setPreview(null); setFile(null); }}>
                                        Remove ✕
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                <div style={{ fontSize: '3rem' }}>🩻</div>
                                <div>
                                    <p style={{ fontWeight: 600, marginBottom: 4 }}>Drag &amp; drop your DICOM or Image file here</p>
                                    <p className="text-sm text-secondary">or click to browse files</p>
                                </div>
                                <p className="text-xs text-muted">Supports JPG, PNG, JPEG, DCM · Max 20MB</p>
                            </>
                        )}
                    </div>

                    {err && <div className="alert alert-error mt-4">{err}</div>}

                    <div className="flex justify-center mt-6">
                        <button
                            className="btn btn-primary btn-lg"
                            disabled={!file || !reportName || loading}
                            onClick={handleSubmit}
                        >
                            {loading ? <><div className="spinner" />Analyzing Radiography... Uploading and processing X-ray image</> : 'Continue to Landmark Marking →'}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}
