import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';

const sampleArray = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
];

export default function D3HeatmapSVG({ array = sampleArray }) {
    const svgRef = useRef(null);

    const margin = { top: 20, right: 20, bottom: 20, left: 20 };
    const minCellSize = 1; // Minimum size for each cell

    // Calculate SVG dimensions dynamically
    const cols = array.length > 0 ? array[0].length : 1;
    const rows = array.length > 0 ? array.length : 1;
    console.log('cols: ' + cols + 'rows: ' + rows);

    const cellWidth = Math.max(minCellSize, 600 / cols); // Scale cells to fit in 600px width
    const cellHeight = Math.max(minCellSize, 5 / rows); // Scale cells to fit in 600px height

    const width = cols * cellWidth + margin.left + margin.right;
    const height = rows * cellHeight + margin.top + margin.bottom;
    console.log ('width: ' + width + 'height: ' + height)

    useEffect(() => {
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove(); // Clear previous content

        if (array.length === 0) return;

        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]);

        // Create a group for the heatmap
        const g = svg
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        g.selectAll('rect')
            .data(array.flat())
            .enter()
            .append('rect')
            .attr('x', (_, i) => (i % cols) * cellWidth)
            .attr('y', (_, i) => Math.floor(i / cols) * cellHeight)
            .attr('width', cellWidth)
            .attr('height', cellHeight)
            .attr('fill', d => colorScale(d));
    }, [array, cellWidth, cellHeight, cols, rows]);

    return <svg ref={svgRef} width={width} height={height}></svg>;
}




/* import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';


const sampleArray = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
];
export default function SimpleD3HeatMap({array=sampleArray}) {
    const svgRef = useRef(null);
    var width = 0;
    var height = 0;

    if (array.length !== 0) {
        width = array.length * 3;
        height = array[0].length * 3; 
    }
    
    useEffect(() => {

        const margin = { top: 20, right: 20, bottom: 20, left: 20 };

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove(); // Clear previous content

        if (array.length === 0) {
            return
        }
        const rows = array.length;
        const cols = array[0].length;
        console.log('rows: ' + rows + 'cols: ' + cols);

        const cellWidth = (width - margin.left - margin.right) / cols;
        const cellHeight = (height - margin.top - margin.bottom) / rows;
        console.log({cellHeight});
        console.log({cellWidth});

        const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([0, 255]); //we know our data is Uint8, so we should set this once with useMemo and [0, 255]

        // Create a group for the heatmap
        const g = svg
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        g.selectAll('rect')
            .data(array.flat())
            .enter()
            .append('rect')
            .attr('x', (_, i) => (i % cols) * cellWidth)
            .attr('y', (_, i) => Math.floor(i / cols) * cellHeight)
            .attr('width', cellWidth)
            .attr('height', cellHeight)
            .attr('fill', d => colorScale(d));
    }, [array]);

    return <svg ref={svgRef} width={width} height={height}></svg>;
}
 */