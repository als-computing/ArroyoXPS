import React, { useRef, useEffect, useState } from 'react';
import Plot from 'react-plotly.js';

const plotlyColorScales = ['Viridis', 'Plasma', 'Inferno', 'Magma', 'Cividis']

export default function PlotlyHeatMap({array=[], title='', xAxisTitle='', yAxisTitle='', colorScale='Viridis', verticalScaleFactor=3500, minPlotHeight=200, width='w-full'}) {
    //console.log({array})
    const plotContainer = useRef(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

    const getScaledHeight = (containerHeight, arrayHeight) => {
        //return the new height as a ratio
        //console.log({containerHeight})
        //console.log({arrayHeight})
        const scaledPlotContainerHeight = (arrayHeight/verticalScaleFactor)*containerHeight + minPlotHeight;
        //console.log({scaledPlotContainerHeight})
        return scaledPlotContainerHeight;
    }

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

    const data = [
        {
            z: array,
            type: 'heatmap',
            colorscale: colorScale,
            zmin: 0, // Minimum value in the heatmap
            zmax: 255, // Maximum value in the heatmap
        },
    ];

    return (
        <div className={`h-full ${width} rounded-b-md pb-4 overflow-auto flex-col content-end`} ref={plotContainer}>
            <Plot
                data={data}
                layout={{
                    title: {title},
                    xaxis: { title: xAxisTitle },
                    yaxis: { title: yAxisTitle },
                    autosize: true,
                    width: dimensions.width,
                    height: getScaledHeight(dimensions.height, array.length),
                }}
                config={{ responsive: true }}
                className="rounded-b-md"
            />
        </div>
    );
}
    