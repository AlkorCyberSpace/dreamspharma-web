// import React, { useState } from "react";
// import { Package, AlertTriangle, Zap, Clock, ChevronRight } from "lucide-react";

// const InventoryInsights = () => {
//     const [activeTab, setActiveTab] = useState("expiring");

//     const inventoryData = {
//         expiring: [
//             { id: 1, name: "Paracetamol 500mg", stock: 450, status: "15 Days", type: "expiry" },
//             { id: 2, name: "Amoxicillin 250mg", stock: 120, status: "22 Days", type: "expiry" },
//             { id: 3, name: "Cetirizine Syrup", stock: 85, status: "8 Days", type: "expiry" },
//             { id: 4, name: "Ibuprofen 400mg", stock: 300, status: "30 Days", type: "expiry" },
//         ],
//         oos: [
//             { id: 1, name: "Insulin Glargine", stock: 0, status: "Critical", type: "stock" },
//             { id: 2, name: "Metformin 500mg", stock: 0, status: "Critical", type: "stock" },
//             { id: 3, name: "Vicks Vaporub 50g", stock: 0, status: "Refill Needed", type: "stock" },
//         ],
//         fast: [
//             { id: 1, name: "Dolo 650mg", stock: 1200, status: "High Demand", type: "velocity" },
//             { id: 2, name: "Azithromycin 500mg", stock: 800, status: "Fast Moving", type: "velocity" },
//             { id: 3, name: "Pantoprazole 40mg", stock: 950, status: "Steady", type: "velocity" },
//         ],
//         slow: [
//             { id: 1, name: "Rare-Cold Suspension", stock: 15, status: "Low Turn", type: "velocity" },
//             { id: 2, name: "Spec-Cream 30g", stock: 8, status: "Stagnant", type: "velocity" },
//         ]
//     };

//     const tabs = [
//         { id: "expiring", label: "Expiring Soon", icon: Clock, color: "text-amber-500", bg: "bg-amber-50" },
//         { id: "oos", label: "Out of Stock", icon: AlertTriangle, color: "text-red-500", bg: "bg-red-50" },
//         { id: "fast", label: "Fast Moving", icon: Zap, color: "text-emerald-500", bg: "bg-emerald-50" },
//         { id: "slow", label: "Slow Moving", icon: Package, color: "text-blue-500", bg: "bg-blue-50" },
//     ];

//     return (
//         <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col h-full min-h-[300px]">
//             <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
//                 <div>
//                     <h3 className="text-lg font-bold text-gray-800 tracking-tight">Inventory Insights</h3>
//                 </div>
                
//                 <div className="flex bg-gray-50 p-1 rounded-xl border border-gray-100">
//                     {tabs.map((tab) => (
//                         <button
//                             key={tab.id}
//                             onClick={() => setActiveTab(tab.id)}
//                             className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all ${
//                                 activeTab === tab.id 
//                                 ? "bg-white text-[#127690] shadow-sm ring-1 ring-black/5" 
//                                 : "text-gray-400 hover:text-gray-600"
//                             }`}
//                         >
//                             <tab.icon size={14} className={activeTab === tab.id ? tab.color : ""} />
//                             <span className="hidden md:inline">{tab.label}</span>
//                         </button>
//                     ))}
//                 </div>
//             </div>

//             <div className="flex-1 overflow-hidden flex flex-col">
//                 <div className="overflow-x-auto">
//                     <table className="w-full text-left">
//                         <thead>
//                             <tr className="border-b border-gray-50">
//                                 <th className="pb-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider pl-2">Product</th>
//                                 <th className="pb-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider">Current Stock</th>
//                                 <th className="pb-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
//                                     {activeTab === "expiring" ? "Expiry In" : "Velocity Status"}
//                                 </th>
//                                 <th className="pb-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider text-right pr-2">Action</th>
//                             </tr>
//                         </thead>
//                         <tbody className="divide-y divide-gray-50">
//                             {inventoryData[activeTab].map((item) => (
//                                 <tr key={item.id} className="group hover:bg-gray-50/50 transition-colors">
//                                     <td className="py-4 pl-2">
//                                         <div className="flex items-center gap-3">
//                                             <div className={`w-8 h-8 rounded-lg ${tabs.find(t => t.id === activeTab).bg} flex items-center justify-center`}>
//                                                 <Package size={14} className={tabs.find(t => t.id === activeTab).color} />
//                                             </div>
//                                             <span className="text-sm font-semibold text-gray-700">{item.name}</span>
//                                         </div>
//                                     </td>
//                                     <td className="py-4">
//                                         <span className={`text-sm font-bold ${item.stock === 0 ? "text-red-500" : "text-gray-600"}`}>
//                                             {item.stock} Units
//                                         </span>
//                                     </td>
//                                     <td className="py-4">
//                                         <div className="flex items-center gap-2">
//                                             <div className={`w-1.5 h-1.5 rounded-full ${tabs.find(t => t.id === activeTab).color.replace('text', 'bg')}`}></div>
//                                             <span className="text-xs font-bold text-gray-500 uppercase">{item.status}</span>
//                                         </div>
//                                     </td>
//                                     <td className="py-4 text-right pr-2">
//                                         <button className="p-2 hover:bg-white hover:shadow-sm rounded-lg transition-all text-gray-400 hover:text-[#127690]">
//                                             <ChevronRight size={16} />
//                                         </button>
//                                     </td>
//                                 </tr>
//                             ))}
//                         </tbody>
//                     </table>
//                 </div>

//                 {inventoryData[activeTab].length === 0 && (
//                     <div className="flex-1 flex flex-col items-center justify-center text-gray-400 py-10">
//                         <Package size={40} className="mb-2 opacity-20" />
//                         <p className="text-sm font-medium">No records found for this category</p>
//                     </div>
//                 )}
//             </div>
//         </div>
//     );
// };

// export default InventoryInsights;
