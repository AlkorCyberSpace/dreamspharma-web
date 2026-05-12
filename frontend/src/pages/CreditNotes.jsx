import React, { useEffect, useState } from "react";
import { Eye, Calendar, X, Package, FileText, User, Tag, Hash, RefreshCw, DollarSign, AlertCircle, ClipboardList, Clock, CheckCircle, XCircle, ChevronDown, Search } from "lucide-react";
import { getCreditNotesAPI, approveCreditNoteAPI, rejectCreditNoteAPI } from "../services/allAPI";

export default function CreditNotes() {
    const [fromDate, setFromDate] = useState("");
    const [toDate, setToDate] = useState("");
    const [creditNotesData, setCreditNotesData] = useState([]);
    const [rawData, setRawData] = useState([]);
    const [statusFilter, setStatusFilter] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedNote, setSelectedNote] = useState(null);
    const [isApproving, setIsApproving] = useState(false);
    const [isRejecting, setIsRejecting] = useState(false);
    const [showRejectDialog, setShowRejectDialog] = useState(false);
    const [rejectionReason, setRejectionReason] = useState("");

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage] = useState(10);

    const fetchCreditNotes = async () => {
        try {
            const params = {};
            if (statusFilter) params.status = statusFilter;
            if (searchQuery) params.search = searchQuery;
            if (fromDate) params.date_from = fromDate;
            if (toDate) params.date_to = toDate;

            const response = await getCreditNotesAPI(params);
            console.log(response);
            if (response.data?.success) {
                setRawData(response.data.data);
                const formattedData = response.data.data.map(item => ({
                    orderId: item.order_id || "-",
                    creditNoteId: item.credit_note_id,
                    referenceInvoice: item.reference_invoice || "-",
                    productName: item.product_name,
                    quantity: item.quantity,
                    returnQuantity: item.quantity_to_return,
                    status: item.status_display,
                    createdAt: item.created_at,
                    _raw: item
                }));
                setCreditNotesData(formattedData);
            }
        } catch (error) {
            console.log(error);
        }
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            fetchCreditNotes();
        }, searchQuery ? 500 : 0);
        return () => clearTimeout(timer);
    }, [searchQuery, statusFilter, fromDate, toDate]);

    // Pagination logic
    const totalPages = Math.ceil(creditNotesData.length / itemsPerPage);
    const indexOfLastItem = currentPage * itemsPerPage;
    const indexOfFirstItem = indexOfLastItem - itemsPerPage;
    const currentItems = creditNotesData.slice(indexOfFirstItem, indexOfLastItem);

    const paginate = (pageNumber) => setCurrentPage(pageNumber);

    // Reset pagination when data changes
    useEffect(() => {
        setCurrentPage(1);
    }, [creditNotesData.length]);

    const getStatusStyle = (status) => {
        switch (status) {
            case "Approved":
                return "bg-[#E6F9F1] text-[#00A360]";
            case "Pending":
                return "bg-[#FFF4ED] text-[#FF8A48]";
            case "Rejected":
                return "bg-red-50 text-red-600";
            default:
                return "bg-gray-100 text-gray-700";
        }
    };

    const getStatusBadgeModal = (status) => {
        switch (status) {
            case "APPROVED":
            case "Approved":
                return "bg-emerald-100 text-emerald-700 border border-emerald-200";
            case "PENDING":
            case "Pending":
                return "bg-amber-100 text-amber-700 border border-amber-200";
            case "REJECTED":
            case "Rejected":
                return "bg-red-100 text-red-700 border border-red-200";
            default:
                return "bg-gray-100 text-gray-600 border border-gray-200";
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return "—";
        const d = new Date(dateStr);
        return d.toLocaleString("en-IN", {
            day: "2-digit", month: "short", year: "numeric"
        });
    };

    const handleApprove = async () => {
        try {
            setIsApproving(true);

            // Call API to approve credit note using credit_note_id
            const response = await approveCreditNoteAPI(selectedNote.credit_note_id, {
                admin_remarks: "Approved by admin"
            });

            if (response.data?.success) {
                // Update the selected note status
                const updatedNote = {
                    ...selectedNote,
                    status: "APPROVED",
                    status_display: "Approved"
                };
                setSelectedNote(updatedNote);

                // Refresh the credit notes list
                await fetchCreditNotes();
            }

            setIsApproving(false);
        } catch (error) {
            console.log("Error approving credit note:", error);
            setIsApproving(false);
        }
    };

    const handleRejectSubmit = async () => {
        if (!rejectionReason.trim()) {
            alert("Please enter a rejection reason");
            return;
        }

        try {
            setIsRejecting(true);

            // Call API to reject credit note
            const response = await rejectCreditNoteAPI(selectedNote.credit_note_id, {
                admin_remarks: rejectionReason
            });

            if (response.data?.success) {
                // Update the selected note status
                const updatedNote = {
                    ...selectedNote,
                    status: "REJECTED",
                    status_display: "Rejected",
                    admin_remarks: rejectionReason
                };
                setSelectedNote(updatedNote);

                // Refresh the credit notes list
                await fetchCreditNotes();

                // Close the reject dialog
                setShowRejectDialog(false);
                setRejectionReason("");
            }

            setIsRejecting(false);
        } catch (error) {
            console.log("Error rejecting credit note:", error);
            setIsRejecting(false);
        }
    };

    const DetailRow = ({ icon: Icon, label, value, highlight }) => (
        <div className="flex items-start gap-3 py-3 border-b border-[#F1F5F9] last:border-0">
            <div className="mt-0.5 p-1.5 rounded-md bg-[#EBF3F6] flex-shrink-0">
                <Icon size={14} className="text-[#127690]" />
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#94A3B8]">{label}</p>
                <p className={`text-sm mt-0.5 font-medium break-words ${highlight ? "text-[#127690]" : "text-[#1E293B]"}`}>
                    {value || "—"}
                </p>
            </div>
        </div>
    );

    return (
        <div className="ml-2 mt-2">
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-4 gap-4">
                <div>
                    <h1 className="text-xl font-semibold text-[#505050]">Credit Note Management</h1>
                    <p className="text-[#8E8E8E] text-sm">
                        Manage credit requests for returned, damaged, or expired products.
                    </p>
                </div>

                <div className="w-full lg:w-auto">
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center bg-white border border-[#E2E8F0] rounded-2xl p-1 w-full lg:min-w-[500px] shadow-sm gap-2 sm:gap-0">
                        {/* Search Icon & Input */}
                        <div className="flex items-center gap-2 flex-1 px-3 py-1.5 sm:py-0">
                            <Search size={16} className="text-[#94A3B8] flex-shrink-0" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full bg-transparent border-none outline-none text-xs text-[#454545] placeholder-[#94A3B8]"
                                placeholder="Search by order id or product name..."
                            />
                        </div>

                        {/* Divider */}
                        <div className="hidden sm:block w-px h-8 bg-[#E2E8F0] mx-1"></div>

                        {/* Status Filter */}
                        <div className="relative min-w-[100px] px-1 sm:px-0">
                            <select
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                                className="w-full pl-6 sm:pl-4 pr-8 py-2 border sm:border-none border-[#E2E8F0] rounded-xl sm:rounded-none text-xs text-[#00000] outline-none bg-white appearance-none cursor-pointer hover:bg-gray-50 transition-colors"
                            >
                                <option value="">All Statuses</option>
                                <option value="PENDING">Pending</option>
                                <option value="APPROVED">Approved</option>
                                <option value="REJECTED">Rejected</option>
                            </select>
                            <ChevronDown className="absolute right-5 sm:right-3 top-1/2 -translate-y-1/2 text-[#94A3B8] pointer-events-none" size={14} />
                        </div>

                        {/* Divider */}
                        <div className="hidden sm:block w-px h-8 bg-[#E2E8F0] mx-1"></div>

                        {/* Date Range Selection */}
                        <div className="flex items-center justify-between sm:justify-start gap-1 px-3 py-2 sm:py-0 bg-[#F8FAFC] sm:bg-transparent rounded-xl sm:rounded-none mx-2 sm:mx-0">
                            <div className="flex items-center gap-1">
                                <Calendar className="text-[#94A3B8] flex-shrink-0" size={14} />
                                <input
                                    type={fromDate ? "date" : "text"}
                                    onFocus={(e) => {
                                        e.target.type = "date";
                                        if (e.target.showPicker) e.target.showPicker();
                                    }}
                                    onClick={(e) => {
                                        if (e.target.showPicker) e.target.showPicker();
                                    }}
                                    onBlur={(e) => (e.target.type = fromDate ? "date" : "text")}
                                    placeholder="From"
                                    value={fromDate}
                                    onChange={(e) => setFromDate(e.target.value)}
                                    className="px-1 py-1 bg-transparent text-xs text-[#00000] outline-none cursor-pointer w-[80px]"
                                />
                            </div>
                            <span className="text-gray-400 text-[10px] font-medium uppercase">-</span>
                            <div className="flex items-center gap-1">
                                <input
                                    type={toDate ? "date" : "text"}
                                    onFocus={(e) => {
                                        e.target.type = "date";
                                        if (e.target.showPicker) e.target.showPicker();
                                    }}
                                    onClick={(e) => {
                                        if (e.target.showPicker) e.target.showPicker();
                                    }}
                                    onBlur={(e) => (e.target.type = toDate ? "date" : "text")}
                                    placeholder="To"
                                    value={toDate}
                                    onChange={(e) => setToDate(e.target.value)}
                                    className="px-1 py-1 bg-transparent text-xs text-[#00000] outline-none cursor-pointer w-[80px]"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Table Area - Desktop */}
            <div className="hidden lg:block bg-white rounded-xl shadow-sm border border-[#F1F5F9] overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-[#EBF3F6] text-[#4F5B67] text-[12px] font-semibold uppercase tracking-wider">
                            <tr>
                                <th className="px-2 py-4">ORDER ID</th>
                                <th className="px-1 py-4 ">CREDIT NOTE ID</th>
                                <th className="px-3 py-4">DATE</th>
                                <th className="px-3 py-4 text-center">REFERENCE INVOICE</th>
                                <th className="px-3 py-4">PRODUCT NAME</th>
                                <th className="px-3 py-4 text-center">QUANTITY</th>
                                <th className="px-1 py-4 text-center">RETURN QUANTITY</th>
                                <th className="px-3 py-4 text-center">STATUS</th>
                                <th className="px-3 py-4 text-center">VIEW</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#F1F5F9]">
                            {currentItems.map((note, index) => (
                                <tr key={index} className="hover:bg-[#F8FAFC] transition-colors">
                                    <td className="px-2 py-2 text-sm font-semibold text-[#127690]">{note.orderId}</td>
                                    <td className="px-2  py-1 text-[#000000] text-sm">{note.creditNoteId}</td>
                                    <td className="px-1 py-1 text-[#1c2025] text-sm ">{formatDate(note.createdAt)}</td>
                                    <td className="px-2 py-1 text-[#000000] text-sm text-center">{note.referenceInvoice}</td>
                                    <td className="px-3 py-1 text-[#000000] text-sm">{note.productName}</td>
                                    <td className="px-3 py-1 text-[#000000] text-sm text-center">{note.quantity}</td>
                                    <td className="px-3 py-1 text-[#000000] text-sm text-center">{note.returnQuantity}</td>
                                    <td className="px-3 py-1 text-center">
                                        <span className={`px-4 py-1.5 rounded-lg text-xs font-bold ${getStatusStyle(note.status)}`}>
                                            {note.status}
                                        </span>
                                    </td>
                                    <td className="px-3 py-1 text-center">
                                        <button
                                            onClick={() => setSelectedNote(note._raw)}
                                            className="text-[#127690] hover:scale-110 transition-transform"
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

            {/* Card Layout - Mobile & Tablet */}
            <div className="lg:hidden space-y-3">
                {currentItems.map((note, index) => (
                    <div key={index} className="bg-white rounded-lg shadow-sm border border-[#F1F5F9] p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-3">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Order ID</p>
                                <p className="text-sm font-semibold text-[#0F172A] mt-0.5">{note.orderId}</p>
                            </div>
                            <span className={`px-3 py-1 rounded-lg text-xs font-bold whitespace-nowrap ${getStatusStyle(note.status)}`}>
                                {note.status}
                            </span>
                        </div>

                        <div className="grid grid-cols-2 gap-3 mb-3">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Credit Note ID</p>
                                <p className="text-sm font-medium text-[#475569] mt-0.5">{note.creditNoteId}</p>
                            </div>
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Date</p>
                                <p className="text-xs font-medium text-[#475569] mt-0.5">{formatDate(note.createdAt)}</p>
                            </div>
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Ref. Invoice</p>
                                <p className="text-sm font-medium text-[#475569] mt-0.5">{note.referenceInvoice}</p>
                            </div>
                        </div>

                        <div className="mb-3">
                            <p className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Product</p>
                            <p className="text-sm font-medium text-[#475569] mt-0.5">{note.productName}</p>
                        </div>

                        <div className="grid grid-cols-3 gap-2 mb-3 pt-3 border-t border-[#F1F5F9]">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Qty</p>
                                <p className="text-sm font-medium text-[#475569] mt-0.5">{note.quantity}</p>
                            </div>
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Return Qty</p>
                                <p className="text-sm font-medium text-[#475569] mt-0.5">{note.returnQuantity}</p>
                            </div>
                            <div className="flex justify-end pt-2">
                                <button
                                    onClick={() => setSelectedNote(note._raw)}
                                    className="text-[#127690] hover:scale-110 transition-transform p-2 hover:bg-[#EBF3F6] rounded-lg"
                                >
                                    <Eye size={18} />
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Pagination UI - Numbered Design */}
            {totalPages > 1 && (
                <div className="mt-8 mb-4 flex items-center justify-end px-2">
                    <div className="flex gap-1.5">
                        <button
                            onClick={() => paginate(Math.max(1, currentPage - 1))}
                            disabled={currentPage === 1}
                            className="p-2 rounded-xl border border-gray-200 text-gray-400 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                        >
                            <ChevronDown className="rotate-90" size={16} />
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
                                        onClick={() => paginate(pageNum)}
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
                            onClick={() => paginate(Math.min(totalPages, currentPage + 1))}
                            disabled={currentPage === totalPages}
                            className="p-2 rounded-xl border border-gray-200 text-gray-400 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                        >
                            <ChevronDown className="-rotate-90" size={16} />
                        </button>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {selectedNote && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    style={{ backgroundColor: "rgba(15,23,42,0.55)", backdropFilter: "blur(4px)" }}
                    onClick={() => setSelectedNote(null)}
                >
                    <div
                        className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-y-auto mx-auto"
                        style={{ animation: "modalSlideIn 0.25s ease" }}
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Modal Header */}
                        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 sm:px-5 py-3 sm:py-1.5 border-b border-[#F1F5F9] bg-gradient-to-r from-[#EBF3F6] to-white rounded-t-2xl gap-3 sm:gap-0">
                            <div className="flex-1 min-w-0">
                                <h2 className="text-base sm:text-lg font-medium text-[#1E293B]">Credit Note Details</h2>
                                <p className="text-xs text-[#94A3B8] mt-0.5 truncate">Full information for <span className="font-semibold text-[#127690]">{selectedNote.credit_note_id}</span></p>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className={`px-3 py-1 rounded-full text-xs font-bold ${getStatusBadgeModal(selectedNote.status)}`}>
                                    {selectedNote.status_display || selectedNote.status}
                                </span>
                                <button
                                    onClick={() => setSelectedNote(null)}
                                    className="p-2 rounded-full hover:bg-[#EBF3F6] text-[#64748B] transition-colors"
                                >
                                    <X size={18} />
                                </button>
                            </div>
                        </div>

                        {/* Modal Body — 1 col on mobile, 2 on tablet, 3 on lg */}
                        <div className="px-3 sm:px-6 py-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-6 max-w-7xl">
                            {/* Column 1 — Order */}
                            <div>
                                <p className="text-[11px] font-bold uppercase tracking-widest text-[#127690] mb-1 mt-2">Order Information</p>
                                <DetailRow icon={Hash} label="Order ID" value={selectedNote.order_id} highlight />
                                <DetailRow icon={FileText} label="Credit Note ID" value={selectedNote.credit_note_id} />
                                <DetailRow icon={FileText} label="Reference Invoice" value={selectedNote.reference_invoice} />
                                <div>
                                    <p className="text-[11px] font-bold uppercase tracking-widest text-[#127690] mb-1 mt-2">Timeline</p>
                                    <DetailRow icon={Clock} label="Created At" value={formatDate(selectedNote.created_at)} />
                                    <DetailRow icon={Clock} label="Reviewed At" value={formatDate(selectedNote.reviewed_at)} />

                                    {selectedNote.upload_image && (
                                        <>
                                            <p className="text-[11px] font-bold uppercase tracking-widest text-[#127690] mb-2 mt-4">Uploaded Image</p>
                                            <img
                                                src={selectedNote.upload_image}
                                                alt="Return proof"
                                                className="w-full max-h-40 object-cover rounded-xl border border-[#E2E8F0]"
                                            />
                                        </>
                                    )}
                                </div>
                                {/* <p className="text-[11px] font-bold uppercase tracking-widest text-[#127690] mb-1 mt-4">Product Details</p>
                                <DetailRow icon={Package} label="Product Name" value={selectedNote.product_name} />
                                <DetailRow icon={Tag} label="Sale Rate" value={selectedNote.sale_rate ? `₹ ${selectedNote.sale_rate}` : "—"} />
                                <DetailRow icon={DollarSign} label="Amount" value={selectedNote.amount ? `₹ ${selectedNote.amount}` : "—"} />
                                <DetailRow icon={Hash} label="Quantity" value={selectedNote.quantity} />
                                <DetailRow icon={RefreshCw} label="Quantity to Return" value={selectedNote.quantity_to_return} /> */}
                            </div>

                            {/* Column 2 — Retailer + Reason */}
                            <div>
                                <p className="text-[11px] font-bold uppercase tracking-widest text-[#127690] mb-1 mt-4">Product Details</p>
                                <DetailRow icon={Package} label="Product Name" value={selectedNote.product_name} />
                                <DetailRow icon={Tag} label="Sale Rate" value={selectedNote.sale_rate ? `₹ ${selectedNote.sale_rate}` : "—"} />
                                <DetailRow icon={DollarSign} label="Amount" value={selectedNote.amount ? `₹ ${selectedNote.amount}` : "—"} />
                                <DetailRow icon={Hash} label="Quantity" value={selectedNote.quantity} />
                                <DetailRow icon={RefreshCw} label="Quantity to Return" value={selectedNote.quantity_to_return} />
                            </div>

                            {/* Column 3 — Timeline + Image */}
                            <div>
                                {/* <p className="text-[11px] font-bold uppercase tracking-widest text-[#127690] mb-1 mt-4">Product Details</p>
                                <DetailRow icon={Package} label="Product Name" value={selectedNote.product_name} />
                                <DetailRow icon={Tag} label="Sale Rate" value={selectedNote.sale_rate ? `₹ ${selectedNote.sale_rate}` : "—"} />
                                <DetailRow icon={DollarSign} label="Amount" value={selectedNote.amount ? `₹ ${selectedNote.amount}` : "—"} />
                                <DetailRow icon={Hash} label="Quantity" value={selectedNote.quantity} />
                                <DetailRow icon={RefreshCw} label="Quantity to Return" value={selectedNote.quantity_to_return} />    */}
                                <p className="text-[11px] font-bold uppercase tracking-widest text-[#127690] mb-1 mt-2">Retailer Information</p>
                                <DetailRow icon={User} label="Retailer Name" value={selectedNote.retailer_name} />
                                <DetailRow icon={User} label="Shop Name" value={selectedNote.shop_name || "—"} />

                                <p className="text-[11px] font-bold uppercase tracking-widest text-[#127690] mb-1 mt-4">Return Reason</p>
                                <DetailRow icon={AlertCircle} label="Reason" value={selectedNote.reason_display || selectedNote.reason} />
                                <DetailRow icon={ClipboardList} label="Additional Notes" value={selectedNote.additional_notes || "—"} />
                                <DetailRow icon={ClipboardList} label="Admin Remarks" value={selectedNote.admin_remarks || "—"} />
                            </div>
                        </div>



                        {/* Modal Footer */}
                        <div className="px-3 sm:px-6 py-3 border-t border-[#F1F5F9] flex flex-col-reverse sm:flex-row justify-end gap-2 sm:gap-3">
                            {(selectedNote.status === "PENDING" || selectedNote.status === "Pending") && (
                                <>
                                    <button
                                        onClick={() => setShowRejectDialog(true)}
                                        disabled={isRejecting}
                                        className="w-full sm:w-auto px-4 sm:px-6 py-2 rounded-lg bg-red-500 text-white text-sm font-semibold hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center sm:justify-start gap-2"
                                    >
                                        <XCircle size={16} />
                                        {isRejecting ? "Rejecting..." : "Reject"}
                                    </button>
                                    <button
                                        onClick={handleApprove}
                                        disabled={isApproving}
                                        className="w-full sm:w-auto px-4 sm:px-6 py-2 rounded-lg bg-emerald-500 text-white text-sm font-semibold hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center sm:justify-start gap-2"
                                    >
                                        <CheckCircle size={16} />
                                        {isApproving ? "Approving..." : "Approve"}
                                    </button>
                                </>
                            )}
                            <button
                                onClick={() => setSelectedNote(null)}
                                className="w-full sm:w-auto px-4 sm:px-6 py-2 rounded-lg bg-[#127690] text-white text-sm font-semibold hover:bg-[#0e5d72] transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    </div>

                    {/* Reject Dialog */}
                    {showRejectDialog && (
                        <div
                            className="fixed inset-0 z-[51] flex items-center justify-center p-4"
                            style={{ backgroundColor: "rgba(15,23,42,0.55)", backdropFilter: "blur(4px)" }}
                            onClick={() => setShowRejectDialog(false)}
                        >
                            <div
                                className="bg-white rounded-2xl shadow-2xl w-full max-w-md"
                                style={{ animation: "modalSlideIn 0.25s ease" }}
                                onClick={e => e.stopPropagation()}
                            >
                                <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-[#F1F5F9] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                                    <div className="flex-1">
                                        <h2 className="text-base sm:text-lg font-semibold text-[#1E293B]">Reject Credit Note</h2>
                                        <p className="text-xs text-[#94A3B8] mt-0.5">Enter reason for rejection</p>
                                    </div>
                                    <button
                                        onClick={() => setShowRejectDialog(false)}
                                        className="p-2 rounded-full hover:bg-[#EBF3F6] text-[#64748B] transition-colors flex-shrink-0"
                                    >
                                        <X size={18} />
                                    </button>
                                </div>

                                <div className="px-4 sm:px-6 py-4">
                                    <textarea
                                        value={rejectionReason}
                                        onChange={(e) => setRejectionReason(e.target.value)}
                                        placeholder="Enter rejection reason..."
                                        className="w-full px-4 py-3 border border-[#E2E8F0] rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 resize-none text-sm"
                                        rows="4"
                                    />
                                </div>

                                <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-[#F1F5F9] flex flex-col-reverse sm:flex-row justify-end gap-2 sm:gap-3">
                                    <button
                                        onClick={() => {
                                            setShowRejectDialog(false);
                                            setRejectionReason("");
                                        }}
                                        className="w-full sm:w-auto px-4 sm:px-6 py-2 rounded-lg border border-[#E2E8F0] text-[#64748B] text-sm font-semibold hover:bg-[#F8FAFC] transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleRejectSubmit}
                                        disabled={isRejecting || !rejectionReason.trim()}
                                        className="w-full sm:w-auto px-4 sm:px-6 py-2 rounded-lg bg-red-500 text-white text-sm font-semibold hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        {isRejecting ? "Rejecting..." : "Reject"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    <style>{`
                        @keyframes modalSlideIn {
                            from { opacity: 0; transform: translateY(-16px) scale(0.98); }
                            to   { opacity: 1; transform: translateY(0) scale(1); }
                        }
                    `}</style>
                </div>
            )}
        </div>
    );
}
