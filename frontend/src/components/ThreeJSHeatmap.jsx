import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import * as d3 from 'd3';

const sampleArray = [
    [39, 42, 43, 38, 36, 34, 32, 33, 44, 49],
    [60, 60, 50, 30, 14, 6, 6, 8, 15, 18],
    [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    [25, 35, 45, 55, 65, 75, 85, 95, 105, 115],
    // Add more rows to simulate larger datasets
];

export default function ThreeJSHeatmap({ array = sampleArray, width = 400, height = 800 }) {
    const containerRef = useRef(null);

    useEffect(() => {
        if (!array.length) return;

        // Set up Three.js scene
        const scene = new THREE.Scene();
        const camera = new THREE.OrthographicCamera(-width / 2, width / 2, height / 2, -height / 2, 0.1, 10);
        camera.position.z = 1;

        const renderer = new THREE.WebGLRenderer();
        renderer.setSize(width, height);
        //renderer.outputEncoding = THREE.sRGBEncoding; // Enable sRGB encoding for gamma correction
        renderer.toneMapping = THREE.ACESFilmicToneMapping; // Improved tone mapping
        renderer.toneMappingExposure = 1.2; // Adjust exposure for better brightness
        containerRef.current.appendChild(renderer.domElement);

        // Create an off-screen canvas to draw the heatmap
        const canvas = document.createElement('canvas');
        const rows = array.length;
        const cols = array[0].length;
        canvas.width = cols;
        canvas.height = rows;
        const ctx = canvas.getContext('2d');

        // Create color scale
        const flatArray = array.flat();
        const minVal = Math.min(...flatArray);
        const maxVal = Math.max(...flatArray);
        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]);

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
        //texture.encoding = THREE.sRGBEncoding;
        texture.needsUpdate = true;

        // Create a plane and map the texture to it
        const geometry = new THREE.PlaneGeometry(width, height);
        const material = new THREE.MeshBasicMaterial({ map: texture, transparent: false });
        const plane = new THREE.Mesh(geometry, material);
        scene.add(plane);

        // Render the scene
        renderer.render(scene, camera);

        // Cleanup
        return () => {
            renderer.dispose();
            containerRef.current.removeChild(renderer.domElement);
        };
    }, [array, width, height]);

    return <div ref={containerRef} style={{ width: `${width}px`, height: `${height}px` }}></div>;
}
