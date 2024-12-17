import React, { useRef, useEffect } from 'react';
import * as PIXI from 'pixi.js';
import * as d3 from 'd3';

const sampleArray = [
    [39, 42, 43, 38, 36, 34, 32, 33, 44, 49],
    [60, 60, 50, 30, 14, 6, 6, 8, 15, 18],
    // ... (your large dataset here)
];

export default function PixiHeatmap({ array = sampleArray, width = 400 }) {
    const containerRef = useRef(null);
    var height = Math.max(array.length, 1);

    useEffect(() => {
        if (!array.length) return;

        const rows = array.length;
        const cols = array[0].length;

        const cellWidth = width / cols;
        const cellHeight = height / rows;

        // Create PixiJS application
        const app = new PIXI.Application({
            width,
            height,
            backgroundColor: 0xffffff, // Optional background color
            resolution:  1,
            antialias: true,
        });

        // Attach PixiJS canvas to the container
        containerRef.current.appendChild(app.view);

        // Create a color scale using d3
        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]);

        // Draw heatmap
        array.forEach((row, rowIndex) => {
            row.forEach((value, colIndex) => {
                const graphics = new PIXI.Graphics();
                graphics.beginFill(PIXI.utils.string2hex(colorScale(value)));
                graphics.drawRect(colIndex * cellWidth, rowIndex * cellHeight, cellWidth, cellHeight);
                graphics.endFill();
                app.stage.addChild(graphics);
            });
        });

        // Cleanup on unmount
        return () => {
            app.destroy(true, true);
        };
    }, [array, width, height]);

    return <div ref={containerRef} className="w-fit border border-slate-500"></div>;
}
