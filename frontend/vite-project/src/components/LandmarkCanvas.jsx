// // // import { useRef, useState } from "react";

// // // const labels = ["Ulna Head", "Ulna Tail", "Radius Head", "Radius Tail"];

// // // export default function LandmarkCanvas({ image, onSubmit }) {
// // //   const ref = useRef();
// // //   const [points, setPoints] = useState([]);

// // //   const handleClick = (e) => {
// // //     if (points.length >= 4) return;
// // //     const rect = ref.current.getBoundingClientRect();
// // //     setPoints([
// // //       ...points,
// // //       { x: e.clientX - rect.left, y: e.clientY - rect.top, label: labels[points.length] },
// // //     ]);
// // //   };

// // //   return (
// // //     <>
// // //       <canvas
// // //         ref={ref}
// // //         onClick={handleClick}
// // //         width={600}
// // //         height={400}
// // //         style={{ backgroundImage: `url(${image})`, backgroundSize: "contain" }}
// // //       />
// // //       {points.length === 4 && (
// // //         <button onClick={() => onSubmit(points)}>Process</button>
// // //       )}
// // //     </>
// // //   );
// // // }
// // import { useRef, useState } from "react";
// // import { processLandmarks } from "../api";

// // const labels = ["Ulna Head", "Ulna Tail", "Radius Head", "Radius Tail"];

// // export default function LandmarkCanvas({ image, sessionId, onSubmit }) {
// //   const canvasRef = useRef();
// //   const [points, setPoints] = useState([]);

// //   const handleClick = (e) => {
// //     if (points.length >= 4) return;

// //     const rect = canvasRef.current.getBoundingClientRect();
// //     const x = e.clientX - rect.left;
// //     const y = e.clientY - rect.top;

// //     setPoints([...points, { x, y, label: labels[points.length] }]);
// //   };

// //   const handleProcess = async () => {
// //     const data = await processLandmarks(sessionId, points);
// //     onSubmit(data);
// //   };

// //   return (
// //     <>
// //       <canvas
// //         ref={canvasRef}
// //         width={700}
// //         height={400}
// //         onClick={handleClick}
// //         className="border rounded-lg mx-auto block cursor-crosshair"
// //         style={{
// //           backgroundImage: `url(${image})`,
// //           backgroundSize: "contain",
// //           backgroundRepeat: "no-repeat",
// //           backgroundPosition: "center",
// //         }}
// //       />

// //       {points.length === 4 && (
// //         <button
// //           onClick={handleProcess}
// //           className="mt-4 bg-green-600 text-white px-6 py-3 rounded-lg font-semibold"
// //         >
// //           Process Fracture
// //         </button>
// //       )}
// //     </>
// //   );
// // }
// import { useEffect, useRef, useState } from "react";
// import { processLandmarks } from "../api";

// const LANDMARK_LABELS = [
//   "Ulna Head",
//   "Ulna Tail",
//   "Radius Head",
//   "Radius Tail",
// ];

// export default function LandmarkCanvas({ image, sessionId, onSubmit }) {
//   const canvasRef = useRef(null);
//   const [points, setPoints] = useState([]);
//   const [processing, setProcessing] = useState(false);

//   // =========================
//   // DRAW IMAGE + POINTS
//   // =========================
//   useEffect(() => {
//     if (!image || !canvasRef.current) return;

//     const canvas = canvasRef.current;
//     const ctx = canvas.getContext("2d");

//     const img = new Image();
//     img.onload = () => {
//       // Resize canvas to image
//       canvas.width = img.width;
//       canvas.height = img.height;

//       // Draw image
//       ctx.clearRect(0, 0, canvas.width, canvas.height);
//       ctx.drawImage(img, 0, 0);

//       // Draw points
//       points.forEach((p, index) => {
//         // Circle
//         ctx.fillStyle = "#ef4444";
//         ctx.beginPath();
//         ctx.arc(p.x, p.y, 8, 0, Math.PI * 2);
//         ctx.fill();

//         // Number
//         ctx.fillStyle = "#ffffff";
//         ctx.font = "bold 14px Arial";
//         ctx.textAlign = "center";
//         ctx.textBaseline = "middle";
//         ctx.fillText(index + 1, p.x, p.y);

//         // Label
//         ctx.fillStyle = "#1f2937";
//         ctx.font = "14px Arial";
//         ctx.textAlign = "left";
//         ctx.fillText(
//           LANDMARK_LABELS[index],
//           p.x + 12,
//           p.y - 10
//         );
//       });
//     };

//     img.src = image;
//   }, [image, points]);

//   // =========================
//   // HANDLE CLICK
//   // =========================
//   const handleClick = (e) => {
//     if (points.length >= 4) return; // 🔒 LOCK after 4

//     const canvas = canvasRef.current;
//     const rect = canvas.getBoundingClientRect();

//     const x = e.clientX - rect.left;
//     const y = e.clientY - rect.top;

//     setPoints([...points, { x, y }]);
//   };

//   // =========================
//   // SUBMIT LANDMARKS
//   // =========================
//   const handleSubmit = async () => {
//     if (points.length !== 4) return;

