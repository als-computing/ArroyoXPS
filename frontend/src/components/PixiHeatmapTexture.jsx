import React, { useRef, useEffect } from 'react';
import * as PIXI from 'pixi.js';
import * as d3 from 'd3';

const sampleArray = [
    [39, 42, 43, 38, 36, 34, 32, 33, 44, 49],
    [60, 60, 50, 30, 14, 6, 6, 8, 15, 18],
    // Add your large dataset here
];

export default function PixiHeatmapTexture({ array = sampleArray, width = 400, height = 800 }) {
    const containerRef = useRef(null);

    useEffect(() => {
        if (!array.length) return;

        const rows = array.length;
        const cols = array[0].length;

        const cellWidth = Math.floor(width / cols);
        const cellHeight = Math.floor(height / rows);

        // Create PixiJS application
        const app = new PIXI.Application({
            width,
            height,
            backgroundColor: 0xffffff,
            resolution: 1,
            antialias: true,
        });

        containerRef.current.appendChild(app.view);

        // Create an off-screen canvas
        const offscreenCanvas = document.createElement('canvas');
        offscreenCanvas.width = cols;
        offscreenCanvas.height = rows;

        const ctx = offscreenCanvas.getContext('2d');

        // Create color scale
        const flatArray = array.flat();
        const minVal = Math.min(...flatArray);
        const maxVal = Math.max(...flatArray);
        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([minVal, maxVal]);

        // Draw heatmap onto off-screen canvas (1 pixel per cell)
        array.forEach((row, rowIndex) => {
            row.forEach((value, colIndex) => {
                ctx.fillStyle = colorScale(value);
                ctx.fillRect(colIndex, rowIndex, 1, 1);
            });
        });

        // Convert the canvas to a texture
        const texture = PIXI.Texture.from(offscreenCanvas);
        const sprite = new PIXI.Sprite(texture);

        // Scale the texture to fit the desired dimensions
        sprite.width = width;
        sprite.height = height;

        app.stage.addChild(sprite);

        // Cleanup on unmount
        return () => {
            app.destroy(true, true);
        };
    }, [array, width, height]);

    return <div ref={containerRef} className="w-fit border border-slate-500"></div>;
}
