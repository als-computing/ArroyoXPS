/* import Plot from 'react-plotly.js';
export default function PlotlyHeatMap() {
    var data = [
        {
          z: [[1, 20, 30], [20, 1, 60], [30, 60, 1]],
          type: 'heatmap'
        }
      ];
    return (
        <div className='h-full w-full'>
            <Plot
                type="heatmap"
                className="w-full h-full"
                data={data}
                layout={{title: `sample heatmap`, xaxis: { title: 'Average'}, yaxis: { title: 'Time' } }}
            />
        </div>
    )
} */

    import React, { useRef, useEffect, useState } from 'react';
    import Plot from 'react-plotly.js';
    
    export default function PlotlyHeatMap({array=[], title='', xAxisTitle='', yAxisTitle=''}) {
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
    