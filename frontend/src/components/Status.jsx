export default function Status({status={websocket:'disconnected', scan:'started'}}) {
    //this component will receive messages
    return (
        <div className="flex-col w-full list-none">
            {Object.keys(status).map((key) => {
                return (
                    <li key={key} className="flex justify-start items-center">
                        <div className={`rounded-full aspect-square w-4 h-4 animate-pulse border border-slate-300 mr-3 ${status[key].startsWith('connected') || status[key].startsWith('started') ? 'bg-green-500' : 'bg-red-400'}`}></div>
                        <p>{`${key}: ${status[key]}`}</p>
                    </li>
                )
            })}
        </div>
    )
}