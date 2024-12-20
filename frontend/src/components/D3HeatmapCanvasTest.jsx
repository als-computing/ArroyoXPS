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

    const resizeArrayWidth = (oldArray = [], newWidth) => {
        const oldWidth = oldArray[0].length;
        if (newWidth >= oldWidth) {
            // If the new width is greater than or equal to the old width, return the original array
            return oldArray.map(row => [...row]);
        }
    
        const scaleFactor = oldWidth / newWidth; // Factor to group and down-sample columns
        const newArray = oldArray.map(row => {
            const newRow = [];
            for (let i = 0; i < newWidth; i++) {
                // Calculate the range of indices to average
                const start = Math.floor(i * scaleFactor);
                const end = Math.min(Math.ceil((i + 1) * scaleFactor), oldWidth);
    
                // Compute the average value for the new column
                const average = row.slice(start, end).reduce((sum, val) => sum + val, 0) / (end - start);
                newRow.push(average);
            }
            return newRow;
        });
    
        return newArray;
    };

    const resizeArray = (oldArray, newWidth, newHeight) => {
        const oldWidth = oldArray[0].length;
        const oldHeight = oldArray.length;
        const newArray = [];
    
        // Calculate scale factors
        const widthScale = oldWidth / newWidth;
        const heightScale = oldHeight / newHeight;
    
        // Iterate over the new array dimensions
        for (let newY = 0; newY < newHeight; newY++) {
            const newRow = [];
            for (let newX = 0; newX < newWidth; newX++) {
                // Determine the region in the old array corresponding to the new cell
                const startX = Math.floor(newX * widthScale);
                const endX = Math.min(Math.ceil((newX + 1) * widthScale), oldWidth);
                const startY = Math.floor(newY * heightScale);
                const endY = Math.min(Math.ceil((newY + 1) * heightScale), oldHeight);
    
                // Average the values in the region
                let sum = 0;
                let count = 0;
                for (let oldY = startY; oldY < endY; oldY++) {
                    for (let oldX = startX; oldX < endX; oldX++) {
                        sum += oldArray[oldY][oldX];
                        count++;
                    }
                }
                const average = count > 0 ? sum / count : 0;
                newRow.push(average);
            }
            newArray.push(newRow);
        }
    
        return newArray;
    };

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
        //create a new array that is downsampled so that the width of new array does not exceed width of dimension.width
        const reducedArray = resizeArray(array, dimensions.width-1, dimensions.height);
        const rows = reducedArray.length;
        const cols = reducedArray[0].length;
        console.log('rows: ' + rows + 'cols: ' + cols )

        const cellWidth = Math.floor(dimensions.width / cols);
        // need to refactor this to support height based on scale factor
        const cellHeight = Math.floor(
            fixPlotHeightToParent ? dimensions.height / rows : (reducedArray.length * verticalScaleFactor) / rows
        );

        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]);
        const myfilld3 = colorScale(0);
        console.log({myfilld3});

        const canvas = canvasRef.current;
        canvas.width = dimensions.width; // Explicitly set canvas width
        canvas.height = fixPlotHeightToParent ? dimensions.height : reducedArray.length * verticalScaleFactor;

        const ctx = canvas.getContext('2d');
        //ctx.imageSmoothingEnabled = false; // Disable antialiasing for crisp rendering

        // Draw heatmap
        reducedArray.forEach((row, rowIndex) => {
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
    }, [array, dimensions]);

    return (
        <div className={`${width} flex-col h-full content-end pb-8 relative px-2`} ref={canvasContainerRef}>
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
