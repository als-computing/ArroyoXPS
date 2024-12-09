import React, { useRef, useEffect, useState } from 'react';
import Plot from 'react-plotly.js';

const sampleData = [
    {
        x: [1, 2, 3],
        y: [2, 6, 3],
        type: 'scatter',
        mode: 'lines+markers',
        marker: {color: 'red'},
    },
];

export default function PlotlyScatterMultiple({data=[{}]}) {
    const plotContainer = useRef(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    //const [ data, setData ] = useState(sampleData);

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


    return (
        <div className="h-full w-full pb-4" ref={plotContainer}>
            <Plot
                data={data}
                layout={{
                    title: `Sample Scatter`,
                    xaxis: { title: 'dist' },
                    yaxis: { title: 'height' },
                    autosize: true,
                    width: dimensions.width,
                    height: dimensions.height,
                }}
                config={{ responsive: true }}
            />
        </div>
    );
}