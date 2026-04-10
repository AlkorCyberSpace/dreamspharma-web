import React, { useState } from 'react';
import { Search, ChevronDown, Eye, X, Check, Download } from 'lucide-react';

const OrderDetailModal = ({ order, onClose }) => {
  if (!order) return null;

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
        <div className="px-8 py-6 border-t border-gray-100">
          <button className="w-full flex items-center justify-center gap-2 py-3 bg-white border border-[#E5E7EB] rounded-xl text-sm font-bold text-[#505050] hover:bg-gray-50 transition-colors">
            <Download size={18} />
            Download Invoice
          </button>
        </div>
      </div>
    </div>
  );
};

const Orders = () => {
  const [selectedOrder, setSelectedOrder] = useState(null);
  const orders = [
    {
      id: 'ORD-2026-001',
      retailer: 'MedPlus Pharmacy',
      date: '2026-02-05',
      items: 12,
      total: '15,420',
      payment: 'Razorpay',
      status: 'Delivered',
      erpRef: 'ERP-45678',
      detailedTimeline: [
        { label: 'Created', date: '2026-02-05 09:30 AM', status: 'completed' },
        { label: 'Confirmed', date: '2026-02-05 10:15 AM', status: 'completed' },
        { label: 'ERP Synced', date: '2026-02-05 10:30 AM', status: 'completed' },
        { label: 'Dispatched', date: '2026-02-05 02:30 PM', status: 'completed' },
        { label: 'Delivered', date: '2026-02-05 06:30 PM', status: 'upcoming' }
      ],
      detailedItems: [
        { name: 'Paracetamol 500mg (Strip of 15)', qty: 50, mrp: 25, total: 1250 },
        { name: 'Amoxicillin 250mg (Strip of 10)', qty: 20, mrp: 85, total: 1700 },
        { name: 'Cetirizine 10mg (Strip of 10)', qty: 100, mrp: 15, total: 1500 },
      ]
    },
    { id: 'ORD-2026-002', retailer: 'MedPlus Pharmacy', date: '2026-02-05', items: 12, total: '15,420', payment: 'Razorpay', status: 'Dispatched', erpRef: 'ERP-45678', detailedTimeline: [], detailedItems: [] },
    { id: 'ORD-2026-003', retailer: 'MedPlus Pharmacy', date: '2026-02-21', items: 12, total: '15,420', payment: 'Razorpay', status: 'Confirmed', erpRef: 'ERP-25821', detailedTimeline: [], detailedItems: [] },
    { id: 'ORD-2026-004', retailer: 'MedPlus Pharmacy', date: '2026-02-21', items: 12, total: '15,420', payment: 'Razorpay', status: 'Pending', erpRef: 'ERP-25821', detailedTimeline: [], detailedItems: [] },
    { id: 'ORD-2026-005', retailer: 'MedPlus Pharmacy', date: '2026-02-21', items: 12, total: '15,420', payment: 'Razorpay', status: 'Cancelled', erpRef: 'ERP-25821', detailedTimeline: [], detailedItems: [] },
  ];

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
                  <td className="px-6 text-sm text-gray-600 text-center font-semibold">{order.total}</td>
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
      </div>
      <OrderDetailModal
        order={selectedOrder}
        onClose={() => setSelectedOrder(null)}
      />
    </div>
  );
};

export default Orders;