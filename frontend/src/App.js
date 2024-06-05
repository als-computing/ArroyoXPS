import { useEffect, useRef, useState } from 'react';
import Button from './component_library/Button';
import TextField from './component_library/TextField';
import Plot from 'react-plotly.js';

export default function App() {
    const canvasRef1 = useRef(null);
    const canvasRef2 = useRef(null);
    const canvasRef3 = useRef(null);

    const [gaussianData1, setGaussianData1] = useState({ xValues: [], yValues: []});
    const [gaussianData2, setGaussianData2] = useState({ xValues: [], yValues: []});

    const [socketStatus, setSocketStatus] = useState('closed');
    const [ wsUrl, setWsUrl ] = useState('ws://localhost:8001/simImages');
    const [ warningMessage, setWarningMessage ] = useState('');
    const ws = useRef(null);
    const [src, setSrc] = useState('');

    const startWebSocket = () => {
      setWarningMessage('');
        const canvases = {
          raw: canvasRef1.current,
          vfft: canvasRef2.current,
          ifft: canvasRef3.current
        }

        const setGaussianFunctions = {
          sum: setGaussianData1,
          fitted: setGaussianData2
        }


        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = (event) => {
            setSocketStatus('Open');
        }

        ws.current.onerror = function (error) {
          console.log("error with ws");
          console.log({error});
          alert("Unable to connect to websocket");
          setWarningMessage("Verify that the Python server is running, and that the port and path are correct");
        }
    
        ws.current.onmessage = function (event) {
            const data = JSON.parse(event.data);

            //Images
            if ("images" in data) {
              if (data.images.length > 0) {
                try {
                  data.images.forEach((imgData, index) => {
                    //display image data to canvas element
                    if (imgData.key in canvases) {
                      const image = new Image();
                      image.onload = function () {
                        const canvas = canvases[imgData.key];
                        const context = canvas.getContext('2d');
                        context.clearRect(0, 0, canvas.width, canvas.height);
                        context.drawImage(image, 0, 0, canvas.width, canvas.height);
                      };
                      image.src = 'data:image/jpeg;base64,' + imgData.image;
  
                      //create and display Gaussian Plot from FWHM data to Plotly
                    } else {
                      console.log("Matching canvas key was not found in WS data");
                      console.log("Received key :" + imgData.key);
                    }
                  })
                } catch (error) {
                  console.log("error in receiving message from websocket: " + error);
                }
              } else {
                console.log('Received empty image data');
              }
            }
            
            
            //Plots
            if ("plots" in data) {
              if (data.plots.length > 0) {
                data.plots.forEach((plot, index) => {
                  const x_peak = plot.terms.X;
                  const y_peak = plot.terms.H;
                  const fwhm = plot.terms.FWHM;
      
                  const sigma = fwhm / (2 * Math.sqrt(2 * Math.log(2)));
                  const xValues = [];
                  const yValues = [];
                  const x_min = x_peak - 5 * sigma;
                  const x_max = x_peak + 5 * sigma;
                  const step = (x_max - x_min) / 100;
      
                  for (let x = x_min; x <= x_max; x += step) {
                    const y = y_peak * Math.exp(-Math.pow(x - x_peak, 2) / (2 * Math.pow(sigma, 2)));
                    xValues.push(x);
                    yValues.push(y);
                  }
                  const setGaussianDataFunction = setGaussianFunctions[plot.key];
                  setGaussianDataFunction({ xValues, yValues });
                })

              }
            }
            

        };
    }

    const closeWebSocket = () => {
        try {
            ws.current.close();
        } catch (error) {
            console.log({error});
            return;
        }
        setSocketStatus('closed');
    }



    useEffect(() => {


    }, []);

    const canvasData = [
      {
        id: 1,
        title: "raw",
        canvasRef: canvasRef1,
        height: 512,
        width: 512
      },
      {
        id: 2,
        title: "vfft",
        canvasRef: canvasRef2,
        height: 512,
        width: 512
      },
      {
        id: 3,
        title: "ifft",
        canvasRef: canvasRef3,
        height: 512,
        width: 512
      },
    ];

    const plotData = [
      {
        id: 'p1',
        title: 'Sum',
        data: gaussianData1
      },
      {
        id: 'p2',
        title: 'Fitted',
        data: gaussianData2
      }
    ]

    return (
      <main className="max-w-screen-xl min-h-screen border m-auto">
        <header className="w-full py-4">
          <h1 className="text-center font-medium text-5xl w-full">AP-XPS Visualization</h1>
        </header>
        <div name="canvas container" className="flex flex-wrap justify-around">
          {canvasData.map((item) => {
            return (
              <section key={item.id} className="my-8 flex flex-col">
                <h2 className="text-center">{item.title}</h2>
                <canvas className='m-auto border shadow-md max-w-96' ref={item.canvasRef} width={item.width} height={item.height} />
              </section>
            )
          })}
        </div>
        <div name="plot container" className='flex flex-wrap justify-around'>
          {plotData.map((item) => {
            return (
              <Plot
                key = {item.id}
                className="max-w-96 max-h-96 my-8 h-auto shadow-md border"
                data={[
                  {
                    x: item.data.xValues,
                    y: item.data.yValues,
                    mode: 'lines',
                    type: 'scatter',
                  },
                ]}
                layout={{ title: `Gaussian Distribution - ${item.title}`, xaxis: { title: 'X' }, yaxis: { title: 'Y' } }}
              />
            )
          })}
        </div>
        <div className="m-auto w-fit mt-8">
          <div className="flex border border-slate-700 rounded-md items-center justify-center space-x-6 py-8 px-8 bg-slate-200 shadow-sm">
            <TextField text="Websocket URL" value={wsUrl} cb={setWsUrl} styles='w-72' />
            {socketStatus === 'closed' ? <Button text="Start" cb={startWebSocket}/> : <Button text="stop" cb={closeWebSocket}/>}
          </div>
        </div>
        <p className="text-red-500 text-center">{warningMessage}</p>
      </main>
    )
}
