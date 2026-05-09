import React, { useState, useMemo, useEffect } from "react";
import { Search, Filter, Eye, AlertCircle, CheckCircle, Package, ChevronDown } from "lucide-react";
import SummaryCard from "../components/SummaryCard";

export default function Refunds() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

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

  // Pagination logic
  const totalPages = Math.ceil(filteredRefunds.length / itemsPerPage);
  const currentItems = filteredRefunds.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Reset pagination when filter changes
  useEffect(() => {
    setCurrentPage(1);
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
    <div className="   ml-5 mt-5 border-l-2 border-gray-100">
      {/* Header */}
      <div className="mb-3 flex flex-col md:flex-row md:items-end justify-between gap-4 ">
        <div>
          <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
            Refund & Cancellation Management
          </h1>
          <p className="text-sm text-gray-500">
            Monitor and track all retailer orders with ERP sync status
          </p>
        </div>

        {/* Search & Filter */}
        <div className="flex items-center bg-white border border-[#E5E7EB] rounded-xl px-2 py-1.5 shadow-sm w-full lg:max-w-xl transition-all focus-within:shadow-lg">

          <Search size={18} className="text-[#9EA2A7] ml-2 shrink-0" />

          <input
            type="text"
            placeholder="Search by shop name or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1 border-none rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none text-sm text-[#505050] placeholder:text-[#9EA2A7] transition-all"
          />

          <div className="relative min-w-[140px]">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="appearance-none w-full bg-white border border-[#E5E7EB] rounded-xl px-4 py-2 pr-10 text-sm text-[#505050] font-medium hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer transition-colors"
            >
              <option value="All">All Status</option>
              <option value="Pending">Pending</option>
              <option value="Approved">Approved</option>
              <option value="Confirmed">Confirmed</option>
            </select>

            <ChevronDown
              size={16}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9EA2A7] pointer-events-none"
            />
          </div>

        </div>
      </div>

      {/* Stats Cards */}
      <div className="flex flex-col md:flex-row gap-4 lg:gap-6 mb-3">
        <SummaryCard
          title="Pending Approval"
          value={refundsData.filter((item) => item.status === "Pending").length}
          icon={<AlertCircle size={20} />}
          bgClass="bg-[#f2ecbb]"
          textClass="text-[#846018]"
          iconClass=""
          blobColor1="bg-[#D08700]"
          blobColor2="bg-[#733E0A]"
        />
        <SummaryCard
          title="In Progress"
          value={refundsData.filter((item) => item.status === "Approved" || item.status === "Confirmed").length}
          icon={<CheckCircle size={20} />}
          bgClass="bg-[#d8e9ff]"
          textClass="text-[#1D4ED8]"
          iconClass="text-blue-600"
          blobColor1="bg-[#83ACE5]"
          blobColor2="bg-[#1447EA]"
        />
        <SummaryCard
          title="Total Refunds (This Month)"
          value={refundsData.length}
          icon={<Package size={20} />}
          bgClass="bg-[#e9fedf]"
          textClass="text-[#207238]"
          iconClass=""
          blobColor1="bg-[#A3FF63]"
          blobColor2="bg-[#33CB6C]"
        />
      </div>


      {/* Table with Scroll */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 flex-1 overflow-hidden">
        <div className="overflow-x-auto overflow-y-auto max-h-[500px]">
          <table className="min-w-[1000px] w-full text-left">
            <thead className="bg-[#DCE4EA] text-gray-500 text-[11px] uppercase font-bold tracking-wider sticky top-0 z-10">
              <tr>
                <th className="px-6 py-4 text-center">SI NO</th>
                <th className="px-6 py-4">Refund ID</th>
                <th className="px-6">Order ID</th>
                <th className="px-6">Retailer</th>
                <th className="px-6">Amount</th>
                <th className="px-6">Type</th>
                <th className="px-6 text-center">Status</th>
                <th className="px-6">Request Date</th>
                <th className="px-6 text-center">Actions</th>
              </tr>
            </thead>

            <tbody className="text-sm text-gray-700">
              {currentItems.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-10 text-center text-gray-400">
                    No refunds found.
                  </td>
                </tr>
              ) : (
                currentItems.map((item, index) => (
                  <tr
                    key={item.id}
                    className={`${index % 2 === 0 ? "bg-white" : "bg-[#F4F6F8]"
                      } hover:bg-[#EEF2F6] transition`}
                  >
                    <td className="px-6 py-4 font-bold text-center">{(currentPage - 1) * itemsPerPage + index + 1}</td>
                  <td className="px-6 py-4 text-sm font-bold text-[#127690]">{item.id}</td>
                  <td className="px-6 text-sm text-gray-500 font-medium">{item.orderId}</td>
                  <td className="px-6 text-sm text-gray-600 font-medium">{item.retailer}</td>
                  <td className="px-6 text-sm text-gray-900 font-bold">₹ {item.amount}</td>
                  <td className="px-6 text-sm text-gray-600 font-medium">{item.type}</td>
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
                  <td className="px-6 text-center">
                    <button className="text-[#127690] hover:text-[#116278] transition-colors">
                      <Eye size={18} />
                    </button>
                  </td>
                </tr>
              )))}
            </tbody>
          </table>
        </div>

        {/* Pagination UI - Numbered Design */}
        {totalPages > 1 && (
          <div className="mt-4 mb-4 flex items-center justify-end px-6 border-t border-gray-50 pt-4">
            <div className="flex gap-1.5">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-xl border border-gray-200 text-gray-400 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="rotate-90"><path d="m6 9 6 6 6-6"/></svg>
              </button>

              {[...Array(totalPages)].map((_, i) => {
                const pageNum = i + 1;
                if (
                  totalPages <= 7 ||
                  pageNum === 1 ||
                  pageNum === totalPages ||
                  (pageNum >= currentPage - 1 && pageNum <= currentPage + 1)
                ) {
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`w-9 h-9 rounded-xl font-bold text-xs transition-all ${currentPage === pageNum
                        ? 'bg-[#127690] text-white shadow-lg shadow-[#127690]/20 scale-110'
                        : 'bg-white border border-gray-200 text-gray-500 hover:border-[#127690] hover:text-[#127690]'
                        }`}
                    >
                      {pageNum}
                    </button>
                  );
                } else if (
                  pageNum === currentPage - 2 ||
                  pageNum === currentPage + 2
                ) {
                  return <span key={pageNum} className="flex items-end pb-2 text-gray-300">...</span>;
                }
                return null;
              })}

              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="p-2 rounded-xl border border-gray-200 text-gray-400 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="-rotate-90"><path d="m6 9 6 6 6-6"/></svg>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}