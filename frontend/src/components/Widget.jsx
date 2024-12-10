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
        <div className={` p-2 rounded-md ${width} ${defaultHeight} ${maxHeight} ${maxWidth}`}>
            <div className="w-full h-full shadow-md bg-white rounded-md">
                {/* Title */}
                <header className="bg-sky-950 h-10 flex justify-start items-center rounded-t-md">
                    <h3 className="text-white text-lg font-semibold pl-4">{title}</h3>
                </header>

                {/* Main Body */}
                <div className="h-[calc(100%-2.5rem)] rounded-b-md flex w-full">
                    {children}
                </div>
            </div>
        </div>
    )
}