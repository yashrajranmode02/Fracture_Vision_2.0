import { useState } from "react";
import { uploadXray, uploadModel } from "../api";

export default function UploadXray({ onNext }) {
  const [sessionId, setSessionId] = useState(null);
  const [xrayImage, setXrayImage] = useState(null);
  const [xrayFileName, setXrayFileName] = useState("");
  const [modelFileName, setModelFileName] = useState("");
  const [loading, setLoading] = useState(false);

  // ============================
  // X-RAY UPLOAD
  // ============================
  const handleXrayUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setXrayFileName(file.name);

    try {
      const res = await uploadXray(file);

      setSessionId(res.session_id);
      setXrayImage(res.image_base64); // ✅ STORE LOCALLY

      alert("X-ray uploaded successfully");

    } catch (err) {
      console.error(err);
      alert("Failed to upload X-ray");
    } finally {
      setLoading(false);
    }
  };

  // ============================
  // MODEL UPLOAD
  // ============================
  const handleModelUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !sessionId) return;

    setLoading(true);
    setModelFileName(file.name);

    try {
      await uploadModel(file, sessionId);
      alert("3D model uploaded successfully");
    } catch (err) {
      console.error(err);
      alert("Failed to upload 3D model");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-xl p-8">

        <h1 className="text-3xl font-bold text-center text-gray-900">
          Upload Medical Data
        </h1>

        {/* ========================= */}
        {/* X-RAY UPLOAD */}
        {/* ========================= */}
        <label className="mt-8 flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-xl p-10 cursor-pointer hover:border-blue-500">
          <span className="font-semibold">Upload X-ray</span>
          <span className="text-sm text-gray-500">JPG / PNG</span>

          <input
            type="file"
            accept=".jpg,.jpeg,.png"
            className="hidden"
            onChange={handleXrayUpload}
          />
        </label>

        {xrayFileName && (
          <p className="mt-2 text-green-600 text-sm font-medium">
            ✓ {xrayFileName}
          </p>
        )}

        {/* ========================= */}
        {/* MODEL UPLOAD */}
        {/* ========================= */}
        {sessionId && (
          <label className="mt-6 flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-xl p-8 cursor-pointer hover:border-purple-500">
            <span className="font-semibold">Upload 3D Model (Optional)</span>
            <span className="text-sm text-gray-500">GLB / GLTF</span>

            <input
              type="file"
              accept=".glb,.gltf"
              className="hidden"
              onChange={handleModelUpload}
            />
          </label>
        )}

        {/* ========================= */}
        {/* CONTINUE BUTTON */}
        {/* ========================= */}
        {xrayImage && (
          <button
            onClick={() => onNext(sessionId, xrayImage)}
            className="mt-8 w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700"
          >
            Continue to Mark Landmarks
          </button>
        )}
      </div>
    </div>
  );
}