//     setProcessing(true);

//     try {
//       const payload = points.map((p, index) => ({
//         x: p.x,
//         y: p.y,
//         label: LANDMARK_LABELS[index],
//       }));

//       const result = await processLandmarks(sessionId, payload);
//       onSubmit(result);
//     } catch (err) {
//       console.error(err);
//       alert("Failed to process landmarks");
//     } finally {
//       setProcessing(false);
//     }
//   };

//   return (
//     <div className="flex flex-col items-center">
      
//       {/* STATUS */}
//       <div className="mb-3 text-sm font-semibold text-gray-700">
//         {points.length < 4
//           ? `Landmark ${points.length + 1} of 4: ${LANDMARK_LABELS[points.length]}`
//           : "All landmarks selected"}
//       </div>

//       {/* CANVAS */}
//       <div className="border rounded-lg overflow-auto max-w-full">
//         <canvas
//           ref={canvasRef}
//           onClick={handleClick}
//           className={`cursor-crosshair ${
//             points.length >= 4 ? "cursor-not-allowed opacity-90" : ""
//           }`}
//         />
//       </div>

//       {/* ACTION BUTTON */}
//       {points.length === 4 && (
//         <button
//           onClick={handleSubmit}
//           disabled={processing}
//           className="mt-6 bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50"
//         >
//           {processing ? "Processing..." : "Detect Fracture"}
//         </button>
//       )}
//     </div>
//   );
// }
import { useEffect, useRef, useState } from "react";
import { processLandmarks } from "../api";

const LANDMARK_LABELS = [
  "Ulna Head",
  "Ulna Tail",
  "Radius Head",
  "Radius Tail",
];

const VIEWER_HEIGHT = 420;

export default function LandmarkCanvas({ image, sessionId, onSubmit }) {
  const canvasRef = useRef(null);
  const imgRef = useRef(null);

  const [points, setPoints] = useState([]);
  const [scale, setScale] = useState(1);
  const [processing, setProcessing] = useState(false);

  // ===============================
  // 1️⃣ LOAD IMAGE ONCE
  // ===============================
  useEffect(() => {
    if (!image || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    const img = new Image();
    img.onload = () => {
      imgRef.current = img;

      // Scale based ONLY on height
      const finalScale = Math.min(VIEWER_HEIGHT / img.height, 1);
      setScale(finalScale);

      canvas.height = img.height * finalScale;
      canvas.width = img.width * finalScale;

      // Initial draw
      ctx.drawImage(
        img,
        0,
        0,
        canvas.width,
        canvas.height
      );
    };

    img.src = image;
  }, [image]); // 🔥 ONLY image dependency

  // ===============================
  // 2️⃣ REDRAW POINTS ONLY
  // ===============================
  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext("2d");

    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Redraw image
    ctx.drawImage(
      img,
      0,
      0,
      img.width * scale,
      img.height * scale
    );

    // Draw points
    points.forEach((p, index) => {
      const x = p.x * scale;
      const y = p.y * scale;

      ctx.fillStyle = "#ef4444";
      ctx.beginPath();
      ctx.arc(x, y, 7, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 13px Arial";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(index + 1, x, y);

      ctx.fillStyle = "#111827";
      ctx.font = "13px Arial";
      ctx.textAlign = "left";
      ctx.fillText(LANDMARK_LABELS[index], x + 10, y - 10);
    });
  }, [points, scale]);

  // ===============================
  // CLICK HANDLER
  // ===============================
  const handleClick = (e) => {
    if (points.length >= 4) return;

    const rect = canvasRef.current.getBoundingClientRect();

    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;

    setPoints([...points, { x, y }]);
  };

  // ===============================
  // SUBMIT
  // ===============================
  const handleSubmit = async () => {
    setProcessing(true);
    try {
      const payload = points.map((p, i) => ({
        x: p.x,
        y: p.y,
        label: LANDMARK_LABELS[i],
      }));

      const res = await processLandmarks(sessionId, payload);
      onSubmit(res);
    } catch {
      alert("Failed to process landmarks");
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="flex flex-col items-center w-full">

      <div className="mb-4 font-semibold text-gray-700">
        {points.length < 4
          ? `Landmark ${points.length + 1} of 4: ${LANDMARK_LABELS[points.length]}`
          : "All landmarks selected"}
      </div>

      <div className="w-full max-w-5xl h-[420px] border rounded-xl bg-gray-50 flex justify-center items-center overflow-hidden">
        <canvas
          ref={canvasRef}
          onClick={handleClick}
          className={`cursor-crosshair ${
            points.length >= 4 ? "cursor-not-allowed opacity-90" : ""
          }`}
        />
      </div>

      {points.length === 4 && (
        <button
          onClick={handleSubmit}
          disabled={processing}
          className="mt-6 bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700"
        >
          {processing ? "Processing..." : "Detect Fracture"}
        </button>
      )}

      <p className="mt-2 text-xs text-gray-500">
        Click accurately on anatomical landmarks
      </p>
    </div>
  );
}
