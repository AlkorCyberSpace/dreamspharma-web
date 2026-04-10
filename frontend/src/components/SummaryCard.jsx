import React from "react";

function SummaryCard({ title, value, icon, bgClass, textClass, iconClass, blobColor1, blobColor2 }) {
    return (
        <div className={`relative overflow-hidden rounded-2xl p-6 ${bgClass} flex-1 min-h-[105px] shadow-[0_4px_20px_rgba(0,0,0,0.03)] border border-white/40`}>
            {/* Decorative Blobs */}
            <div className={`absolute top-[-80%] right-[1%] w-[150px] h-[140px] rounded-full ${blobColor1} opacity-40 pointer-events-none`} />
            <div className={`absolute top-[-60%] right-[-12%] w-[140px] h-[140px] rounded-full ${blobColor2} opacity-30 pointer-events-none`} />

            <div className="relative z-10 flex flex-col h-full justify-between">
                <div className={`text-4xl font-bold tracking-tight ${textClass}`}>{value}</div>
                <div className={`text-[12px] font-bold flex items-center gap-2 ${textClass} opacity-90`}>
                    {title}
                    <span className={iconClass}>{icon}</span>
                </div>
            </div>
        </div>
    );
}

export default SummaryCard;
