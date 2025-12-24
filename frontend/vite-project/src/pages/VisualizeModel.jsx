
import ModelViewer from "../components/ModelViewer";

export default function VisualizeModel({ sessionId, onBack }) {
  return (
    <div className="max-w-5xl mx-auto py-10">
      <div className="bg-white shadow-xl rounded-xl p-6">
        <h2 className="text-xl font-bold mb-4">3D Bone Visualization</h2>

        <ModelViewer sessionId={sessionId} />

        <button
          onClick={onBack}
          className="mt-4 bg-gray-700 text-white px-6 py-2 rounded-lg"
        >
          Back
        </button>
      </div>
    </div>
  );
}
