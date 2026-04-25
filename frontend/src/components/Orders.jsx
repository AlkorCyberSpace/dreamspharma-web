import React, { useEffect, useState } from 'react';
import { Search, ChevronDown, Eye, X, Check, Download } from 'lucide-react';
import { getOrdersApi, markCODDeliveredAPI, getSuperAdminProfileAPI } from '../services/allAPI';

const OrderDetailModal = ({ order, onClose, userId, onOrderConfirmed }) => {
  const [confirming, setConfirming] = useState(false);
  if (!order) return null;

  const handleConfirmOrder = async () => {
    try {
      setConfirming(true);
      const data = {
        order_id: order.id,
        status: 'delivered'
      };
      const response = await markCODDeliveredAPI(data);

      if (response.data.success) {
        alert(response.data.message || "Order marked as delivered successfully!");
        onOrderConfirmed();
        onClose();
      } else {
        alert(response.data.error || "Failed to mark order as delivered.");
      }
    } catch (error) {
      console.error("Error marking order as delivered:", error);
      const errorMessage = error.response?.data?.error || "An error occurred. Please try again.";
      alert(errorMessage);
    } finally {
      setConfirming(false);
    }
  };



  const timelineSteps = [
    { key: 'Created', label: 'Created' },
    { key: 'Confirmed', label: 'Confirmed' },
    { key: 'ERP Synced', label: 'ERP Synced' },
    { key: 'Dispatched', label: 'Dispatched' },
    { key: 'Delivered', label: 'Delivered' }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in duration-200" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="px-8 py-4 flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-[#505050]">order Details</h2>
            <p className="text-sm font-medium text-[#9EA2A7] mt-1">{order.id}</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-full border border-gray-200 text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Info Grid */}
        <div className="px-8 pb-4 grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="space-y-1">
            <p className="text-[10px] font-bold text-[#9EA2A7] uppercase tracking-wider">Retailer</p>
            <p className="text-sm font-bold text-[#505050] break-words">{order.retailer}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] font-bold text-[#9EA2A7] uppercase tracking-wider">Order Date</p>
            <p className="text-sm font-bold text-[#505050]">{order.date}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] font-bold text-[#9EA2A7] uppercase tracking-wider">Payment Mode</p>
            <p className="text-sm font-bold text-[#505050]">{order.payment}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] font-bold text-[#9EA2A7] uppercase tracking-wider">ERP Reference</p>
            <p className="text-sm font-bold text-[#505050]">{order.erpRef}</p>
          </div>
        </div>

        <div className="px-8 py-2 max-h-[60vh] overflow-y-auto custom-scrollbar">
          {/* Order Timeline */}
          <div className="">
            <h3 className="text-sm font-bold text-[#505050] mb-6">Order Timeline</h3>
            <div className="space-y-0">
              {timelineSteps.map((step, idx) => {
                const milestone = order.detailedTimeline?.find(t => t.label === step.key);
                const isCompleted = milestone?.status === 'completed';
                const isLast = idx === timelineSteps.length - 1;

                return (
                  <div key={step.key} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors ${isCompleted ? 'bg-[#E7F9F0]' : 'bg-[#F2F4F7]'}`}>
                        {isCompleted ? (
                          <Check size={16} className="text-[#12B76A] stroke-[3px]" />
                        ) : (
                          <span className="text-xs font-bold text-[#9EA2A7]">{idx + 1}</span>
                        )}
                      </div>
                      {!isLast && (
                        <div className={`w-[2px] h-8 transition-colors ${isCompleted ? 'bg-[#E7F9F0]' : 'bg-[#F2F4F7]'}`} />
                      )}
                    </div>
                    <div className="pt-1 pb-6">
                      <p className={`text-sm font-bold ${isCompleted ? 'text-[#505050]' : 'text-[#9EA2A7]'}`}>
                        {step.label}
                      </p>
                      {milestone && (
                        <p className="text-xs text-[#9EA2A7] mt-0.5">{milestone.date}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Order Items */}
          <div className="mb-6">
            <h3 className="text-sm font-bold text-[#505050] mb-2">Order Items</h3>
            <div className="rounded-xl border border-[#E5E7EB] overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-[#EEF7FA]">
                  <tr className="text-[11px] font-bold text-[#505050]/70 uppercase tracking-wider">
                    <th className="px-4 py-3">Product</th>
                    <th className="px-4 py-3 text-center">Quantity</th>
                    <th className="px-4 py-3 text-center">MRP</th>
                    <th className="px-4 py-3 text-right">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E7EB]">
                  {(order.detailedItems || []).map((item, idx) => (
                    <tr key={idx} className="text-xs text-[#505050] font-medium">
                      <td className="px-4 py-3">{item.name}</td>
                      <td className="px-4 py-3 text-center">{item.qty}</td>
                      <td className="px-4 py-3 text-center">₹{item.mrp}</td>
                      <td className="px-4 py-3 text-right font-bold">₹{item.total.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex flex-col items-end gap-1 mb-8">
            <p className="text-[10px] font-bold text-[#9EA2A7] uppercase tracking-wider">Total Amount</p>
            <p className="text-3xl font-bold text-[#505050]">₹{order.total}</p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-8 py-6 border-t border-gray-100 flex gap-4">
          <button className="flex-1 flex items-center justify-center gap-2 py-3 bg-white border border-[#E5E7EB] rounded-xl text-sm font-bold text-[#505050] hover:bg-gray-50 transition-colors">
            <Download size={18} />
            Download Invoice
          </button>
          {order.status === 'Pending' && order.payment === 'Cash on Delivery' && (
            <button
              onClick={handleConfirmOrder}
              disabled={confirming}
              className="flex-1 flex items-center justify-center gap-2 py-3 bg-[#127690] text-white rounded-xl text-sm font-bold hover:bg-teal-700 transition-all shadow-lg shadow-teal-900/10 disabled:opacity-50 disabled:cursor-not-allowed group"
            >
              {confirming ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Check size={18} className="group-hover:scale-110 transition-transform" />
              )}
              {confirming ? 'Confirming...' : 'Confirm Order'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const Orders = () => {
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [adminId, setAdminId] = useState(null);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const response = await getOrdersApi();

      // Map API response to component format
      if (response?.data?.results) {
        const mappedOrders = response.data.results.map(order => ({
          id: order.id,
          retailer: order.retailer,
          retailer_id: order.retailer_id,
          date: order.date,
          items: order.items,
          total: order.total,
          payment: order.payment,
          payment_status: order.payment_status,
          status: order.status,
          payment_id: order.payment_id,
          erpRef: order.erpRef,
          detailedTimeline: order.detailedTimeline || [],
          detailedItems: order.detailedItems || []
        }));
        setOrders(mappedOrders);
        setError(null);
      }
    } catch (error) {
      console.error("Failed to fetch orders:", error);
      setError("Failed to load orders. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();

    // Fetch Admin Profile for ID
    const fetchAdminProfile = async () => {
      try {
        const response = await getSuperAdminProfileAPI();
        if (response.status === 200) {
          setAdminId(response.data.profile.id);
        }
      } catch (err) {
        console.error("Failed to fetch admin profile:", err);
      }
    };
    fetchAdminProfile();
  }, []);
  const getStatusStyles = (status) => {
    switch (status) {
      case 'Delivered':
        return 'bg-emerald-100 text-emerald-600';
      case 'Dispatched':
        return 'bg-purple-100 text-purple-600';
      case 'Confirmed':
        return 'bg-blue-100 text-blue-600';
      case 'Pending':
        return 'bg-amber-100 text-amber-600';
      case 'Cancelled':
        return 'bg-red-100 text-red-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  return (
    <div className="h-screen overflow-hidden flex flex-col font-sans ml-2 mt-3">
      <style>
        {`
          .custom-scrollbar::-webkit-scrollbar {
            width: 5px;
            height: 5px;
          }
          .custom-scrollbar::-webkit-scrollbar-track {
            background: transparent;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #E5E7EB;
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #D1D5DB;
          }
        `}
      </style>

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 shrink-0">
        <div>
          <h1 className="text-xl font-semibold text-[#505050]">Order Management</h1>
          <p className="text-sm text-gray-500 ">Monitor and track all retailer orders with ERP sync status</p>
        </div>

        <div className="flex items-center bg-white border border-[#E5E7EB] rounded-xl px-2.5 py-1.5 shadow-sm w-full lg:max-w-xl transition-all focus-within:shadow-lg">
          <div className="flex items-center flex-1 px-2">
            <Search size={18} className="text-[#9EA2A7] shrink-0" />
            <input
              type="text"
              placeholder="Search by shop name or owner..."
              className="w-full bg-transparent outline-none px-3 text-sm text-[#505050] placeholder:text-[#9EA2A7]"
            />
          </div>
          <div className="relative min-w-[140px]">
            <select className="appearance-none w-full bg-white border border-[#E5E7EB] rounded-xl px-4 py-1.5 pr-10 text-sm text-[#505050] font-medium focus:outline-none cursor-pointer">
              <option>All Status</option>
              <option>Delivered</option>
              <option>Dispatched</option>
              <option>Confirmed</option>
              <option>Pending</option>
              <option>Cancelled</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9EA2A7] w-4 h-4 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Table Section */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col mb-5">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#127690] mb-4"></div>
              <p className="text-gray-500">Loading orders...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-red-500 font-medium">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-[#127690] text-white rounded-lg text-sm font-medium hover:bg-teal-600 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        ) : orders.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-gray-500">No orders found</p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto overflow-y-auto flex-1 custom-scrollbar">
            <table className="w-full text-left border-collapse min-w-[1000px]">
              <thead className="sticky top-0 z-10">
                <tr className="bg-[#DCE4EA] text-gray-500 uppercase text-[11px] font-bold tracking-wider">
                  <th className="px-6 py-4">Order ID</th>
                  <th className="px-6">Retailer</th>
                  <th className="px-6">Date</th>
                  <th className="px-6">Items</th>
                  <th className="px-6 text-center">Total Value</th>
                  <th className="px-6">Payment</th>
                  <th className="px-6 text-center">Status</th>
                  <th className="px-6">ERP Ref</th>
                  <th className="px-6 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {orders.map((order, index) => (
                  <tr key={index} className={`transition-colors hover:bg-[#EEF2F6] ${index % 2 === 0 ? "bg-white" : "bg-[#F4F6F8]"}`}>
                    <td className="px-3 py-3 text-sm font-semibold text-[#127690]">{order.id}</td>
                    <td className="px-6 text-sm text-gray-600 font-medium">{order.retailer}</td>
                    <td className="px-6 text-sm text-gray-500 whitespace-nowrap">{order.date}</td>
                    <td className="px-6 text-sm text-gray-600 font-semibold">{order.items}</td>
                    <td className="px-6 text-sm text-gray-600 text-center font-semibold">₹{order.total}</td>
                    <td className="px-6 text-sm text-gray-600 font-medium">{order.payment}</td>
                    <td className="px-6 text-center">
                      <span className={`px-3 py-1 rounded-full text-[12px] font-bold inline-block min-w-[85px] ${getStatusStyles(order.status)}`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="px-6 text-sm text-gray-500 font-medium">{order.erpRef}</td>
                    <td className="px-6 text-center">
                      <button
                        onClick={() => setSelectedOrder(order)}
                        className="text-[#127690] hover:text-teal-600 transition-colors"
                      >
                        <Eye size={20} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <OrderDetailModal
          order={selectedOrder}
          onClose={() => setSelectedOrder(null)}
          userId={adminId}
          onOrderConfirmed={fetchOrders}
        />
      </div>
    </div>
  );
};

export default Orders;