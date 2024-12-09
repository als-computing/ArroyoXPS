import Main from "./components/Main";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";

import { useAPXPS } from "./hooks/useAPXPS";
export default function App() {

  const {

  } = useAPXPS({});
  
    return (
      <div className="flex-col h-screen w-screen">
        <div className="h-16">
          <Header />
        </div>
        <div className="flex h-[calc(100vh-4rem)]">
          <Sidebar />
          <Main />
        </div>
      </div>
      
    )
}



