import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';

const sampleArray = [
    [39, 42, 43, 38, 36, 34, 32, 33, 44, 49],
    [60, 60, 50, 30, 14, 6, 6, 8, 15, 18],
    // ... (your large dataset here)
];

export default function D3HeatmapCanvas({ array = sampleArray, width = 200}) {
    const canvasRef = useRef(null);
    var height = Math.max(array.length, 0)

    useEffect(() => {
        if (!array.length) return;
        

        const rows = array.length;
        const cols = array[0].length;

        const cellWidth = width / cols;
        const cellHeight = height / rows;


        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]);

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        // Clear canvas before drawing
        ctx.clearRect(0, 0, width, height);

        // Draw heatmap
        array.forEach((row, rowIndex) => {
            row.forEach((value, colIndex) => {
                ctx.fillStyle = colorScale(value);
                ctx.fillRect(colIndex * cellWidth, rowIndex * cellHeight, cellWidth, cellHeight);
            });
        });

    }, [array, width, height]);

    return <div className='flex-col h-full content-end pb-8'>
            <canvas ref={canvasRef} width={width} height={height} className="w-fit border border-slate-500"></canvas>
        </div>;
}
