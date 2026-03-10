import React, { useState } from "react";
import { Search, Package, AlertTriangle, Archive } from "lucide-react";

/* ── Summary Card Helper ── */
function SummaryCard({ title, value, icon, bgClass, textClass, iconClass, blobColor1, blobColor2 }) {
    return (
        <div className={`relative overflow-hidden rounded-2xl p-6 ${bgClass} flex-1 min-h-[100px] shadow-[0_4px_20px_rgba(0,0,0,0.03)] border border-white/40`}>
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

export default function Products() {
    const [search, setSearch] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("All Categories");
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 5;

    // Mock Data
    const productsData = [
        { id: "PRD-001", name: "Paracetamol 500mg (Strip of 15)", category: "Analgesics", mrp: "₹35", stock: 5420, warehouse: "Warehouse A" },
        { id: "PRD-002", name: "Amoxicillin 250mg Capsules", category: "Antibiotics", mrp: "₹220", stock: 2340, warehouse: "Warehouse A" },
        { id: "PRD-003", name: "Cetirizine 10mg Tablets", category: "Antihistamines", mrp: "₹60", stock: 3200, warehouse: "Warehouse B" },
        { id: "PRD-004", name: "Omeprazole 20mg Capsules", category: "Antacids", mrp: "₹110", stock: 150, warehouse: "Warehouse A", lowStock: true },
        { id: "PRD-005", name: "Metformin 500mg Tablets", category: "Antidiabetics", mrp: "₹150", stock: 1890, warehouse: "Warehouse B" },
        { id: "PRD-006", name: "Atorvastatin 10mg Tablets", category: "Cardiovascular", mrp: "₹125", stock: 80, warehouse: "Warehouse A", lowStock: true },
        { id: "PRD-007", name: "Paracetamol 500mg (Strip of 15)", category: "Analgesics", mrp: "₹35", stock: 5420, warehouse: "Warehouse A" },
        { id: "PRD-008", name: "Aspirin 75mg Tablets", category: "Analgesics", mrp: "₹45", stock: 1200, warehouse: "Warehouse B" },
        { id: "PRD-009", name: "Loratadine 10mg Tablets", category: "Antihistamines", mrp: "₹85", stock: 450, warehouse: "Warehouse A" },
        { id: "PRD-010", name: "Losartan 50mg Tablets", category: "Cardiovascular", mrp: "₹210", stock: 3000, warehouse: "Warehouse B" },
    ];

    const categories = ["All Categories", "Analgesics", "Antibiotics", "Antihistamines", "Antacids", "Antidiabetics", "Cardiovascular"];

    const filteredProducts = productsData.filter((product) => {
        const matchesSearch = product.name.toLowerCase().includes(search.toLowerCase()) || product.id.toLowerCase().includes(search.toLowerCase());
        const matchesCategory = categoryFilter === "All Categories" || product.category === categoryFilter;
        return matchesSearch && matchesCategory;
    });

    // Pagination Logic
    const totalPages = Math.ceil(filteredProducts.length / itemsPerPage);
    const paginatedProducts = filteredProducts.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    const handleSearch = (e) => {
        setSearch(e.target.value);
        setCurrentPage(1);
    };

    const handleCategoryChange = (cat) => {
        setCategoryFilter(cat);
        setCurrentPage(1);
        setIsDropdownOpen(false);
    };

    return (
        <div className="h-full overflow-hidden flex flex-col ">

            {/* Header Section */}
            <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4 ">
                <div>
                    <h1 className="text-xl sm:text-xl md:text-xl font-semibold text-[#505050]">
                        Product & Inventory View
                    </h1>
                    <p className="text-xs sm:text-sm text-[#505050] mt-1">
                        Real-time ERP-synced product catalog and stock levels
                    </p>
                </div>

                {/* Search & Filter */}
                <div className="flex items-center bg-white border border-gray-200 rounded-xl px-4 py-1.5 shadow-sm w-full md:w-[400px] relative">
                    <Search size={20} className="text-gray-400 shrink-0" />
                    <input
                        type="text"
                        placeholder="Search by product name or ID..."
                        value={search}
                        onChange={handleSearch}
                        className="flex-1 bg-transparent border-none outline-none px-3 text-sm text-[#505050] placeholder:text-[#9EA2A7]"
                    />

                    {/* Custom Dropdown */}
                    <div className="relative border border-gray-100 rounded-lg bg-white">
                        <button
                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                            className="flex items-center gap-2 px-4 py-1.5 text-[#505050] text-sm font-medium hover:bg-gray-50 rounded-lg transition-colors whitespace-nowrap min-w-[140px] justify-between"
                        >
                            {categoryFilter}
                            <svg
                                width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                                className={`text-gray-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
                            >
                                <path d="m6 9 6 6 6-6" />
                            </svg>
                        </button>

                        {isDropdownOpen && (
                            <>
                                {/* Backdrop to close dropdown */}
                                <div className="fixed inset-0 z-40" onClick={() => setIsDropdownOpen(false)} />

                                <div className="absolute top-full right-0 mt-2 w-56 bg-white border border-gray-100 rounded-xl shadow-xl z-50 py-2 animate-in fade-in zoom-in duration-200">
                                    {categories.map((cat) => (
                                        <button
                                            key={cat}
                                            onClick={() => handleCategoryChange(cat)}
                                            className={`w-full text-left px-4 py-2.5 text-[13px] transition-colors hover:bg-[#EEF1F5] ${categoryFilter === cat ? 'bg-[#EEF1F5] text-[#000000] font-semibold' : 'text-[#505050]'
                                                }`}
                                        >
                                            {cat}
                                        </button>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="flex flex-col md:flex-row gap-4 lg:gap-6 mb-3">
                <SummaryCard
                    title="Total Products"
                    value="10"
                    icon={<Package size={20} />}
                    bgClass="bg-[#f2ecbb]"
                    textClass="text-[#846018]"
                    iconClass=""
                    blobColor1="bg-[#D08700]"
                    blobColor2="bg-[#733E0A]"
                />
                <SummaryCard
                    title="Low Stock Items"
                    value="2"
                    icon={<AlertTriangle size={20} />}
                    bgClass="bg-[#d8e9ff]"
                    textClass="text-[#1D4ED8]"
                    iconClass="text-blue-600"
                    blobColor1="bg-[#83ACE5]"
                    blobColor2="bg-[#1447EA]"
                />
                <SummaryCard
                    title="Total Warehouses"
                    value="4"
                    icon={<Archive size={20} />}
                    bgClass="bg-[#e9fedf]"
                    textClass="text-[#207238]"
                    iconClass=""
                    blobColor1="bg-[#A3FF63]"
                    blobColor2="bg-[#33CB6C]"
                />
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.04)] border border-gray-100 flex-1 overflow-hidden flex flex-col">
                <div className="flex-1 overflow-auto">
                    <table className="min-w-[900px] w-full text-left border-collapse">
                        <thead className="bg-[#e7f1f4] text-[#505050] text-xs font-semibold uppercase tracking-wider sticky top-0 z-10">
                            <tr>
                                <th className="px-6 py-3 font-medium">PRODUCT ID</th>
                                <th className="px-6 font-medium">PRODUCT NAME</th>
                                <th className="px-6 font-medium">CATEGORY</th>
                                <th className="px-6 font-medium">MRP</th>
                                <th className="px-6 font-medium">STOCK</th>
                                <th className="px-6 font-medium">WAREHOUSE</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm text-gray-700 divide-y divide-gray-50">
                            {paginatedProducts.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-10 text-center text-gray-400">
                                        No products found.
                                    </td>
                                </tr>
                            ) : (
                                paginatedProducts.map((product, index) => (
                                    <tr
                                        key={index}
                                        className={`${index % 2 === 0 ? "bg-white" : "bg-[#F7F9FB]"} hover:bg-[#EEF2F6] transition`}
                                    >
                                        <td className="px-6 py-2 text-[12px] font-semibold text-gray-800 whitespace-nowrap">{product.id}</td>
                                        <td className="px-6 text-[13px] text-[#000000] font-medium">{product.name}</td>
                                        <td className="px-6 text-[13px] text-[#000000]">{product.category}</td>
                                        <td className="px-6 text-[13px] text-[#000000]">{product.mrp}</td>
                                        <td className="px-6 text-[13px] whitespace-nowrap">
                                            {product.lowStock ? (
                                                <span className="text-red-600 font-bold flex items-center gap-1.5">
                                                    {product.stock}
                                                    <AlertTriangle size={14} className="text-red-500" />
                                                </span>
                                            ) : (
                                                <span className="text-[#000000]">{product.stock}</span>
                                            )}
                                        </td>
                                        <td className="px-6 text-[13px] text-[#000000]">{product.warehouse}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination Controls */}
                <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between bg-white bg-opacity-50">
                    <div className="text-sm text-gray-500 font-medium">
                        Showing <span className="text-gray-900">{(currentPage - 1) * itemsPerPage + 1}</span> to <span className="text-gray-900">{Math.min(currentPage * itemsPerPage, filteredProducts.length)}</span> of <span className="text-gray-900">{filteredProducts.length}</span> results
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                            disabled={currentPage === 1}
                            className={`px-4 py-1.5 rounded-lg border border-gray-200 text-sm font-semibold transition-all ${currentPage === 1 ? 'bg-gray-50 text-gray-300 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 active:scale-95 shadow-sm'}`}
                        >
                            Previous
                        </button>
                        <div className="flex items-center gap-1 px-3">
                            <span className="text-sm font-bold text-[#505050]">Page {currentPage}</span>
                            <span className="text-sm text-gray-400 font-medium">of {totalPages || 1}</span>
                        </div>
                        <button
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            disabled={currentPage === totalPages || totalPages === 0}
                            className={`px-4 py-1.5 rounded-lg border border-gray-200 text-sm font-semibold transition-all ${currentPage === totalPages || totalPages === 0 ? 'bg-gray-50 text-gray-300 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50 hover:border-gray-300 active:scale-95 shadow-sm'}`}
                        >
                            Next
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
