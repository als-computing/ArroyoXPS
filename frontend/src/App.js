import { useEffect } from 'react';

import Main from "./components/Main";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import SidebarItem from "./components/SidebarItem";
import Widget from "./components/Widget";
import PlotlyHeatMap from "./components/PlotlyHeatMap";
import PlotlyScatterSingle from "./components/PlotlyScatterSingle";
import PlotlyScatterMultiple from "./components/PlotlyScatterMultiple";
import ConsoleViewer from "./components/ConsoleViewer";
import Button from "./component_library/Button";
import TextField from "./component_library/TextField";
import Status from "./components/Status";
import Settings from "./components/Settings";
import FormContainer from "./component_library/FormContainer";

import { useAPXPS } from "./hooks/useAPXPS";
export default function App() {

  const {
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
    status,
    heatmapSettings,
    handleHeatmapSettingChange
  } = useAPXPS({});

  //Automatically start the websocket connection on page load
  useEffect(() => {
    startWebSocket();
    return closeWebSocket;
  }, []);
  
    return (
      <div className="flex-col h-screen w-screen">

        <div className="h-16 shadow-lg">
          <Header />
        </div>

        <div className="flex h-[calc(100vh-4rem)]">
          <Sidebar>
            <SidebarItem title="Websocket Connection">
              <li className="flex flex-col w-full items-center justify-center space-x-6 space-y-4">
                  <TextField text="Websocket URL" value={wsUrl} cb={setWsUrl} styles='w-64' />
                  {socketStatus === 'closed' ? <Button text="Start" cb={startWebSocket}/> : <Button text="stop" cb={closeWebSocket}/>}
              </li>
            </SidebarItem>
            <SidebarItem title='Scan Status'>
              <Status status={status}/>
            </SidebarItem>
            <SidebarItem title='Live Image Settings'>
              <Settings>
                <FormContainer inputs={heatmapSettings} handleInputChange={handleHeatmapSettingChange}/>
              </Settings>
            </SidebarItem>
          </Sidebar>

          <Main >
            <Widget title='Live Images' width='w-3/5' maxWidth='max-w-[1000px]' defaultHeight='h-full' maxHeight='max-h-[1400px]' expandedWidth='w-full'>
              <div className="w-full h-full overflow-auto flex">
                <PlotlyHeatMap array={rawArray} title='RAW' xAxisTitle='Averaged Vertical Intensity' yAxisTitle='Frame' width='w-1/3' verticalScaleFactor={heatmapSettings.scaleFactor.value} showTicks={heatmapSettings.showTicks.value}/>
                <PlotlyHeatMap array={vfftArray} title='VFFT' xAxisTitle='Averaged Vertical Intensity' yAxisTitle='Frame' width='w-1/3' verticalScaleFactor={heatmapSettings.scaleFactor.value} showTicks={heatmapSettings.showTicks.value}/>
                <PlotlyHeatMap array={ifftArray} title='IFFT' xAxisTitle='Averaged Vertical Intensity' yAxisTitle='Frame' width='w-1/3' verticalScaleFactor={heatmapSettings.scaleFactor.value} showTicks={heatmapSettings.showTicks.value}/>
              </div>
            </Widget>

            <div className='flex flex-wrap w-2/5'>
              <Widget title='Recent Fitted Peaks' width='w-full' maxWidth='max-w-[1000px]' defaultHeight='h-1/2' maxHeight='max-h-96'>
                  <PlotlyScatterSingle dataX={singlePeakData.x} dataY={singlePeakData.y} title='Recent Fitted Peaks' xAxisTitle='x' yAxisTitle='y'/>
              </Widget>
              <Widget title='Cumulative Fitted Peaks' width='w-full' maxWidth='max-w-[1000px]' defaultHeight='h-1/2' maxHeight='max-h-96'>
                  <PlotlyScatterMultiple data={allPeakData} title='Cumulative Fitted Peaks' xAxisTitle='x' yAxisTitle='y'/>
              </Widget>
            </div>
          </Main>
        </div>
      </div>
      
    )
}



