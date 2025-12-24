import { useEffect, useRef } from "react";
import { getModelUrl } from "../api";

export default function ModelViewer({ sessionId }) {
  const ref = useRef();

  useEffect(() => {
    (async () => {
      const THREE = await import("three");
      const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
      const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");

      ref.current.innerHTML = "";
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(70, 1, 0.1, 1000);
      camera.position.z = 2;

      const renderer = new THREE.WebGLRenderer();
      renderer.setSize(600, 400);
      ref.current.appendChild(renderer.domElement);

      const controls = new OrbitControls(camera, renderer.domElement);
      scene.add(new THREE.AmbientLight(0xffffff));

      new GLTFLoader().load(getModelUrl(sessionId), (g) => scene.add(g.scene));

      const animate = () => {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      };
      animate();
    })();
  }, [sessionId]);

  return <div ref={ref}></div>;
}
