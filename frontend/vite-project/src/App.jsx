
import { useState } from "react";
import UploadXray from "./pages/UploadXray";
import MarkLandmarks from "./pages/MarkLandmarks";
import Report from "./pages/Report";
import VisualizeModel from "./pages/VisualizeModel";

export default function App() {
  const [page, setPage] = useState("upload");
  const [sessionId, setSessionId] = useState(null);
  const [xrayImage, setXrayImage] = useState(null);
  const [fractureData, setFractureData] = useState(null);

  return (
    <div className="min-h-screen bg-gray-100">
      {page === "upload" && (
        <UploadXray
          onNext={(sid, img) => {
            setSessionId(sid);
            setXrayImage(img);
            setPage("landmarks");
          }}
        />
      )}

      {page === "landmarks" && (
        <MarkLandmarks
          sessionId={sessionId}
          xrayImage={xrayImage}
          onDone={(data) => {
            setFractureData(data);
            setPage("report");
          }}
        />
      )}

      {page === "report" && (
        <Report
          data={fractureData}
          onVisualize={() => setPage("visualize")}
          onReset={() => setPage("upload")}
        />
      )}

      {page === "visualize" && (
        <VisualizeModel
          sessionId={sessionId}
          onBack={() => setPage("report")}
        />
      )}
    </div>
  );
}
