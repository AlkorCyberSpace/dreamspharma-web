import React, { useState, useMemo, useEffect } from "react";
import { Search, ChevronDown, ShieldCheck, Download } from "lucide-react";
import { getAuditLogsAPI } from "../services/allAPI";

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
    const [auditData, setAuditData] = useState([]);

    useEffect(() => {
    const fetchAuditLogs = async () => {
        try {
            const response = await getAuditLogsAPI();

            if (response && response.data) {
                const formatted = response.data.data.map((log) => ({
                    id: log.log_id,
                    action: log.action,
                    performedBy: log.performed_by,
                    targetEntity: log.target_entity,
                    details: log.details,
                    category: log.category,
                    timestamp: log.created_at,
                }));

                setAuditData(formatted);
            }
        } catch (error) {
            console.error("Failed to fetch audit logs:", error);
        }
    };

    fetchAuditLogs();
}, []);

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
}, [search, categoryFilter, auditData]); 
    // const handleExportCSV = () => {
    //     const headers = ["Log ID", "Action", "Performed By", "Target Entity", "Details", "Category", "Timestamp"];
    //     const rows = filtered.map((r) => [
    //         r.id, r.action, r.performedBy, r.targetEntity,
    //         `"${r.details}"`, r.category, r.timestamp,
    //     ]);
    //     const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
    //     const blob = new Blob([csv], { type: "text/csv" });
    //     const url = URL.createObjectURL(blob);
    //     const a = document.createElement("a");
    //     a.href = url;
    //     a.download = "audit_logs.csv";
    //     a.click();
    //     URL.revokeObjectURL(url);
    // };

    return (
        <div className="ml-2 mt-3 ">
            <div className="mb-7 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
                        Audit Logs &amp; System Tracking
                    </h1>
                    <p className="text-sm text-gray-500">
                        Compliance-ready audit trail of all system activities
                    </p>
                </div>

                <div className="flex items-center bg-white border border-[#E5E7EB] rounded-xl px-2 py-1.5 shadow-sm w-full lg:max-w-xl transition-all focus-within:shadow-lg">
                    <div className="flex items-center flex-1 px-2">
                        <Search size={18} className="text-[#9EA2A7] shrink-0" />
                        <input
                            type="text"
                            placeholder="Search by shop name or owner..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-transparent outline-none px-3 text-sm text-[#505050] placeholder:text-[#9EA2A7]"
                        />
                    </div>

                    <div className="relative min-w-[140px]">
                        <select
                            value={categoryFilter}
                            onChange={(e) => setCategoryFilter(e.target.value)}
                            className="appearance-none w-full bg-white border border-[#E5E7EB] rounded-xl px-4 py-1.5 pr-10 text-sm text-[#505050] font-medium focus:outline-none cursor-pointer"
                        >
                            {CATEGORIES.map((c) => (
                                <option key={c} value={c}>
                                    {c === "All" ? "All Status" : c}
                                </option>
                            ))}
                        </select>
                        <ChevronDown
                            size={16}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9EA2A7] pointer-events-none"
                        />
                    </div>
                </div>
            </div>          

            {/* ── Table ── */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col mb-5">
                <div className="overflow-x-auto overflow-y-auto max-h-[500px]">
                    <table className="min-w-[900px] w-full text-left">
                        <thead className="bg-[#DCE4EA] text-gray-500 text-[11px] uppercase font-bold tracking-wider sticky top-0 z-10">
                            <tr>
                                <th className="px-5 py-4">Log ID</th>
                                <th className="px-5">Action</th>
                                <th className="px-5">Performed By</th>
                                <th className="px-5">Target Entity</th>
                                <th className="px-5">Details</th>
                                <th className="px-5">Category</th>
                                <th className="px-5">Timestamp</th>
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
                                        <td className="px-5 py-2.5 font-semibold text-[#127690] whitespace-nowrap">
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
                                            {new Date(item.timestamp).toLocaleString()}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Footer */}
                <div className="px-6 py-3  text-xs text-gray-400 flex items-center justify-between">
                    <span>
                        {/* Showing <span className="font-medium text-gray-600">{filtered.length}</span> of{" "} */}
                        {/* <span className="font-medium text-gray-600">{auditData.length}</span> entries */}
                    </span>
                    <span>Logs are retained for 90 days.</span>
                </div>
            </div>
        </div>
    );
}
