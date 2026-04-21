import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';

const hamburgerIcon = (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
    </svg>
);

function NavItem({ icon, label, to, isCollapsed }) {
    return (
        <NavLink
            to={to}
            title={isCollapsed ? label : undefined}
            className={({ isActive }) =>
                `w-full flex items-center gap-3 px-2 py-2.5 rounded-lg transition-colors duration-150 ${
                    isActive
                        ? 'bg-sky-700 text-white shadow-sm'
                        : 'text-slate-600 hover:bg-slate-200 hover:text-sky-900'
                } ${isCollapsed ? 'justify-center' : ''}`
            }
        >
            <div className="w-5 h-5 flex-shrink-0">{icon}</div>
            {!isCollapsed && (
                <span className="text-sm font-medium whitespace-nowrap">{label}</span>
            )}
        </NavLink>
    );
}

export default function NavSidebar({ navItems }) {
    const [isCollapsed, setIsCollapsed] = useState(false);

    return (
        <aside
            className={`bg-slate-100 border-r border-slate-200 flex-shrink-0 h-full flex flex-col transition-all duration-300 ${
                isCollapsed ? 'w-[52px]' : 'w-[200px]'
            }`}
        >
            <div className={`flex items-center border-b border-slate-200 p-2 ${isCollapsed ? 'justify-center' : 'justify-start'}`}>
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="p-1.5 rounded hover:bg-slate-200 focus:outline-none text-slate-500"
                >
                    {hamburgerIcon}
                </button>
            </div>

            <nav className="flex flex-col gap-1 p-2 flex-grow">
                {navItems.map((item) => (
                    <NavItem
                        key={item.to}
                        to={item.to}
                        icon={item.icon}
                        label={item.label}
                        isCollapsed={isCollapsed}
                    />
                ))}
            </nav>
        </aside>
    );
}
