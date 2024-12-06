export default function Widget({
    children,
    title='',
    icon='',
    defaultHeight='h-1/4',
    maxHeight='max-h-3/4',
    width='w-1/4',
    maxWidth='max-w-300px'
}) {
    return (
        <div className="bg-white shadow-md rounded-md">
            {/* Title */}
            <header className="bg-sky-950 h-10 flex rounded-t-md">
                <h3>{title}</h3>
            </header>

            {/* Main Body */}
            <div>
                {children}
            </div>
        </div>
    )
}