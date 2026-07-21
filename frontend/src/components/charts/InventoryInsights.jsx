import React, { useState, useEffect } from 'react';
import { Package, AlertTriangle, Zap, Clock, ChevronRight } from "lucide-react";
import { getInventoryInsightsAPI } from '../../services/allAPI';

const InventoryInsights = ({ storeId }) => {
  const [insightsData, setInsightsData] = useState({
    expiring_soon: [],
    out_of_stock: [],
    fast_moving: [],
    slow_moving: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('expiring_soon');

  const tabs = [
    { id: 'expiring_soon', label: 'Expiring Soon', icon: Clock, color: "text-amber-500", bg: "bg-amber-50" },
    { id: 'out_of_stock', label: 'Out of Stock', icon: AlertTriangle, color: "text-red-500", bg: "bg-red-50" },
    { id: 'fast_moving', label: 'Fast Moving', icon: Zap, color: "text-emerald-500", bg: "bg-emerald-50" },
    { id: 'slow_moving', label: 'Slow Moving', icon: Package, color: "text-blue-500", bg: "bg-blue-50" }
  ];

  useEffect(() => {
    const fetchInsights = async () => {
      setLoading(true);
      setError(null);
      try {
        console.log(`[InventoryInsights] Fetching for store: ${storeId || '001'}`);
        const response = await getInventoryInsightsAPI({ store_id: storeId || '001' });
        console.log('[InventoryInsights] Response:', response);

        if (response.status === 200 && response.data?.success) {
          setInsightsData(response.data.data);
          console.log('[InventoryInsights] Data loaded:', response.data.data);
        } else if (response.status === 200) {
          setError(response.data?.message || 'Failed to fetch insights');
        }
      } catch (error) {
        console.error("[InventoryInsights] Error fetching inventory insights:", error);
        setError(`Error: ${error.message || 'Failed to load insights'}`);
      } finally {
        setLoading(false);
      }
    };
    fetchInsights();
  }, [storeId]);

  const currentTabData = insightsData[activeTab] || [];
  const activeTabInfo = tabs.find(t => t.id === activeTab);

  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col h-[400px]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
        <div>
          <h3 className="text-lg font-bold text-gray-800 tracking-tight">Inventory Insights</h3>
          <p className="text-gray-400 text-xs mt-1">Real-time pharmaceutical stock analysis</p>
        </div>

        <div className="flex bg-gray-50 p-1 rounded-xl border border-gray-100 overflow-x-auto no-scrollbar">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all whitespace-nowrap ${activeTab === tab.id
                  ? "bg-white text-[#127690] shadow-sm ring-1 ring-black/5"
                  : "text-gray-400 hover:text-gray-600"
                }`}
            >
              <tab.icon size={14} className={activeTab === tab.id ? tab.color : ""} />
              <span className="hidden md:inline">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center py-12">
            <div className="w-8 h-8 border-3 border-[#127690] border-t-transparent rounded-full animate-spin mb-3"></div>
            <p className="text-gray-400 text-xs font-medium">Fetching insights...</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex flex-col items-center justify-center py-12">
            <AlertTriangle size={40} className="mb-2 opacity-30 text-red-500" />
            <p className="text-red-500 text-sm font-medium">{error}</p>
            <p className="text-gray-400 text-xs mt-2">Please check if ERP is configured and running</p>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto relative">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-white z-10 before:absolute before:inset-x-0 before:bottom-0 before:border-b before:border-gray-50">
                  <tr>
                    <th className="pb-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider pl-2 pt-2">Product</th>
                    <th className="pb-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider text-center pt-2">Stock</th>
                    <th className="pb-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider text-center pt-2">
                      {activeTab === 'fast_moving' ? 'Sold (30d)' : 'Status/Expiry'}
                    </th>
                    <th className="pb-4 text-[10px] font-bold text-gray-400 uppercase tracking-wider text-right pr-2 pt-2">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {currentTabData.length > 0 ? (
                    currentTabData.map((item, index) => (
                      <tr key={index} className="group hover:bg-gray-50/50 transition-colors">
                        <td className="py-4 pl-2">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-lg ${activeTabInfo.bg} flex items-center justify-center`}>
                              <Package size={14} className={activeTabInfo.color} />
                            </div>
                            <span className="text-sm font-semibold text-gray-700 truncate max-w-[150px]" title={item.product}>
                              {item.product}
                            </span>
                          </div>
                        </td>
                        <td className="py-4 text-center">
                          <span className={`text-sm font-bold ${item.stock === 0 ? "text-red-500" : "text-gray-600"}`}>
                            {item.stock}
                          </span>
                        </td>
                        <td className="py-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className={`w-1.5 h-1.5 rounded-full ${activeTabInfo.color.replace('text', 'bg')}`}></div>
                            <span className="text-xs font-bold text-gray-500 uppercase">
                              {activeTab === 'fast_moving' ? item.sold_last_30_days : item.expiry}
                            </span>
                          </div>
                        </td>
                        <td className="py-4 text-right pr-2">
                          <button className="p-2 hover:bg-white hover:shadow-sm rounded-lg transition-all text-gray-400 hover:text-[#127690]">
                            <ChevronRight size={16} />
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" className="py-12 text-center text-gray-400">
                        <div className="flex flex-col items-center">
                          <Package size={40} className="mb-2 opacity-20" />
                          <p className="text-sm font-medium">No records found for this category</p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default InventoryInsights;
