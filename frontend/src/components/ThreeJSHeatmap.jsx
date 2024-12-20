/* import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import * as d3 from 'd3';
const sampleArray = [
    [39, 42, 43, 38, 36, 34, 32, 33, 44, 49],
    [60, 60, 50, 30, 14, 6, 6, 8, 15, 18],
    [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    [25, 35, 45, 55, 65, 75, 85, 95, 105, 115],
    // Add more rows to simulate larger datasets
];

export default function ThreeJSHeatmap({ array = sampleArray, width = 'w-full', fixPlotHeightToParent=false, title='' }) {
    const plotRef = useRef(null);
    const containerRef = useRef(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    const sceneRef = useRef(null);
    const textureRef = useRef(null);
    const rendererRef = useRef(null);
    const cameraRef = useRef(null);

    useEffect(() => {
        const resizeObserver = new ResizeObserver((entries) => {
            if (entries[0]) {
                const { width, height } = entries[0].contentRect;
                setDimensions({ width, height });
            }
        });
        if (containerRef.current) {
            resizeObserver.observe(containerRef.current);
        }
        return () => resizeObserver.disconnect();
    }, []);

    // Initialize Three.js scene, camera, and renderer
    useEffect(() => {
        if (dimensions.width === 0 || dimensions.height === 0) return;

        const scene = new THREE.Scene();
        sceneRef.current = scene;

        const camera = new THREE.OrthographicCamera(
            -dimensions.width / 2,
            dimensions.width / 2,
            dimensions.height / 2,
            -dimensions.height / 2,
            0.1,
            10
        );
        camera.position.z = 1;
        cameraRef.current = camera;

        const renderer = new THREE.WebGLRenderer();
        renderer.setSize(dimensions.width, dimensions.height);
        plotRef.current.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Add an initial empty plane
        const canvas = document.createElement('canvas');
        const texture = new THREE.CanvasTexture(canvas);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.needsUpdate = true;
        textureRef.current = texture;

        const geometry = new THREE.PlaneGeometry(dimensions.width, dimensions.height);
        const material = new THREE.MeshBasicMaterial({ map: texture, transparent: false });
        const plane = new THREE.Mesh(geometry, material);
        scene.add(plane);

        renderer.render(scene, camera);

        return () => {
            renderer.dispose();
            plotRef.current.removeChild(renderer.domElement);
        };
    }, [dimensions]);

    // Update the texture when the array changes
    useEffect(() => {
        if (!array.length || !textureRef.current) return;

        const canvas = document.createElement('canvas');
        const rows = array.length;
        const cols = array[0].length;
        canvas.width = cols;
        canvas.height = rows;
        const ctx = canvas.getContext('2d');

        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]);

        array.forEach((row, rowIndex) => {
            row.forEach((value, colIndex) => {
                ctx.fillStyle = colorScale(value);
                ctx.fillRect(colIndex, rowIndex, 1, 1);
            });
        });

        const texture = textureRef.current;
        texture.image = canvas;
        texture.needsUpdate = true;

        // Re-render the scene with the updated texture
        if (rendererRef.current && sceneRef.current && cameraRef.current) {
            rendererRef.current.render(sceneRef.current, cameraRef.current);
        }
    }, [array]);

    return (
        <div className={`${width} h-full pb-8 relative`} ref={containerRef}>
            <div ref={plotRef} style={{ width: `${dimensions.width}px`, height: `${dimensions.height}px` }}></div>;
            <div className="absolute bottom-0 left-0 right-0 text-center text-md font-semibold">
                {title}
            </div>
        </div>
    );
}
 */



import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import * as d3 from 'd3';

const sampleArray = [
    [39, 42, 43, 38, 36, 34, 32, 33, 44, 49],
    [60, 60, 50, 30, 14, 6, 6, 8, 15, 18],
    [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    [25, 35, 45, 55, 65, 75, 85, 95, 105, 115],
    // Add more rows to simulate larger datasets
];

export default function ThreeJSHeatmap({ array = sampleArray, width = 'w-full', fixPlotHeightToParent=false, title='' }) {
    const plotRef = useRef(null);
    const containerRef = useRef(null);
    const [ dimensions, setDimensions ] = useState({width: 0, height: 0});

    useEffect(() =>{
        const resizeObserver = new ResizeObserver((entries) => {
            if (entries[0]) {
                const { width, height } = entries[0].contentRect;
                setDimensions({ width, height })
            }
        })
        if (containerRef.current) {
            resizeObserver.observe(containerRef.current);
        }
        return () => resizeObserver.disconnect();
    }, [])

    useEffect(() => {
        if (!array.length) return;

        // Set up Three.js scene
        const scene = new THREE.Scene();
        const camera = new THREE.OrthographicCamera(-dimensions.width / 2, dimensions.width / 2, dimensions.height / 2, -dimensions.height / 2, 0.1, 10);
        camera.position.z = 1;

        const renderer = new THREE.WebGLRenderer();
        renderer.setSize(dimensions.width, dimensions.height);
        plotRef.current.appendChild(renderer.domElement);

        // Create an off-screen canvas to draw the heatmap
        const canvas = document.createElement('canvas');
        const rows = array.length;
        const cols = array[0].length;
        canvas.width = cols;
        canvas.height = rows;
        const ctx = canvas.getContext('2d');

        // Create color scale
        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]);
        const myfillThreeJS = colorScale(0);

        // Draw heatmap to the canvas (1 pixel per data point)
        array.forEach((row, rowIndex) => {
            row.forEach((value, colIndex) => {
                ctx.fillStyle = colorScale(value);
                ctx.fillRect(colIndex, rowIndex, 1, 1);
            });
        });

        // Convert the canvas to a Three.js texture
        const texture = new THREE.CanvasTexture(canvas);
        texture.minFilter = THREE.LinearFilter; // Avoid pixelation on zoom
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.needsUpdate = true;

        // Create a plane and map the texture to it
        const geometry = new THREE.PlaneGeometry(dimensions.width, dimensions.height);
        const material = new THREE.MeshBasicMaterial({ map: texture, transparent: false });
        const plane = new THREE.Mesh(geometry, material);
        scene.add(plane);

        // Render the scene
        renderer.render(scene, camera);

        // Cleanup
        return () => {
            renderer.dispose();
            plotRef.current.removeChild(renderer.domElement);
        };
    }, [array, dimensions]);

    return (
        <div className={`${width} h-full pb-8 relative`} ref={containerRef}>
            <div ref={plotRef} style={{ width: `${dimensions.width}px`, height: `${dimensions.height}px` }}></div>;
            <div className="absolute bottom-0 left-0 right-0 text-center  text-md font-semibold">
                {title}
            </div>
        </div>
    )
}
