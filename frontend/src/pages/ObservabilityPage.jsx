import { useState } from 'react';

const TABS = [
    { id: 'grafana',    label: 'Grafana',    src: 'http://localhost:3000/d/arroyopy-metrics/arroyopy-metrics?orgId=1&kiosk&refresh=5s' },
    { id: 'prometheus', label: 'Prometheus', src: 'http://localhost:9091/targets' },
    { id: 'jaeger',     label: 'Jaeger',     src: 'http://localhost:16686/search?service=arroyopy-demo&limit=20' },
];

export default function ObservabilityPage() {
    const [activeTab, setActiveTab] = useState('grafana');

    return (
        <div className="h-full w-full flex flex-col overflow-hidden">
            {/* Tab bar */}
            <div className="flex-shrink-0 flex border-b border-slate-200 bg-slate-100">
                {TABS.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === tab.id
                                ? 'border-sky-600 text-sky-700 bg-white'
                                : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-200'
                        }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Iframes — all mounted, only active one visible, preserves state on tab switch */}
            {TABS.map((tab) => (
                <iframe
                    key={tab.id}
                    src={tab.src}
                    title={tab.label}
                    className={`flex-grow w-full border-0 ${activeTab === tab.id ? 'block' : 'hidden'}`}
                    allow="fullscreen"
                />
            ))}
        </div>
    );
}
