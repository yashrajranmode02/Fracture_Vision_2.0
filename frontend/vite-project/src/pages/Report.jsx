
export default function Report({ data, onVisualize, onReset }) {
  if (!data) return null;

  const severityColor = {
    mild: "bg-green-100 text-green-800",
    moderate: "bg-yellow-100 text-yellow-800",
    severe: "bg-red-100 text-red-800",
  };

  return (
    <div className="min-h-screen bg-gray-100 flex justify-center px-4 py-10">
      <div className="bg-white max-w-4xl w-full rounded-2xl shadow-xl p-8">

        {/* HEADER */}
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Fracture Report
        </h1>
        <p className="text-gray-500 mb-6">
          AI-assisted fracture analysis summary
        </p>

        {/* CONFIDENCE */}
        <div className="mb-6">
          <div className="flex justify-between mb-1">
            <span className="font-semibold text-gray-700">
              Detection Confidence
            </span>
            <span className="font-bold text-blue-600">
              {(data.confidence * 100).toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full"
              style={{ width: `${data.confidence * 100}%` }}
            />
          </div>
        </div>

        {/* DETECTED BONES */}
        <div className="mb-6">
          <h2 className="font-semibold text-gray-700 mb-2">
            Detected Bones
          </h2>
          <div className="flex gap-3 flex-wrap">
            {data.detected_bones.map((bone, i) => (
              <span
                key={i}
                className="px-4 py-2 rounded-full bg-blue-100 text-blue-800 font-medium capitalize"
              >
                {bone}
              </span>
            ))}
          </div>
        </div>

        {/* FRACTURE DETAILS */}
        <div className="grid md:grid-cols-2 gap-6">
          {data.fractures.map((f, i) => (
            <div
              key={i}
              className="border rounded-xl p-6 hover:shadow-lg transition"
            >
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold capitalize text-gray-800">
                  {f.bone} Fracture
                </h3>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-semibold capitalize ${
                    severityColor[f.severity]
                  }`}
                >
                  {f.severity}
                </span>
              </div>

              <div className="space-y-2 text-gray-700">
                <div className="flex justify-between">
                  <span>Damage Type</span>
                  <span className="font-semibold capitalize">
                    {f.damage}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Location</span>
                  <span className="font-semibold">
                    {(f.location * 100).toFixed(0)}%
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Top Angle</span>
                  <span className="font-semibold">
                    {f.top_angle.toFixed(1)}°
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Bottom Angle</span>
                  <span className="font-semibold">
                    {f.bottom_angle.toFixed(1)}°
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* ACTION BUTTONS */}
        <div className="flex flex-col sm:flex-row gap-4 mt-10">
          <button
            onClick={onVisualize}
            className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
          >
            View 3D Model
          </button>

          <button
            onClick={onReset}
            className="flex-1 bg-gray-600 text-white py-3 rounded-lg font-semibold hover:bg-gray-700 transition"
          >
            New Analysis
          </button>
        </div>

        {/* FOOTER */}
        <p className="text-xs text-gray-400 text-center mt-6">
          This report is generated for academic & research purposes
        </p>
      </div>
    </div>
  );
}
