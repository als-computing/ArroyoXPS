import { Navigate, Route, Routes } from 'react-router-dom';

import Header from './components/Header';
import NavSidebar from './components/NavSidebar';
import HomePage from './pages/HomePage';
import LiveDataViewer from './pages/LiveDataViewer';
import ObservabilityPage from './pages/ObservabilityPage';
import { tailwindIcons, phosphorIcons } from './assets/icons';

const navItems = [
    {
        to: '/',
        label: 'Home',
        icon: tailwindIcons.home,
    },
    // {
    //     to: '/realtime',
    //     label: 'Realtime Viz',
    //     icon: phosphorIcons.chartPolar,
    // },
    {
        to: '/observability',
        label: 'Observability',
        icon: tailwindIcons.presentationChart,
    },
];

export default function App() {
    return (
        <div className="flex h-screen w-screen overflow-hidden">
            <NavSidebar navItems={navItems} />

            <div className="flex flex-col flex-grow overflow-hidden">
                <div className="h-16 shadow-lg flex-shrink-0">
                    <Header />
                </div>

                <div className="flex-grow overflow-hidden">
                    <Routes>
                        <Route path="/" element={<HomePage />} />
                        <Route path="/realtime" element={<LiveDataViewer />} />
                        <Route path="/observability" element={<ObservabilityPage />} />
                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </div>
            </div>
        </div>
    );
}
