import React, { useRef, useEffect, useState } from 'react';
import Plot from 'react-plotly.js';

const plotlyColorScales = ['Viridis', 'Plasma', 'Inferno', 'Magma', 'Cividis'];


export default function PlotlyHeatMap({
    array = [], //2d array [[1, 2, 3], [2, 2 1]]
    title = '',
    xAxisTitle = '',
    yAxisTitle = '',
    colorScale = 'Viridis', //plotly compatible colorScale
    verticalScaleFactor = 0.1, // Adjusts the height of the plot. ex) A factor of 2 makes each row in the array take up 2 pixels
    width = 'w-full', //width of the container
    height='h-full', //height of the container
    showTicks = false,
    tickStep = 100,
    fixPlotHeightToParent=false, //locks the height of the plot to the height of the container, should not be set to True if preventInterpolation is on
    preventInterpolation=false, //restricts the maximum view of the plot so that it never exceeds a 1 pixel to 1 array element density (preventing interpolation and inaccurate display for sensitive data)
}) {
    const plotContainer = useRef(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 }); //applied to plot, not the container

    // Hook to update dimensions of plot dynamically
    useEffect(() => {
        const resizeObserver = new ResizeObserver((entries) => {
            if (entries[0]) {
                const { width, height } = entries[0].contentRect;
                setDimensions({ width, height });
            }
        });
        if (plotContainer.current) {
            resizeObserver.observe(plotContainer.current);
        }
        return () => resizeObserver.disconnect();
    }, []);

    const data = [
        {
            z: array,
            type: 'heatmap',
            colorscale: colorScale,
            zmin: 0,
            zmax: 255,
            showscale: false,
        },
    ];

    // Calculate the height based on the number of rows in the array
    const dynamicHeight = Math.max(array.length * verticalScaleFactor, 0); // Minimum height is 200px

    return (
        <div name="container" className={`${height} ${width} rounded-b-md pb-6 flex-col content-end relative`} ref={plotContainer}>
            <Plot
                data={data}
                layout={{
                    title: {
                        text: '',
                    },
                    xaxis: {
                        title: xAxisTitle,
                        //scaleanchor: "y", // Ensure squares remain proportional
                    },
                    yaxis: {
                        title: yAxisTitle,
                        range: [0, array.length], // Dynamically adjust y-axis range
                        autorange: false,
                        tickmode: showTicks ? 'linear' : '', // tick marks should only appear when
                        tick0: 0, // Starting tick
                        dtick: showTicks ? tickStep : 10000, // Tick step,
                        showticklabels: showTicks
                    },
                    autosize: true,
                    width: preventInterpolation ? Math.min(dimensions.width, array[0].length) : dimensions.width,
                    height: preventInterpolation ? Math.min(dimensions.height, array.length) : fixPlotHeightToParent ? dimensions.height : dynamicHeight, // Dynamically set height
                    margin: {
                        l: showTicks ? 50 : 0,
                        r: 0,
                        t: 0,
                        b: 0,
                    },
                }}
                config={{ responsive: true }}
                className="rounded-b-md"
            />
            <div className="absolute bottom-0 left-0 right-0 text-center  text-md font-semibold">
                {title}
            </div>
        </div>
    );
}