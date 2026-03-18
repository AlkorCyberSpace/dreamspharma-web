import React, { useState, useMemo } from "react";
import { Search, ChevronDown, ShieldCheck, Download } from "lucide-react";

const auditData = [
    {
        id: "AUD-001",
        action: "KYC Approved",
        performedBy: "Admin User",
        targetEntity: "MedPlus Pharmacy (RET001)",
        details: "All documents verified and approved",
        category: "KYC",
        timestamp: "2026-03-13 09:15:22",
    },
    {
        id: "AUD-002",
        action: "Refund Approved",
        performedBy: "Admin User",
        targetEntity: "REF-Q01",
        details: "Approved refund of ₹5,420 for damaged product",
        category: "Refund",
        timestamp: "2026-03-13 09:42:05",
    },
    {
        id: "AUD-003",
        action: "Order Synced",
        performedBy: "System",
        targetEntity: "ORD-2026-003",
        details: "Order successfully synced to ERP system",
        category: "ERP",
        timestamp: "2026-03-13 10:01:47",
    },
    {
        id: "AUD-004",
        action: "KYC Rejected",
        performedBy: "Admin User",
        targetEntity: "Life Care Pharmacy (RET005)",
        details: "Drug license expired – Rejected",
        category: "KYC",
        timestamp: "2026-03-13 10:28:33",
    },
    {
        id: "AUD-005",
        action: "Refund Rejected",
        performedBy: "Finance Admin",
        targetEntity: "REF-005",
        details: "Insufficient evidence for quality issue claim",
        category: "Refund",
        timestamp: "2026-03-13 11:05:18",
    },
    {
        id: "AUD-006",
        action: "ERP Sync Failed",
        performedBy: "System",
        targetEntity: "Orders Batch-452",
        details: "Connection timeout – Retry scheduled",
        category: "ERP",
        timestamp: "2026-03-13 11:30:00",
    },
    {
        id: "AUD-007",
        action: "Admin Login",
        performedBy: "Admin User",
        targetEntity: "System",
        details: "Successful login from IP 192.168.1.100",
        category: "System",
        timestamp: "2026-03-13 12:00:45",
    },
    {
        id: "AUD-008",
        action: "Product Updated",
        performedBy: "Admin User",
        targetEntity: "Paracetamol 500mg",
        details: "Stock quantity updated from 200 to 450 units",
        category: "Products",
        timestamp: "2026-03-13 12:15:10",
    },
    {
        id: "AUD-009",
        action: "Offer Created",
        performedBy: "Admin User",
        targetEntity: "OFF-004",
        details: "New offer 'Summer Sale 30% off' created",
        category: "Offers",
        timestamp: "2026-03-13 12:30:55",
    },
    {
        id: "AUD-010",
        action: "Password Reset",
        performedBy: "Admin User",
        targetEntity: "System",
        details: "Admin password reset successfully",
        category: "System",
        timestamp: "2026-03-13 12:58:00",
    },
];

const CATEGORIES = ["All", "KYC", "Refund", "ERP", "System", "Products", "Offers"];

const categoryStyle = (cat) => {
    switch (cat) {
        case "KYC":
            return "bg-blue-100 text-blue-700";
        case "Refund":
            return "bg-orange-100 text-orange-600";
        case "ERP":
            return "bg-purple-100 text-purple-700";
        case "System":
            return "bg-gray-200 text-gray-600";
        case "Products":
            return "bg-teal-100 text-teal-700";
        case "Offers":
            return "bg-yellow-100 text-yellow-700";
        default:
            return "bg-gray-100 text-gray-500";
    }
};

