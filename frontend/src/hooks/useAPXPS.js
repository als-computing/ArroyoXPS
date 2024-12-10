import { useEffect, useRef, useState } from 'react';

import msgpack from 'msgpack-lite';
import TextField from '../component_library/TextField';
import { getWsUrl } from '../utils/connectionHelper'

export const useAPXPS = ({}) => {

    const [ messages, setMessages ] = useState([]);


    const [ rawArray, setRawArray ] = useState([]);
    const [ vfftArray, setVfftArray ] = useState([]);
    const [ ifftArray, setIfftArray ] = useState([]);

    const [ singlePeakData, setSinglePeakData ] = useState({x:[], y:[]});
    const [ allPeakData, setAllPeakData ] = useState([]);

    const [ status, setStatus ] = useState({scan: 'N/A', websocket: 'N/A'})

    const frameNumber = useRef(null);
    


    const defaultWsUrl = getWsUrl();
    const [socketStatus, setSocketStatus] = useState('closed');
    const [ wsUrl, setWsUrl ] = useState(defaultWsUrl);
    const [frameCount, setFrameCount ] = useState('');
    const [timeStamp, setTimeStamp] = useState('');
    const [ warningMessage, setWarningMessage ] = useState('');
    const ws = useRef(null);

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
            }
            //log keys
            var keyList = '';
            for (const key in newMessage) {
                keyList = keyList.concat(', ', key);
            };

            setMessages((prevMessages) => [...prevMessages, keyList]);

            if ('frame_number' in newMessage) {
                //console.log({newMessage})
                frameNumber.current = newMessage.frame_number;
            }
            
            //handle fitted data parameters for line plots
            if ('fitted' in newMessage) {
                const fittedData = JSON.parse(newMessage.fitted);
                console.log({fittedData})
                processPeakData(fittedData[1], setSinglePeakData, updateCumulativePlot)
            }

            //handle heatmap data
            if ('raw' in newMessage) {
                //console.log({newMessage})
                //send in height as width and vice versa until height/width issues fixed
                processArrayData(newMessage.raw,  newMessage.height, newMessage.width, setRawArray)
            }
            if ('vfft' in newMessage) {
                //console.log({newMessage})
                //send in height as width and vice versa until height/width issues fixed
                processArrayData(newMessage.vfft, newMessage.height,  newMessage.width, setVfftArray)
            }
            if ('ifft' in newMessage) {
                //console.log({newMessage})
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

        const y_peak = data.h;
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

        //update state
        singlePlotCallback(singlePlot);
        multiPlotCallback(singlePlot);
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

    const updateCumulativePlot = (singlePlot) => {
       //console.log({frameNumber})
      setAllPeakData((data) => {
        var oldArrayData = Array.from(data);
        var newArrayData = [];
        let totalFrames = oldArrayData.length;
        let colorNumber = 255; //the lightest color for the oldest entries

        //TO DO: refactor this if its slowing the app down
        oldArrayData.forEach((plot, index) => {
            let colorWeight = (totalFrames - index) / totalFrames * colorNumber; //scale color based on index relative to total frames
            plot.line = {
                color: `rgb(${colorWeight}, ${colorWeight}, ${colorWeight})`,
                width: 1,
            };
            newArrayData.push(plot);
        })
        const newestData = {
            x: singlePlot.x,
            y: singlePlot.y,
            line: {
                color: 'rgb(0, 94, 245)',
                width: 1,
            },
            name: `frame ${frameNumber.current ? frameNumber.current : 'NA'}`
        }
        return [...newArrayData, newestData];
      })
    };

    const closeWebSocket = () => {
        try {
            ws.current.close();
        } catch (error) {
            console.log({error});
            return;
        }
        setSocketStatus('closed');
    };


    return {
        rawArray,
        vfftArray,
        ifftArray,
        singlePeakData,
        allPeakData,
        messages,
        wsUrl,
        setWsUrl,
        frameNumber,
        socketStatus,
        startWebSocket,
        closeWebSocket,
        warningMessage,
        status
    }
}