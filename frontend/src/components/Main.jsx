import { useEffect, useRef, useState } from 'react';
import Button from '../component_library/Button';
import msgpack from 'msgpack-lite';
import TextField from '../component_library/TextField';
import Plot from 'react-plotly.js';
import dayjs from 'dayjs';
import Widget from './Widget';
import ConsoleViewer from './ConsoleViewer';
//import msgpack from 'msgpack-lite';
import PlotlyHeatMap from './PlotlyHeatMap';
import PlotlyScatterSingle from './PlotlyScatterSingle';

import { useAPXPS } from '../hooks/useAPXPS';

export default function Main() {

    const {

    } = useAPXPS({});

    const [ messages, setMessages ] = useState([]);

    const canvasRef1 = useRef(null);
    const canvasRef2 = useRef(null);
    const canvasRef3 = useRef(null);

    const [ rawArray, setRawArray ] = useState([]);
    const [ vfftArray, setVfftArray ] = useState([]);
    const [ ifftArray, setIfftArray ] = useState([]);

    const [ singlePeakData, setSinglePeakData ] = useState({x:[], y:[]});
    

    

    const [gaussianData1, setGaussianData1] = useState([]); //persistent values
    const [gaussianData2, setGaussianData2] = useState([]); //fitted values

    const [socketStatus, setSocketStatus] = useState('closed');
    const [ wsUrl, setWsUrl ] = useState('ws://localhost:8001/simImages');
    const [frameCount, setFrameCount ] = useState('');
    const [timeStamp, setTimeStamp] = useState('');
    const [ warningMessage, setWarningMessage ] = useState('');
    const ws = useRef(null);

    const defaultCanvasHeight = 512;

    const handleNewWebsocketMessages = async (event) => {
        //process with webpack and set to messages.
        try {
            let newMessage;

            if (event.data instanceof Blob) {
                // Convert Blob to ArrayBuffer for binary processing
                const arrayBuffer = await event.data.arrayBuffer();
                newMessage = msgpack.decode(new Uint8Array(arrayBuffer));
            } else if (event.data instanceof ArrayBuffer) {
                // Process ArrayBuffer directly
                newMessage = msgpack.decode(new Uint8Array(event.data));
            } else {
                // Assume JSON string for non-binary data
                newMessage = JSON.parse(event.data);
                console.log({newMessage});
                console.log(newMessage.fitted);
                const fittedData = JSON.parse(newMessage.fitted);
                console.log({fittedData})
                processPeakData(fittedData[1], setSinglePeakData)
                //handle fitted data
            }
            //create a message with the keys provided.
            // Update the messages state with the new message
            //console.log({newMessage});
            var keyList = '';
            for (const key in newMessage) {
                //console.log(key);
                keyList = keyList.concat(', ', key);
                //console.log(keyList);
            };
            //console.log(keyList)
            setMessages((prevMessages) => [...prevMessages, keyList]);

            //handle raw array so it can render in heatmap
            if ('raw' in newMessage) {
                console.log({newMessage})
                //send in height as width and vice versa until height/width issues fixed
                processArrayData(newMessage.raw,  newMessage.height, newMessage.width, setRawArray)
            }
            if ('vfft' in newMessage) {
                console.log({newMessage})
                //send in height as width and vice versa until height/width issues fixed
                processArrayData(newMessage.vfft, newMessage.height,  newMessage.width, setVfftArray)
            }
            if ('ifft' in newMessage) {
                console.log({newMessage})
                //send in height as width and vice versa until height/width issues fixed
                processArrayData(newMessage.ifft, newMessage.height, newMessage.width, setIfftArray)
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    }

    const processArrayData = (data=[], width, height, cb) => {
        //convert a single dimensional array data into width and height to make suitable for heatmap
        const newData = [];
        for (let i = 0; i < height; i++) {
            newData.push(data.slice(i * width, (i + 1) * width));
        }
        cb(newData);
    };

    //to do: revise data to be an object instead of array if only a single plot is needed
    const processPeakData = (data={x:0, h:0, fwhm: 0}, singlePlotCallback=()=>{}, multiPlotCallback=()=>{}) => {
        //process the json message, get data, put data into both the single plot and the cumulativeplot

          //to do: refactor this to accept the newest plot data
/*           const x_peak = plot.x;
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
          singlePlot.y = yValues; */


        const y_peak = data.y;
        const x_peak = data.x;

        // Calculate sigma and define x range
        const sigma = data.fwhm / (2 * Math.sqrt(2 * Math.log(2)));
        const x_min = x_peak - 5 * sigma;
        const x_max = x_peak + 5 * sigma;
        const step = (x_max - x_min) / 100;

        // Generate x and y values for the single plot
        const xValues = [];
        const yValues = [];
        for (let x = x_min; x <= x_max; x += step) {
            const y = y_peak * Math.exp(-Math.pow(x - x_peak, 2) / (2 * Math.pow(sigma, 2)));
            xValues.push(x);
            yValues.push(y);
        }

        // Create single plot object
        const singlePlot = { x: xValues, y: yValues };
        singlePlotCallback(singlePlot); // Pass single plot data to the callback
        console.log({singlePlot})
      

          //singlePlotCallback(singlePlot);
         // multiPlotCallback()
    }



    const startWebSocket = () => {
        setWarningMessage('');

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
            handleNewWebsocketMessages(event);
        };
    };

    const updateCumulativePlot = (newPlot) => {
      //append the newest plot data to the existing data for the cumulative plot
      setGaussianData1((data) => {
        //copy by value to be safe
        var oldArrayData = Array.from(data);
        var newArrayData = [];
        oldArrayData.forEach((plot, index) => {
          plot.line = {
            color: 'rgb(199, 199, 199)',
            width: 1,
          };
          plot.name = `frame ${index}`;
          newArrayData.push(plot);
        })
        return [...newArrayData, ...newPlot];
      })
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
        height: defaultCanvasHeight,
        width: 512
      },
      {
        id: 2,
        title: "vfft",
        canvasRef: canvasRef2,
        height: defaultCanvasHeight,
        width: 512
      },
      {
        id: 3,
        title: "ifft",
        canvasRef: canvasRef3,
        height: defaultCanvasHeight,
        width: 512
      },
    ];

    const plotData = [
      {
        id: 'p2',
        title: 'Fitted Peaks',
        data: gaussianData2
      },
      {
        id: 'p1',
        title: 'Fitted peaks - Cumulative',
        data: gaussianData1
      },
    ];

    //to do: make main render children, lift up everything into app.js
    return (
        <main className="bg-slate-500 h-full flex-grow overflow-y-auto flex flex-wrap">

            {/* TO DO: lift this all up into app.js*/}
            <Widget title='Raw' width='w-1/3' maxWidth='' defaultHeight='h-1/2' maxHeight=''>
                <PlotlyHeatMap array={rawArray} title='RAW' xAxisTitle='Averaged Vertical Intensity' yAxisTitle='Frame'/>
            </Widget>
            <Widget title='VFFT' width='w-1/3' maxWidth='' defaultHeight='h-1/2' maxHeight=''>
                <PlotlyHeatMap array={vfftArray} title='VFFT' xAxisTitle='Averaged Vertical Intensity' yAxisTitle='Frame'/>
            </Widget>
            <Widget title='IFFT' width='w-1/3' maxWidth='' defaultHeight='h-1/2' maxHeight=''>
                <PlotlyHeatMap array={ifftArray} title='IFFT' xAxisTitle='Averaged Vertical Intensity' yAxisTitle='Frame'/>
            </Widget>

            <Widget title='Fitted Peaks' width='w-1/2' maxWidth='' defaultHeight='h-1/4' maxHeight=''>
                <PlotlyScatterSingle dataX={singlePeakData.x} dataY={singlePeakData.y} />
            </Widget>
            <Widget title='Fitted Peaks' width='w-1/2' maxWidth='' defaultHeight='h-1/4' maxHeight=''>
                <PlotlyScatterSingle dataX={[1, 2, 3]} dataY={[1, 2, 3]} />
            </Widget>
            <Widget title='Websocket Message Keys' width='w-[500px]' defaultHeight='h-[500px]'>
                <ConsoleViewer messages={messages}/>
            </Widget>







            {/* TO DO: put this into the left sidebar*/}
            <div className="m-auto w-fit my-8">
                <div className="flex border border-slate-700 rounded-md items-center justify-center space-x-6 py-8 px-8 bg-slate-200 shadow-sm">
                    <TextField text="Websocket URL" value={wsUrl} cb={setWsUrl} styles='w-72' />
                    {socketStatus === 'closed' ? <Button text="Start" cb={startWebSocket}/> : <Button text="stop" cb={closeWebSocket}/>}
                </div>
            </div>
            
           
      </main>
    )
}