export default function AuditLogs() {
    const [search, setSearch] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("All");

    const filtered = useMemo(() => {
        const q = search.toLowerCase();
        return auditData.filter((item) => {
            const matchSearch =
                item.id.toLowerCase().includes(q) ||
                item.action.toLowerCase().includes(q) ||
                item.performedBy.toLowerCase().includes(q) ||
                item.targetEntity.toLowerCase().includes(q) ||
                item.details.toLowerCase().includes(q);
            const matchCat =
                categoryFilter === "All" || item.category === categoryFilter;
            return matchSearch && matchCat;
        });
    }, [search, categoryFilter]);

    const handleExportCSV = () => {
        const headers = ["Log ID", "Action", "Performed By", "Target Entity", "Details", "Category", "Timestamp"];
        const rows = filtered.map((r) => [
            r.id, r.action, r.performedBy, r.targetEntity,
            `"${r.details}"`, r.category, r.timestamp,
        ]);
        const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "audit_logs.csv";
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="ml-5 mt-5 border-l-2 border-gray-100">
            {/* ── Header ── */}
            <div className="mb-4 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
                        Audit Logs &amp; System Tracking
                    </h1>
                    <p className="text-sm text-gray-500">
                        Compliance-ready audit trail of all system activities
                    </p>
                </div>

                <div className="flex items-center gap-3 flex-wrap">
                    {/* Search */}
                    <div className="flex items-center bg-white border border-[#E5E7EB] rounded-xl px-3 py-1.5 shadow-sm focus-within:shadow-lg transition-all">
                        <Search size={16} className="text-[#9EA2A7] shrink-0" />
                        <input
                            type="text"
                            placeholder="Search by shop name or owner..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="ml-2 w-52 bg-transparent outline-none text-sm text-[#505050] placeholder:text-[#9EA2A7]"
                        />
                    </div>

                    {/* Category Filter */}
                    <div className="relative">
                        <select
                            value={categoryFilter}
                            onChange={(e) => setCategoryFilter(e.target.value)}
                            className="appearance-none bg-white border border-[#E5E7EB] rounded-xl px-4 py-2 pr-8 text-sm text-[#505050] font-medium focus:outline-none focus:ring-2 focus:ring-teal-400 cursor-pointer"
                        >
                            {CATEGORIES.map((c) => (
                                <option key={c} value={c}>
                                    {c === "All" ? "All Status" : c}
                                </option>
                            ))}
                        </select>
                        <ChevronDown
                            size={14}
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                        />
                    </div>

                    {/* Export Button */}
                    <button
                        onClick={handleExportCSV}
                        className="flex items-center gap-2 bg-white border border-[#E5E7EB] hover:bg-gray-50 text-[#505050] text-sm font-medium px-4 py-2 rounded-xl shadow-sm transition-colors"
                    >
                        <Download size={15} />
                        Export CSV
                    </button>
                </div>
            </div>          

            {/* ── Table ── */}
            <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
                <div className="overflow-x-auto overflow-y-auto max-h-[500px]">
                    <table className="min-w-[900px] w-full text-left">
                        <thead className="bg-[#DCE4EA] text-gray-600 text-xs uppercase tracking-wide sticky top-0 z-10">
                            <tr>
                                <th className="px-6 py-4">Log ID</th>
                                <th className="px-6">Action</th>
                                <th className="px-6">Performed By</th>
                                <th className="px-6">Target Entity</th>
                                <th className="px-6">Details</th>
                                <th className="px-6">Category</th>
                                <th className="px-6">Timestamp</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm text-gray-700">
                            {filtered.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-10 text-center text-gray-400">
                                        No audit entries found.
                                    </td>
                                </tr>
                            ) : (
                                filtered.map((item, index) => (
                                    <tr
                                        key={item.id}
                                        className={`${index % 2 === 0 ? "bg-white" : "bg-[#F4F6F8]"
                                            } hover:bg-[#EEF2F6] transition`}
                                    >
                                        <td className="px-6 py-3.5 font-semibold text-[#127690] whitespace-nowrap">
                                            {item.id}
                                        </td>
                                        <td className="px-6 font-medium whitespace-nowrap">{item.action}</td>
                                        <td className="px-6 text-gray-500 whitespace-nowrap">{item.performedBy}</td>
                                        <td className="px-6 whitespace-nowrap">{item.targetEntity}</td>
                                        <td className="px-6 text-gray-500 max-w-[260px] truncate" title={item.details}>
                                            {item.details}
                                        </td>
                                        <td className="px-6 whitespace-nowrap">
                                            <span
                                                className={`px-3 py-1 rounded-full text-xs font-semibold ${categoryStyle(
                                                    item.category
                                                )}`}
                                            >
                                                {item.category}
                                            </span>
                                        </td>
                                        <td className="px-6 text-gray-400 text-xs whitespace-nowrap">
                                            {item.timestamp}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Footer */}
                <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 text-xs text-gray-400 flex items-center justify-between">
                    <span>
                        Showing <span className="font-medium text-gray-600">{filtered.length}</span> of{" "}
                        <span className="font-medium text-gray-600">{auditData.length}</span> entries
                    </span>
                    <span>Logs are retained for 90 days.</span>
                </div>
            </div>
        </div>
    );
}
