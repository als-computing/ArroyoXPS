export default function Widget({
    children,
    title='',
    icon='',
    defaultHeight='h-1/4',
    maxHeight='max-h-3/4',
    width='w-1/4',
    maxWidth='max-w-full'
}) {
    return (
        <div className={`bg-white shadow-md rounded-md ${width} ${defaultHeight} ${maxHeight} ${maxWidth}`}>
            {/* Title */}
            <header className="bg-sky-950 h-10 flex justify-start items-center rounded-t-md">
                <h3 className="text-white text-md font-semibold pl-4">{title}</h3>
            </header>

            {/* Main Body */}
            <div>
                {children}
            </div>
        </div>
    )
}