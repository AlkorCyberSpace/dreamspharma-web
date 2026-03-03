import React, { useState, useMemo } from "react";
import { Search, Filter, Eye, CheckCircle } from "lucide-react";

export default function Refunds() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const refundsData = [
    {
      id: "RET001",
      orderId: "ORD-2026-001",
      retailer: "MedPlus Pharmacy",
      amount: "5,420",
      type: "Partial",
      status: "Pending",
      date: "2026 - 03 - 05",
    },
    {
      id: "RET002",
      orderId: "ORD-2026-003",
      retailer: "Care Well Medicals",
      amount: "22,340",
      type: "Full",
      status: "Approved",
      date: "2026 - 03 - 09",
    },
    {
      id: "RET003",
      orderId: "ORD-2026-004",
      retailer: "MedPlus Pharmacy",
      amount: "5,420",
      type: "Partial",
      status: "Pending",
      date: "2026 - 03 - 05",
    },
    {
      id: "RET004",
      orderId: "ORD-2026-008",
      retailer: "Care Well Medicals",
      amount: "22,340",
      type: "Full",
      status: "Confirmed",
      date: "2026 - 04 - 09",
    },
    {
      id: "RET005",
      orderId: "ORD-2026-011",
      retailer: "Apollo Pharmacy",
      amount: "8,950",
      type: "Partial",
      status: "Approved",
      date: "2026 - 04 - 12",
    },
  ];

  const filteredRefunds = useMemo(() => {
    return refundsData.filter((item) => {
      const searchValue = search.toLowerCase();

      const matchesSearch =
        item.retailer.toLowerCase().includes(searchValue) ||
        item.id.toLowerCase().includes(searchValue) ||
        item.orderId.toLowerCase().includes(searchValue);

      const matchesStatus =
        statusFilter === "All" || item.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [search, statusFilter]);

  const getStatusStyle = (status) => {
    switch (status) {
      case "Pending":
        return "bg-yellow-100 text-yellow-700";
      case "Approved":
        return "bg-green-100 text-green-700";
      case "Confirmed":
        return "bg-blue-100 text-blue-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <div className="p-8 bg-[#F4F6F8] min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-800">
          Refund & Cancellation Management
        </h1>
        <p className="text-sm text-gray-500">
          Razorpay – linked refund approval workflow with audit trail
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-[#F6EED6] border border-[#F2D58A] rounded-2xl p-6">
          <span className="text-sm text-[#B7791F] font-medium">
            Pending Approval
          </span>
          <div className="text-3xl text-[#B7791F] font-semibold mt-2">
            {
              refundsData.filter((item) => item.status === "Pending").length
            }
          </div>
        </div>

        <div className="bg-[#E3ECFA] border border-[#B6CCF6] rounded-2xl p-6">
          <span className="text-sm text-[#2563EB] font-medium">
            In Progress
          </span>
          <div className="text-3xl text-[#2563EB] font-semibold mt-2">
            {
              refundsData.filter(
                (item) =>
                  item.status === "Approved" ||
                  item.status === "Confirmed"
              ).length
            }
          </div>
        </div>

        <div className="bg-[#DFF5E8] border border-[#A7E3C2] rounded-2xl p-6">
          <div className="flex justify-between items-center">
            <span className="text-sm text-[#15803D] font-medium">
              Total Refunds (This Month)
            </span>
            <CheckCircle size={18} className="text-[#15803D]" />
          </div>
          <div className="text-3xl text-[#15803D] font-semibold mt-2">
            {refundsData.length}
          </div>
        </div>
      </div>

      {/* Search + Filter */}
      <div className="bg-white p-4 rounded-2xl shadow-sm mb-6 flex items-center gap-4">
        <div className="relative flex-1">
          <Search
            size={18}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Search by shop name or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-11 pr-4 py-2 border border-gray-200 rounded-xl bg-[#F9FAFB] focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 border border-gray-200 bg-[#F9FAFB] px-4 py-2 rounded-xl">
          <Filter size={16} className="text-gray-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-transparent outline-none text-sm text-gray-600"
          >
            <option value="All">All</option>
            <option value="Pending">Pending</option>
            <option value="Approved">Approved</option>
            <option value="Confirmed">Confirmed</option>
          </select>
        </div>
      </div>

      {/* Table with Scroll */}
      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto overflow-y-auto max-h-[400px]">
          <table className="min-w-[900px] w-full text-left">
            <thead className="bg-[#DCE4EA] text-gray-600 text-xs uppercase tracking-wide sticky top-0 z-10">
              <tr>
                <th className="px-6 py-4">Refund ID</th>
                <th className="px-6">Order ID</th>
                <th className="px-6">Retailer</th>
                <th className="px-6">Amount</th>
                <th className="px-6">Type</th>
                <th className="px-6">Status</th>
                <th className="px-6">Request Date</th>
                <th className="px-6">Actions</th>
              </tr>
            </thead>

            <tbody className="text-sm text-gray-700">
              {filteredRefunds.map((item, index) => (
                <tr
                  key={item.id}
                  className={`${
                    index % 2 === 0 ? "bg-white" : "bg-[#F4F6F8]"
                  } hover:bg-[#EEF2F6] transition`}
                >
                  <td className="px-6 py-4 font-semibold">{item.id}</td>
                  <td className="px-6">{item.orderId}</td>
                  <td className="px-6">{item.retailer}</td>
                  <td className="px-6 font-medium">₹ {item.amount}</td>
                  <td className="px-6">{item.type}</td>
                  <td className="px-6">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusStyle(
                        item.status
                      )}`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="px-6">{item.date}</td>
                  <td className="px-6">
                    <button className="text-teal-600 hover:text-teal-800">
                      <Eye size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}