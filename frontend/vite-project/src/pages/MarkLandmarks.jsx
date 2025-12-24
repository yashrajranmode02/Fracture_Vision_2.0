
import LandmarkCanvas from "../components/LandmarkCanvas";

export default function MarkLandmarks({ xrayImage, sessionId, onDone }) {
  return (
    <div className="max-w-4xl mx-auto py-10">
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-xl font-bold mb-4">Mark Landmarks</h2>

        <LandmarkCanvas
          image={xrayImage}
          sessionId={sessionId}
          onSubmit={onDone}
        />
      </div>
    </div>
  );
}
