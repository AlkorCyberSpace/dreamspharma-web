import React, { useState } from "react";
import { Eye, Calendar, ChevronDown } from "lucide-react";

export default function CreditNotes() {
    const [fromDate, setFromDate] = useState("12.2025");
    const [toDate, setToDate] = useState("12.2025");

    const creditNotesData = [
        {
            orderId: "RET001",
            creditNoteId: "RET001",
            referenceInvoice: "INV-2024-0045",
            productName: "Paracetamole",
            quantity: 100,
            returnQuantity: 20,
            status: "Approved",
        },
        {
            orderId: "RET001",
            creditNoteId: "RET001",
            referenceInvoice: "INV-2024-0045",
            productName: "Paracetamole",
            quantity: 100,
            returnQuantity: 30,
            status: "Pending",
        },
        {
            orderId: "RET001",
            creditNoteId: "RET001",
            referenceInvoice: "INV-2024-0045",
            productName: "Paracetamole",
            quantity: 100,
            returnQuantity: 20,
            status: "Approved",
        },
        {
            orderId: "RET001",
            creditNoteId: "RET001",
            referenceInvoice: "INV-2024-0045",
            productName: "Paracetamole",
            quantity: 100,
            returnQuantity: 30,
            status: "Approved",
        },
        {
            orderId: "RET001",
            creditNoteId: "RET001",
            referenceInvoice: "INV-2024-0045",
            productName: "Paracetamole",
            quantity: 100,
            returnQuantity: 20,
            status: "Approved",
        },
        {
            orderId: "RET001",
            creditNoteId: "RET001",
            referenceInvoice: "INV-2024-0045",
            productName: "Paracetamole",
            quantity: 100,
            returnQuantity: 30,
            status: "Approved",
        },
        {
            orderId: "RET001",
            creditNoteId: "RET001",
            referenceInvoice: "INV-2024-0045",
            productName: "Paracetamole",
            quantity: 100,
            returnQuantity: 20,
            status: "Approved",
        },
        {
            orderId: "RET001",
            creditNoteId: "RET001",
            referenceInvoice: "INV-2024-0045",
            productName: "Paracetamole",
            quantity: 100,
            returnQuantity: 30,
            status: "Approved",
        },
    ];

    const getStatusStyle = (status) => {
        switch (status) {
            case "Approved":
                return "bg-[#E6F9F1] text-[#00A360]";
            case "Pending":
                return "bg-[#FFF4ED] text-[#FF8A48]";
            default:
                return "bg-gray-100 text-gray-700";
        }
    };

    return (
        <div className=" ml-2">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <div>
                    <h1 className="text-xl font-semibold text-[#505050]">Credit Note Management</h1>
                    <p className="text-[#8E8E8E] text-sm">
                        Manage credit requests for returned, damaged, or expired products.
                    </p>
                </div>

                <div className="flex flex-col items-start gap-2">
                    <span className="text-[#454545] font-small text-sm">Time Selection:</span>
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <input
                                type="text"
                                value={fromDate}
                                onChange={(e) => setFromDate(e.target.value)}
                                className="border border-[#E2E8F0] rounded-lg px-10 py-2 text-sm text-[#454545] w-36 outline-none focus:ring-1 focus:ring-[#127690]"
                            />
                            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" size={18} />
                        </div>
                        <div className="relative">
                            <input
                                type="text"
                                value={toDate}
                                onChange={(e) => setToDate(e.target.value)}
                                className="border border-[#E2E8F0] rounded-lg px-10 py-2 text-sm text-[#454545] w-36 outline-none focus:ring-1 focus:ring-[#127690]"
                            />
                            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" size={18} />
                        </div>
                        <button className="bg-[#127690] text-white px-8 py-2 rounded-lg font-semibold text-sm hover:bg-[#0e5d72] transition-colors">
                            Apply
                        </button>
                    </div>
                </div>
            </div>

            {/* Table Area */}
            <div className="bg-white rounded-xl shadow-sm border border-[#F1F5F9] overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-[#EBF3F6] text-[#4F5B67] text-[12px] font-semibold uppercase tracking-wider">
                            <tr>
                                <th className="px-3 py-4">ORDER ID</th>
                                <th className="px-3 py-4">CREDIT NOTE ID</th>
                                <th className="px-3 py-4 text-center">REFERENCE INVOICE</th>
                                <th className="px-3 py-4">PRODUCT NAME</th>
                                <th className="px-3 py-4 text-center">QUANTITY</th>
                                <th className="px-3 py-4 text-center">RETURN QUANTITY</th>
                                <th className="px-3 py-4 text-center">STATUS</th>
                                <th className="px-3 py-4 text-center">VIEW</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#F1F5F9]">
                            {creditNotesData.map((note, index) => (
                                <tr key={index} className="hover:bg-[#F8FAFC] transition-colors">
                                    <td className="px-3 py-1 font-semibold text-[#0F172A]">{note.orderId}</td>
                                    <td className="px-3 py-1 text-[#475569]">{note.creditNoteId}</td>
                                    <td className="px-3 py-1 text-[#475569] text-center">{note.referenceInvoice}</td>
                                    <td className="px-3 py-1 text-[#475569] font-medium">{note.productName}</td>
                                    <td className="px-3 py-1 text-[#475569] text-center">{note.quantity}</td>
                                    <td className="px-3 py-1 text-[#475569] text-center">{note.returnQuantity}</td>
                                    <td className="px-3 py-3 text-center">
                                        <span
                                            className={`px-4 py-1.5 rounded-lg text-xs font-bold ${getStatusStyle(
                                                note.status
                                            )}`}
                                        >
                                            {note.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-5 text-center">
                                        <button className="text-[#127690] hover:scale-110 transition-transform">
                                            <Eye size={20} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {/* Horizontal scroll indicator matching the screenshot */}
                <div className="px-2 py-3">
                    <div className="w-full h-1 bg-[#E2E8F0] rounded-full overflow-hidden">
                        <div className="w-[70%] h-full bg-[#94A3B8] rounded-full"></div>
                    </div>
                </div>
            </div>
        </div>
    );
}
