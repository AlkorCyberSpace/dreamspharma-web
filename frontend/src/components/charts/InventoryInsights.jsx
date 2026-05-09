import React, { useState, useEffect } from 'react';
import { getInventoryInsightsAPI } from '../../services/allAPI';

const InventoryInsights = ({ storeId }) => {
  const [insightsData, setInsightsData] = useState({
    expiring_soon: [],
    out_of_stock: [],
    fast_moving: [],
    slow_moving: []
  });
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('expiring_soon');

  const tabs = [
    { id: 'expiring_soon', label: 'Expiring soon medicines' },
    { id: 'out_of_stock', label: 'Out of stock' },
    { id: 'fast_moving', label: 'Fast moving products' },
    { id: 'slow_moving', label: 'Slow moving products' }
  ];

  useEffect(() => {
    const fetchInsights = async () => {
      setLoading(true);
      try {
        const response = await getInventoryInsightsAPI(storeId || '001');
        if (response.status === 200 && response.data?.success) {
          setInsightsData(response.data.data);
        }
      } catch (error) {
        console.error("Error fetching inventory insights:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchInsights();
  }, [storeId]);

  return (
    <div className="bg-black text-white p-6 rounded-2xl shadow-lg border border-gray-800 w-full mb-6">
      <h2 className="text-2xl font-bold mb-2">Inventory Insights</h2>
      <p className="text-gray-400 mb-6 text-sm">Very important in pharma.</p>

      <div className="mb-6">
        <p className="mb-3 text-gray-300">Show:</p>
        <ul className="space-y-2">
          {tabs.map(tab => (
            <li 
              key={tab.id} 
              className={`cursor-pointer flex items-center transition-colors ${activeTab === tab.id ? 'text-white font-semibold' : 'text-gray-400 hover:text-gray-200'}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className={`w-1.5 h-1.5 rounded-full mr-3 ${activeTab === tab.id ? 'bg-white' : 'bg-gray-500'}`}></span>
              {tab.label}
            </li>
          ))}
        </ul>
      </div>

      <p className="text-gray-400 text-sm mb-4">Example:</p>

      {loading ? (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-white"></div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="pb-3 font-semibold w-1/2">Product</th>
                <th className="pb-3 font-semibold w-1/4 text-center">Stock</th>
                <th className="pb-3 font-semibold w-1/4 text-right">Expiry</th>
              </tr>
            </thead>
            <tbody>
              {insightsData[activeTab]?.length > 0 ? (
                insightsData[activeTab].map((item, index) => (
                  <tr key={index} className="border-b border-gray-800 last:border-0 hover:bg-gray-900 transition-colors">
                    <td className="py-4 text-gray-200 truncate pr-4">{item.product}</td>
                    <td className="py-4 text-center text-gray-300">
                      {item.stock}
                    </td>
                    <td className="py-4 text-right text-gray-300">{item.expiry}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="3" className="py-8 text-center text-gray-500">
                    No data available for {tabs.find(t => t.id === activeTab)?.label.toLowerCase()}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default InventoryInsights;
