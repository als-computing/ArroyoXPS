export default function ConsoleViewer({messages=[]}){
    return (
        <div className="w-full overflow-y-auto">
            {messages.map((message, index) => {
                <li key={index}>
                    <p>{JSON.stringify(message)}</p>
                </li>
            })}
        </div>
    )
}