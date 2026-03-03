import React, { useState } from "react";
import { Search, Filter, Eye } from "lucide-react";

export default function RetailerKYCPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const retailersData = [
    {
      id: "RET001",
      shop: "MedPlus Pharmacy",
      owner: "Rajesh Kumar",
      phone: "+91 9876543210",
      email: "rajesh@medplus.com",
      status: "Approved",
    },
    {
      id: "RET002",
      shop: "Care Medicals",
      owner: "Anita Sharma",
      phone: "+91 9876543211",
      email: "anita@caremedicals.com",
      status: "Pending",
    },
    {
      id: "RET003",
      shop: "Health Mart",
      owner: "Vikram Nair",
      phone: "+91 9876543212",
      email: "vikram@healthmart.com",
      status: "Approved",
    },
    {
      id: "RET004",
      shop: "City Pharmacy",
      owner: "Meera Joseph",
      phone: "+91 9876543213",
      email: "meera@citypharmacy.com",
      status: "Approved",
    },
    {
      id: "RET005",
      shop: "LifeCare Drugs",
      owner: "Arjun Menon",
      phone: "+91 9876543214",
      email: "arjun@lifecare.com",
      status: "Pending",
    },
    {
      id: "RET006",
      shop: "Apollo Medicos",
      owner: "Sneha Pillai",
      phone: "+91 9876543215",
      email: "sneha@apollomedicos.com",
      status: "Approved",
    },
  ];

  const filteredRetailers = retailersData.filter((retailer) => {
    const matchesSearch =
      retailer.shop.toLowerCase().includes(search.toLowerCase()) ||
      retailer.owner.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "All" || retailer.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="h-full overflow-hidden flex flex-col px-4 sm:px-6 lg:px-8">
      
      {/* Page Title */}
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-semibold text-gray-800">
          Retailer & KYC Management
        </h1>
        <p className="text-xs sm:text-sm text-gray-500">
          Manage pharmacy retailers and KYC verification
        </p>
      </div>

      {/* Search & Filter */}
      <div className="bg-white rounded-xl p-4 shadow-sm mb-6 flex flex-col sm:flex-row sm:items-center gap-4">
        
        {/* Search */}
        <div className="relative flex-1">
          <Search
            size={18}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Search by shop name or owner..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-11 pr-4 py-2 border border-gray-200 rounded-lg bg-[#F9FAFB] focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm"
          />
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2 bg-[#F9FAFB] border border-gray-200 rounded-lg px-4 py-2 w-full sm:w-auto">
          <Filter size={16} className="text-gray-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-transparent outline-none text-gray-600 text-sm w-full"
          >
            <option value="All">All Status</option>
            <option value="Approved">Approved</option>
            <option value="Pending">Pending</option>
          </select>
        </div>
      </div>

      {/* Table Section */}
      <div className="bg-white rounded-xl shadow-sm flex-1 overflow-hidden">
        
        {/* Vertical Scroll */}
        <div className="h-full overflow-y-auto">
          
          {/* Horizontal Scroll for Mobile */}
          <div className="w-full overflow-x-auto">
            
            <table className="min-w-[900px] w-full text-left">
              
              <thead className="bg-[#DCE4EA] text-gray-600 text-xs uppercase tracking-wide sticky top-0 z-10">
                <tr>
                  <th className="px-6 py-4">Retailer ID</th>
                  <th className="px-6">Shop Name</th>
                  <th className="px-6">Owner</th>
                  <th className="px-6">Contact</th>
                  <th className="px-6">KYC Status</th>
                  <th className="px-6">Actions</th>
                </tr>
              </thead>

              <tbody className="text-sm text-gray-700">
                {filteredRetailers.map((retailer, index) => (
                  <tr
                    key={index}
                    className={`${
                      index % 2 === 0 ? "bg-white" : "bg-[#F7F9FB]"
                    } hover:bg-[#EEF2F6] transition`}
                  >
                    <td className="px-6 py-5 font-semibold whitespace-nowrap">
                      {retailer.id}
                    </td>
                    <td className="px-6 whitespace-nowrap">
                      {retailer.shop}
                    </td>
                    <td className="px-6 whitespace-nowrap">
                      {retailer.owner}
                    </td>
                    <td className="px-6 whitespace-nowrap">
                      <div>{retailer.phone}</div>
                      <div className="text-xs text-gray-500">
                        {retailer.email}
                      </div>
                    </td>
                    <td className="px-6 whitespace-nowrap">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          retailer.status === "Approved"
                            ? "bg-green-100 text-green-600"
                            : "bg-orange-100 text-orange-600"
                        }`}
                      >
                        {retailer.status}
                      </span>
                    </td>
                    <td className="px-6 whitespace-nowrap">
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
    </div>
  );
}