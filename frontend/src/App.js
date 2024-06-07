import { useEffect, useRef, useState } from 'react';
import Button from './component_library/Button';
import TextField from './component_library/TextField';
import Plot from 'react-plotly.js';

export default function App() {
    const canvasRef1 = useRef(null);
    const canvasRef2 = useRef(null);
    const canvasRef3 = useRef(null);

    //const [gaussianData1, setGaussianData1] = useState({ xValues: [], yValues: []}); //remove SUM
    const [gaussianData2, setGaussianData2] = useState([]);

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
          sum: () => {}, //setGaussianData1, //REMOVE SUM
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
            console.log({data});

            //Refactor for new JSON structure
/*             data = {
              raw: 'base64 encoded jpeg',
              vfft: 'base64 encoded jpeg',
              ifft: 'base64 encoded jpeg',
              sum: '[]', //will be array containing n number of plots
              fitted: '[]'  //array containing n number of plots
            }

            var sampleArray = [
              {"x": 235, "h": 433.3, "fwhm": 4334},
              {"x": 235, "h": 433.3, "fwhm": 4334}
              ]; */

              //NEW DATA STRUCTURE
            const imageNames = ['raw', 'vfft', 'ifft'];
            const plotNames = ['sum', 'fitted']
            for (const key in data) {
              if ( imageNames.includes(key) ) {
                //handle image update
                const image = new Image();
                image.onload = function () {
                  const canvas = canvases[key];
                  const context = canvas.getContext('2d');
                  context.clearRect(0, 0, canvas.width, canvas.height);
                  context.drawImage(image, 0, 0, canvas.width, canvas.height);
                };
                image.src = 'data:image/jpeg;base64,' + data[key];
              } else {
                if ( plotNames.includes(key)) {
                  //handle plot update
                  //define xValues and yValues which may contain
                  var allPlots = []
                  data[key].forEach((plot, index) => {
                    var singlePlot = {
                      x: [],
                      y: [],
                      mode: 'lines',
                      type: 'scatter',
                      name: 'peak ' + index
                    };
                    const x_peak = plot.x;
                    const y_peak = plot.h;
                    const fwhm = plot.fwhm;
        
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
                    singlePlot.x = xValues;
                    singlePlot.y = yValues;
                    allPlots.push(singlePlot);
                  })
                  const setGaussianDataFunction = setGaussianFunctions[key];
                  setGaussianDataFunction(allPlots);
                }
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
      /* {
        id: 'p1',
        title: 'Sum',
        data: gaussianData1
      }, */
      {
        id: 'p2',
        title: 'Fitted',
        data: gaussianData2
      }
    ]

    return (
      <main className="sm:w-full 2xl:w-3/4 min-h-screen border m-auto">
        <header className="w-full py-4">
          <h1 className="text-center font-medium text-5xl w-full">AP-XPS Visualization</h1>
        </header>
        <div name="canvas and plot container" className="flex flex-wrap justify-around">
          {canvasData.map((item) => {
            return (
              <section key={item.id} className="my-8 flex flex-col">
                <h2 className="text-center">{item.title}</h2>
                <canvas className='m-auto border shadow-md max-w-96' ref={item.canvasRef} width={item.width} height={item.height} />
              </section>
            )
          })}
          {plotData.map((item) => {
            return (
              <Plot
                key = {item.id}
                className="w-96 h-96 my-12 shadow-md border"
                data={item.data}
                layout={{ title: `Gaussian Distribution - ${item.title}`, xaxis: { title: 'X'}, yaxis: { title: 'Y' } }}
              />
            )
          })}
        </div>
        <div className="m-auto w-fit my-8">
          <div className="flex border border-slate-700 rounded-md items-center justify-center space-x-6 py-8 px-8 bg-slate-200 shadow-sm">
            <TextField text="Websocket URL" value={wsUrl} cb={setWsUrl} styles='w-72' />
            {socketStatus === 'closed' ? <Button text="Start" cb={startWebSocket}/> : <Button text="stop" cb={closeWebSocket}/>}
          </div>
        </div>
        <p className="text-red-500 text-center">{warningMessage}</p>
      </main>
    )
}




// old structure for data
{/* <Plot
key = {item.id}
className="w-96 h-96 my-12 shadow-md border"
data={[
  {
    x: item.data.xValues,
    y: item.data.yValues,
    mode: 'lines',
    type: 'scatter',
  },
]}
layout={{ title: `Gaussian Distribution - ${item.title}`, xaxis: { title: 'X'}, yaxis: { title: 'Y' } }}
/> */}