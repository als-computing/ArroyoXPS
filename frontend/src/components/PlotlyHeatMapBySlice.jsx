import React, { useRef, useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import Plotly from 'plotly.js-basic-dist'; // Import Plotly to use its API methods

const plotlyColorScales = ['Viridis', 'Plasma', 'Inferno', 'Magma', 'Cividis'];

export default function PlotlyHeatMapBySlice({
    initialArray = [],
    title = '',
    xAxisTitle = '',
    yAxisTitle = '',
    colorScale = 'Viridis',
    verticalScaleFactor = 0.1,
    width = 'w-full',
    showTicks = false,
    tickStep = 100,
    updateInterval = 1000, // Update interval in ms
    addSlice, // Function to provide the next slice of data
}) {
    const plotRef = useRef(null); // Reference to the Plotly plot
    const plotContainer = useRef(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    const arrayRef= useRef(initialArray);

    // Hook to update dimensions dynamically
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

    // Add new slice every interval
    useEffect(() => {
        const interval = setInterval(() => {
            const newSlice = addSlice(); // Get the new slice from the provided function
            if (newSlice) {
                extendHeatmap(newSlice);
            }
        }, updateInterval);

        return () => clearInterval(interval);
    }, [addSlice, updateInterval]);

    // Function to extend the heatmap data
    const extendHeatmap = (newSlice) => {
        if (!plotRef.current) return;

        const updatedArray = [newSlice, ...arrayRef.current.slice(0, arrayRef.current.length - 1)]; // Add the new slice on top
        arrayRef.current = updatedArray;
        // Use Plotly's extendTraces to update the plot
        console.log({updatedArray})
        Plotly.extendTraces(plotRef.current, {
            z: [newSlice],
        }, [0]);
    };

    return (
        <div className={`h-full ${width} rounded-b-md pb-6 flex-col content-end relative`} ref={plotContainer}>
            <Plot
                data={[
                    {
                        z: initialArray,
                        type: 'heatmap',
                        colorscale: colorScale,
                        zmin: 0,
                        zmax: 255,
                        showscale: false,
                    },
                ]}
                layout={{
                    title: {
                        text: '',
                    },
                    xaxis: {
                        title: xAxisTitle,
                    },
                    yaxis: {
                        title: yAxisTitle,
                        range: [0, arrayRef.current.length],
                        autorange: false,
                        tickmode: showTicks ? 'linear' : '',
                        tick0: 0,
                        dtick: showTicks ? tickStep : 10000,
                        showticklabels: showTicks,
                    },
                    autosize: true,
                    width: dimensions.width,
                    height: Math.max(arrayRef.current.length * verticalScaleFactor, 0),
                    margin: {
                        l: showTicks ? 50 : 10,
                        r: 10,
                        t: 0,
                        b: 0,
                    },
                }}
                config={{ responsive: true }}
                className="rounded-b-md"
                useResizeHandler
                onInitialized={(figure) => {
                    plotRef.current = figure;
                }}
                onUpdate={(figure) => {
                    plotRef.current = figure;
                }}
                ref={(plot) => {
                    if (plot && plot.getPlot) {
                        plotRef.current = plot.getPlot();
                    }
                }}
            />
            <div className="absolute bottom-0 left-0 right-0 text-center py-2 text-md font-semibold">
                {title}
            </div>
        </div>
    );
}
