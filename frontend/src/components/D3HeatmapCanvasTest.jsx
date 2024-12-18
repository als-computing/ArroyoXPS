import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';

const sampleArray = [
    [39, 42, 43, 38, 36, 34, 32, 33, 44, 49],
    [60, 60, 50, 30, 14, 6, 6, 8, 15, 18],
    // ... (your large dataset here)
];

export default function D3HeatmapCanvasTest({
    array = sampleArray,
    title = '',
    width = 'w-full',
    verticalScaleFactor = 1,
    fixPlotHeightToParent = false,
}) {
    const canvasRef = useRef(null);
    const canvasContainerRef = useRef(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

    // Hook to update dimensions dynamically
    useEffect(() => {
        const resizeObserver = new ResizeObserver((entries) => {
            if (entries[0]) {
                const { width, height } = entries[0].contentRect;
                setDimensions({ width, height });
            }
        });
        if (canvasContainerRef.current) {
            resizeObserver.observe(canvasContainerRef.current);
        }
        return () => resizeObserver.disconnect();
    }, []);

    useEffect(() => {
        if (!array.length || dimensions.width === 0) return;

        const rows = array.length;
        const cols = array[0].length;

        const cellWidth = Math.floor(dimensions.width / cols);
        const cellHeight = Math.floor(
            fixPlotHeightToParent ? dimensions.height / rows : (array.length * verticalScaleFactor) / rows
        );

        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]);
        const myfilld3 = colorScale(0);
        console.log({myfilld3});

        const canvas = canvasRef.current;
        canvas.width = dimensions.width; // Explicitly set canvas width
        canvas.height = fixPlotHeightToParent ? dimensions.height : array.length * verticalScaleFactor;

        const ctx = canvas.getContext('2d');
        //ctx.imageSmoothingEnabled = false; // Disable antialiasing for crisp rendering

        // Draw heatmap
        array.forEach((row, rowIndex) => {
            row.forEach((value, colIndex) => {
                ctx.fillStyle = colorScale(value);
                ctx.fillRect(
                    Math.round(colIndex * cellWidth),
                    Math.round(rowIndex * cellHeight),
                    Math.ceil(cellWidth),
                    Math.ceil(cellHeight)
                );
            });
        });
    }, [array, dimensions, fixPlotHeightToParent, verticalScaleFactor]);

    return (
        <div className={`${width} flex-col h-full content-end pb-8 relative`} ref={canvasContainerRef}>
            <canvas
                ref={canvasRef}
                className="w-fit border border-slate-500"
                style={{ display: 'block' }}
            ></canvas>
            <div className="absolute bottom-0 left-0 right-0 text-center text-md font-semibold">
                {title}
            </div>
        </div>
    );
}
