import React, { useRef, useEffect, useState } from 'react';
import Plot from 'react-plotly.js';

const plotlyColorScales = ['Viridis', 'Plasma', 'Inferno', 'Magma', 'Cividis']

export default function PlotlyHeatMap({array=[], title='', xAxisTitle='', yAxisTitle='', colorScale='Viridis'}) {
    //console.log({array})
    const plotContainer = useRef(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

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
        <div className="h-full w-full rounded-b-md pb-4" ref={plotContainer}>
            <Plot
                data={data}
                layout={{
                    title: {title},
                    xaxis: { title: xAxisTitle },
                    yaxis: { title: yAxisTitle },
                    autosize: true,
                    width: dimensions.width,
                    height: dimensions.height,
                }}
                config={{ responsive: true }}
                className="rounded-b-md"
            />
        </div>
    );
}
    