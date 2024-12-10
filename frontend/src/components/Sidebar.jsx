export default function Sidebar({children}) {
    return (
        <aside className="bg-slate-200 min-w-64 flex-shrink-0 shadow-md h-full">
            {children}
        </aside>
    )
}