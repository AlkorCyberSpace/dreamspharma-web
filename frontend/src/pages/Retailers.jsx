import React, { useEffect, useState } from "react";
import { Search, Filter, Eye, X, CheckCircle, Clock, XCircle, ChevronDown } from "lucide-react";
import { getRetailersAPI, approveRetailerAPI, rejectRetailerAPI } from "../services/allAPI";

/* ── Status badge ── */
function StatusBadge({ status }) {
  const map = {
    APPROVED: { cls: "bg-green-100 text-green-600", icon: <CheckCircle size={13} /> },
    REJECTED: { cls: "bg-red-100 text-red-600", icon: <XCircle size={13} /> },
    PENDING: { cls: "bg-orange-100 text-orange-600", icon: <Clock size={13} /> },
  };
  const cfg = map[status] ?? map.PENDING;
  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.icon} {status}
    </span>
  );
}

/* ── Detail row inside modal ── */
function DetailRow({ label, value }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start gap-1">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide w-40 shrink-0">
        {label}
      </span>
      <span className="text-sm text-gray-900 break-all">{value || "—"}</span>
    </div>
  );
}

/* ── Retailer Detail Modal ── */
function RetailerModal({
  retailer,
  onClose,
  onApprove,
  approving,
  onReject,
  rejecting,
}) {
  if (!retailer) return null;

  const owner = retailer.user
    ? `${retailer.user.first_name || ""} ${retailer.user.last_name || ""}`.trim() || "—"
    : "—";

  const submitted = retailer.submitted_at
    ? new Date(retailer.submitted_at).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    })
    : "—";

  const approved = retailer.approved_at
    ? new Date(retailer.approved_at).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    })
    : "—";

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 backdrop-blur-sm  overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl m-auto relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">
              {retailer.shop_name || "Retailer Details"}
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Retailer ID: #{retailer.id}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <StatusBadge status={retailer.status} />
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2">
          {/* LEFT */}
          <div className="flex flex-col gap-2 p-4 border-r border-gray-100">
            {/* Store Photo */}
            <div>
              <p className="text-xs font-bold text-teal-600 uppercase tracking-widest mb-2">
                Store Photo
              </p>
              {retailer.store_photo ? (
                <a
                  href={`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}${retailer.store_photo}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block group relative"
                >
                  <img
                    src={`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}${retailer.store_photo}`}
                    alt="Store"
                    className="w-full h-44 object-cover rounded-xl border border-gray-100 group-hover:opacity-90 transition-opacity"
                  />
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20 rounded-xl">
                    <Eye className="text-white" size={24} />
                  </div>
                </a>
              ) : (
                <div className="w-full h-44 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400 text-sm">
                  No photo available
                </div>
              )}
            </div>

            {/* KYC Documents */}
            <div className="bg-gray-50 rounded-xl p-3 space-y-2 flex-1">
              <p className="text-xs font-bold text-teal-600 uppercase tracking-widest">
                KYC Documents
              </p>

              <div className="space-y-3">
                <DetailRow label="Drug License No." value={retailer.drug_license_number} />
                <DetailRow label="GST Number" value={retailer.gst_number} />
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Drug License</p>
                  {retailer.drug_license ? (
                    <a
                      href={`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}${retailer.drug_license}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-xs font-medium text-teal-600 hover:bg-gray-50 hover:text-teal-700 transition-colors w-full"
                    >
                      <Eye size={14} />
                      View Document
                    </a>
                  ) : (
                    <div className="w-full py-2 px-3 rounded-lg bg-gray-100 text-[10px] text-gray-400 text-center">No Document</div>
                  )}
                </div>
                <div>
                  <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">ID Proof</p>
                  {retailer.id_proof ? (
                    <a
                      href={`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}${retailer.id_proof}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-xs font-medium text-teal-600 hover:bg-gray-50 hover:text-teal-700 transition-colors w-full"
                    >
                      <Eye size={14} />
                      View Document
                    </a>
                  ) : (
                    <div className="w-full py-2 px-3 rounded-lg bg-gray-100 text-[10px] text-gray-400 text-center">No Document</div>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl p-4 space-y-3">
              <p className="text-xs font-bold text-teal-600 uppercase tracking-widest">
                Timeline
              </p>
              <DetailRow label="Submitted At" value={submitted} />
              <DetailRow label="Approved At" value={approved} />
              {retailer.rejection_reason && (
                <DetailRow label="Rejection Reason" value={retailer.rejection_reason} />
              )}
            </div>
          </div>

          {/* RIGHT */}
          <div className="flex flex-col gap-2 p-4">

            <div className="bg-gray-50 rounded-xl p-4 space-y-3 flex-1">
              <p className="text-xs font-bold text-teal-600 uppercase tracking-widest">
                Shop Information
              </p>

              <DetailRow label="Shop Name" value={retailer.shop_name} />
              <DetailRow label="Shop Phone" value={retailer.shop_phone} />
              <DetailRow label="Shop Email" value={retailer.shop_email} />
              <DetailRow label="Shop Address" value={retailer.shop_address} />
              <DetailRow label="Customer Address" value={retailer.customer_address} />
            </div>

            <div className="bg-gray-50 rounded-xl p-4 space-y-3">
              <p className="text-xs font-bold text-teal-600 uppercase tracking-widest">
                Owner / User
              </p>

              <DetailRow label="Owner Name" value={owner} />
              <DetailRow label="Username" value={retailer.user?.username} />
              <DetailRow label="Email" value={retailer.user?.email} />
            </div>

          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-100 flex justify-end items-center gap-3 shrink-0">
          {retailer.status !== "APPROVED" && (
            <>
              <button
                onClick={onApprove}
                disabled={approving}
                className="px-5 py-2 text-sm font-medium bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white rounded-lg transition-colors flex items-center gap-2"
              >
                <CheckCircle size={16} />
                {approving ? "Approving…" : "Approve"}
              </button>

              <button
                onClick={onReject}
                disabled={rejecting}
                className="px-5 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white rounded-lg transition-colors flex items-center gap-2"
              >
                <XCircle size={16} />
                {rejecting ? "Rejecting…" : "Reject"}
              </button>
            </>
          )}

          <button
            onClick={onClose}
            className="px-5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default function RetailerKYCPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [retailersData2, setRetailersData2] = useState([]);
  const [selectedRetailer, setSelectedRetailer] = useState(null);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);

  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false);

  const fetchRetailers = async () => {
    try {
      const res = await getRetailersAPI();
      setRetailersData2(res.data.results);
      console.log(res.data);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => { fetchRetailers(); }, []);

  const handleApprove = async () => {
    if (!selectedRetailer) return;

    const confirmApprove = window.confirm(`Are you sure you want to approve "${selectedRetailer.shop_name}"?`);
    if (!confirmApprove) return;

    setApproving(true);
    try {
      await approveRetailerAPI(selectedRetailer.user.id);
      await fetchRetailers();
      setSelectedRetailer((prev) => ({ ...prev, status: "APPROVED" }));
    } catch (err) {
      console.error("Approve failed:", err);
      alert("Failed to approve. Please try again.");
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!selectedRetailer) return;
    const reason = prompt("Enter a reason for rejection:");
    if (reason === null) return;
    if (!reason.trim()) {
      alert("Please provide a reason for rejection.");
      return;
    }

    setRejecting(true);
    try {
      await rejectRetailerAPI(selectedRetailer.user.id, { rejection_reason: reason });
      await fetchRetailers();
      setSelectedRetailer((prev) => ({ ...prev, status: "REJECTED", rejection_reason: reason }));
    } catch (err) {
      console.error("Reject failed:", err);
      alert("Failed to reject. Please try again.");
    } finally {
      setRejecting(false);
    }
  };

  const filteredRetailers = retailersData2.filter((retailer) => {
    const ownerName = retailer.user
      ? `${retailer.user.first_name} ${retailer.user.last_name}`.toLowerCase()
      : "";
    const matchesSearch =
      (retailer.shop_name || "").toLowerCase().includes(search.toLowerCase()) ||
      ownerName.includes(search.toLowerCase());
    const matchesStatus =
      statusFilter === "All" || retailer.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusOptions = ["All", "APPROVED", "PENDING", "REJECTED"];

  return (
    <div className="h-full overflow-hidden flex flex-col ml-2 mt-3 ">

      <RetailerModal
        retailer={selectedRetailer}
        onClose={() => setSelectedRetailer(null)}
        onApprove={handleApprove}
        approving={approving}
        onReject={handleReject}
        rejecting={rejecting}
      />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6 ">
        <div className="">
          <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
            Retailer & KYC Management
          </h1>
          <p className="text-xs sm:text-sm  text-[#505050] ">
            Manage pharmacy retailers and KYC verification
          </p>
        </div>

        <div className="flex items-center bg-white border border-[#E5E7EB] rounded-xl px-2.5 py-1.5 shadow-sm w-full lg:max-w-xl transition-all focus-within:shadow-lg">
          <Search size={18} className="text-[#9EA2A7] ml-2 shrink-0" />
          <input
            type="text"
            placeholder="Search by shop name or owner..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1  border-none rounded-lg outline-none text-sm transition-all"
          />

          <div className="relative z-20">
            <button
              onClick={() => setIsStatusDropdownOpen(!isStatusDropdownOpen)}
              className="flex items-center justify-between gap-3 px-4 py-2 border border-[#E5E7EB] rounded-xl bg-white text-[#505050] text-sm font-medium hover:bg-gray-50 transition-colors min-w-[140px]"
            >
              <span>{statusFilter === "All" ? "All Status" : statusFilter.charAt(0) + statusFilter.slice(1).toLowerCase()}</span>
              <ChevronDown
                size={14}
                className={`text-[#9EA2A7] transition-transform duration-200 ${isStatusDropdownOpen ? "rotate-180" : ""}`}
              />
            </button>

            {isStatusDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-30"
                  onClick={() => setIsStatusDropdownOpen(false)}
                />
                <div className="absolute top-full right-0 mt-2 w-48 bg-white border border-[#E5E7EB] rounded-xl shadow-xl z-40 py-2 animate-in fade-in zoom-in duration-200">
                  {statusOptions.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => {
                        setStatusFilter(opt);
                        setIsStatusDropdownOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm transition-colors hover:bg-[#F3F4F6] ${statusFilter === opt ? "bg-[#F3F4F6] text-[#000000] font-semibold" : "text-[#505050]"
                        }`}
                    >
                      {opt === "All" ? "All Status" : opt.charAt(0) + opt.slice(1).toLowerCase()}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto">
          <div className="w-full overflow-x-auto">
            <table className="min-w-[900px] w-full text-left">
              <thead className="bg-[#DCE4EA] text-gray-500 text-[11px] uppercase font-bold tracking-wider sticky top-0 z-10">
                <tr>
                  <th className="px-6 py-4">Retailer ID</th>
                  <th className="px-6">Shop Name</th>
                  <th className="px-6">Owner</th>
                  <th className="px-6">Contact</th>
                  <th className="px-6">Email</th>
                  <th className="px-6">KYC Status</th>
                  <th className="px-6 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="text-md text-gray-700">
                {filteredRetailers.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-10 text-center text-gray-400">
                      No retailers found.
                    </td>
                  </tr>
                ) : (
                  filteredRetailers.map((retailer, index) => {
                    const ownerName = retailer.user
                      ? `${retailer.user.first_name || ""} ${retailer.user.last_name || ""}`.trim() || "—"
                      : "—";
                    return (
                      <tr
                        key={retailer.id ?? index}
                        className={`${index % 2 === 0 ? "bg-white" : "bg-[#F4F6F8]"
                          } hover:bg-[#EEF2F6] transition`}
                      >
                        <td className="px-6 py-3 font-bold text-[#127690] whitespace-nowrap">{retailer.id}</td>
                        <td className="px-6 text-sm text-gray-600 font-medium whitespace-nowrap ">{retailer.shop_name || "—"}</td>
                        <td className="px-6 text-sm text-gray-500 whitespace-nowrap">{ownerName}</td>
                        <td className="px-6 text-sm text-gray-600 whitespace-nowrap">{retailer.shop_phone || "—"}</td>
                        <td className="px-6 text-sm text-gray-500 whitespace-nowrap">{retailer.shop_email || "—"}</td>
                        <td className="px-6 whitespace-nowrap">
                          <StatusBadge status={retailer.status} />
                        </td>
                        <td className="px-6 text-center whitespace-nowrap">
                          <button
                            onClick={() => setSelectedRetailer(retailer)}
                            className="text-[#127690] hover:text-[#127690]/80 transition-colors"
                            title="View details"
                          >
                            <Eye size={20} />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}