import React, { useState, useMemo } from "react";
import {
    Search,
    Plus,
    Pencil,
    Trash2,
    Ban,
    ChevronDown,
    Tag,
    CheckCircle,
    XCircle,
    LayoutTemplate,
} from "lucide-react";
import SummaryCard from "../components/SummaryCard";

const initialOffers = [
    {
        id: "OFF-001",
        title: "Medicines Upto 70% off",
        description: "Health & Wellness Products",
        validFrom: "2026-02-01",
        validTo: "2026-02-28",
        placement: "Homepage Banner",
        status: "Active",
        discount: "70%",
        image: null,
    },
    {
        id: "OFF-002",
        title: "Buy 1 Get 1 Free",
        description: "Special offer on paracetamol",
        validFrom: "2026-02-01",
        validTo: "2026-02-28",
        placement: "Category Page",
        status: "Active",
        discount: "BOGO",
        image: null,
    },
    {
        id: "OFF-003",
        title: "New Year Special",
        description: "15% off on all products",
        validFrom: "2026-02-01",
        validTo: "2026-02-28",
        placement: "Homepage Banner",
        status: "Inactive",
        discount: "15%",
        image: null,
    },
];

const PLACEMENT_OPTIONS = ["All", "Homepage Banner", "Category Page", "Popup"];
const STATUS_OPTIONS = ["All", "Active", "Inactive"];

const statusStyle = (status) =>
    status === "Active"
        ? "bg-green-100 text-green-700"
        : "bg-gray-200 text-gray-500";

/* ── Banner Preview Card ─────────────────────────────────────────────────── */
function BannerCard({ offer }) {
    return (
        <div
            className="relative rounded-2xl overflow-hidden shadow-lg"
            style={{
                background:
                    "linear-gradient(135deg, #1a5276 0%, #1abc9c 60%, #2ecc71 100%)",
                minWidth: "240px",
                maxWidth: "300px",
                minHeight: "140px",
            }}
        >
            {/* Decorative pill shapes */}
            <div className="absolute -top-6 -left-6 w-28 h-28 rounded-full bg-white/10 blur-sm" />
            <div className="absolute -bottom-8 -right-8 w-36 h-36 rounded-full bg-white/10 blur-sm" />

            {/* Pill/capsule SVG decoration */}
            <svg
                className="absolute left-0 top-0 opacity-20"
                width="120"
                height="120"
                viewBox="0 0 120 120"
                fill="none"
            >
                <ellipse cx="30" cy="60" rx="28" ry="55" fill="white" />
                <ellipse cx="90" cy="60" rx="20" ry="40" fill="white" />
                <ellipse cx="60" cy="30" rx="15" ry="25" fill="white" />
            </svg>

            <div className="relative z-10 p-5 flex flex-col justify-between h-full min-h-[140px]">
                <div>
                    <p className="text-white/80 text-xs font-medium tracking-wider uppercase">
                        Medicines
                    </p>
                    <h3 className="text-white font-extrabold text-xl leading-tight mt-0.5">
                        Up To {offer.discount} OFF
                    </h3>
                    <p className="text-white/70 text-[11px] mt-1">{offer.description}</p>
                </div>
                <button className="mt-3 self-start bg-yellow-400 hover:bg-yellow-300 text-gray-900 font-bold text-xs px-4 py-1.5 rounded-full transition-colors shadow-md">
                    ORDER NOW
                </button>
            </div>
        </div>
    );
}

/* ── Modal ───────────────────────────────────────────────────────────────── */
function OfferModal({ offer, onClose, onSave }) {
    const [form, setForm] = useState(
        offer || {
            id: `OFF-00${Math.floor(Math.random() * 900) + 100}`,
            title: "",
            description: "",
            validFrom: "",
            validTo: "",
            placement: "Homepage Banner",
            status: "Active",
            discount: "",
        }
    );

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(form);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
                {/* Modal Header */}
                <div className="bg-gradient-to-r from-[#127690] to-[#1abc9c] px-6 py-4 flex items-center justify-between">
                    <h2 className="text-white font-semibold text-lg">
                        {offer ? "Edit Offer" : "Create New Offer"}
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-white/80 hover:text-white transition-colors"
                    >
                        <XCircle size={22} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs font-medium text-gray-500 mb-1 block">
                                Offer ID
                            </label>
                            <input
                                name="id"
                                value={form.id}
                                readOnly
                                className="w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-400"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-medium text-gray-500 mb-1 block">
                                Discount / Value
                            </label>
                            <input
                                name="discount"
                                value={form.discount}
                                onChange={handleChange}
                                placeholder="e.g. 70% or BOGO"
                                required
                                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="text-xs font-medium text-gray-500 mb-1 block">
                            Offer Title
                        </label>
                        <input
                            name="title"
                            value={form.title}
                            onChange={handleChange}
                            placeholder="e.g. Medicines Upto 70% off"
                            required
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                        />
                    </div>

                    <div>
                        <label className="text-xs font-medium text-gray-500 mb-1 block">
                            Description
                        </label>
                        <input
                            name="description"
                            value={form.description}
                            onChange={handleChange}
                            placeholder="Short offer description"
                            required
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs font-medium text-gray-500 mb-1 block">
                                Valid From
                            </label>
                            <input
                                type="date"
                                name="validFrom"
                                value={form.validFrom}
                                onChange={handleChange}
                                required
                                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-medium text-gray-500 mb-1 block">
                                Valid To
                            </label>
                            <input
                                type="date"
                                name="validTo"
                                value={form.validTo}
                                onChange={handleChange}
                                required
                                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="relative">
                            <label className="text-xs font-medium text-gray-500 mb-1 block">
                                Placement
                            </label>
                            <select
                                name="placement"
                                value={form.placement}
                                onChange={handleChange}
                                className="appearance-none w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400 cursor-pointer"
                            >
                                {PLACEMENT_OPTIONS.filter((p) => p !== "All").map((p) => (
                                    <option key={p} value={p}>
                                        {p}
                                    </option>
                                ))}
                            </select>
                            <ChevronDown
                                size={14}
                                className="absolute right-3 top-8 text-gray-400 pointer-events-none"
                            />
                        </div>
                        <div className="relative">
                            <label className="text-xs font-medium text-gray-500 mb-1 block">
                                Status
                            </label>
                            <select
                                name="status"
                                value={form.status}
                                onChange={handleChange}
                                className="appearance-none w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400 cursor-pointer"
                            >
                                <option value="Active">Active</option>
                                <option value="Inactive">Inactive</option>
                            </select>
                            <ChevronDown
                                size={14}
                                className="absolute right-3 top-8 text-gray-400 pointer-events-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-5 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-5 py-2 rounded-lg bg-[#127690] hover:bg-[#0f5f75] text-white text-sm font-semibold transition-colors shadow-sm"
                        >
                            {offer ? "Save Changes" : "Create Offer"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

/* ── Main Page ───────────────────────────────────────────────────────────── */
export default function OffersAndBanners() {
    const [offers, setOffers] = useState(initialOffers);
    const [search, setSearch] = useState("");
    const [placementFilter, setPlacementFilter] = useState("All");
    const [statusFilter, setStatusFilter] = useState("All");
    const [showModal, setShowModal] = useState(false);
    const [editingOffer, setEditingOffer] = useState(null);
    const [previewPlacement, setPreviewPlacement] = useState("Homepage Banner");

    const filteredOffers = useMemo(() => {
        return offers.filter((o) => {
            const q = search.toLowerCase();
            const matchSearch =
                o.title.toLowerCase().includes(q) ||
                o.id.toLowerCase().includes(q) ||
                o.description.toLowerCase().includes(q);
            const matchPlacement =
                placementFilter === "All" || o.placement === placementFilter;
            const matchStatus =
                statusFilter === "All" || o.status === statusFilter;
            return matchSearch && matchPlacement && matchStatus;
        });
    }, [offers, search, placementFilter, statusFilter]);

    const previewOffers = useMemo(
        () =>
            offers.filter(
                (o) => o.placement === previewPlacement && o.status === "Active"
            ),
        [offers, previewPlacement]
    );

    const handleSave = (form) => {
        if (editingOffer) {
            setOffers((prev) => prev.map((o) => (o.id === form.id ? form : o)));
        } else {
            setOffers((prev) => [...prev, form]);
        }
        setShowModal(false);
        setEditingOffer(null);
    };

    const handleDelete = (id) => {
        setOffers((prev) => prev.filter((o) => o.id !== id));
    };

    const handleToggleStatus = (id) => {
        setOffers((prev) =>
            prev.map((o) =>
                o.id === id
                    ? { ...o, status: o.status === "Active" ? "Inactive" : "Active" }
                    : o
            )
        );
    };

    const handleEdit = (offer) => {
        setEditingOffer(offer);
        setShowModal(true);
    };

    const activeCount = offers.filter((o) => o.status === "Active").length;
    const inactiveCount = offers.filter((o) => o.status === "Inactive").length;

    return (
        <div className="ml-5 mt-5 border-l-2 border-gray-100">
            {/* ── Header ── */}
            <div className="mb-3 flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
                        Offers &amp; Banners Management
                    </h1>
                    <p className="text-sm text-gray-500">
                        Monitor and manage pharmacy operations in real time.
                    </p>
                </div>

                <div className="flex items-center gap-3 flex-wrap">
                    {/* Search */}
                    <div className="flex items-center bg-white border border-[#E5E7EB] rounded-xl px-3 py-1.5 shadow-sm focus-within:shadow-lg transition-all">
                        <Search size={16} className="text-[#9EA2A7] shrink-0" />
                        <input
                            type="text"
                            placeholder="Search offers..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="ml-2 w-48 bg-transparent outline-none text-sm text-[#505050] placeholder:text-[#9EA2A7]"
                        />
                    </div>

                    {/* Placement Filter */}
                    <div className="relative">
                        <select
                            value={placementFilter}
                            onChange={(e) => setPlacementFilter(e.target.value)}
                            className="appearance-none bg-white border border-[#E5E7EB] rounded-xl px-4 py-2 pr-8 text-sm text-[#505050] font-medium focus:outline-none focus:ring-2 focus:ring-teal-400 cursor-pointer"
                        >
                            {PLACEMENT_OPTIONS.map((p) => (
                                <option key={p} value={p}>
                                    {p === "All" ? "All Placements" : p}
                                </option>
                            ))}
                        </select>
                        <ChevronDown
                            size={14}
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                        />
                    </div>

                    {/* Status Filter */}
                    <div className="relative">
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="appearance-none bg-white border border-[#E5E7EB] rounded-xl px-4 py-2 pr-8 text-sm text-[#505050] font-medium focus:outline-none focus:ring-2 focus:ring-teal-400 cursor-pointer"
                        >
                            {STATUS_OPTIONS.map((s) => (
                                <option key={s} value={s}>
                                    {s === "All" ? "All Status" : s}
                                </option>
                            ))}
                        </select>
                        <ChevronDown
                            size={14}
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                        />
                    </div>

                    {/* Create Button */}
                    <button
                        onClick={() => {
                            setEditingOffer(null);
                            setShowModal(true);
                        }}
                        className="flex items-center gap-2 bg-[#127690] hover:bg-[#0f5f75] text-white text-sm font-semibold px-5 py-2 rounded-xl shadow-sm transition-colors"
                    >
                        <Plus size={16} />
                        Create New Offer
                    </button>
                </div>
            </div>

            {/* ── Summary Cards ── */}
            <div className="flex flex-col md:flex-row gap-4 lg:gap-6 mb-4">
                <SummaryCard
                    title="Total Offers"
                    value={offers.length}
                    icon={<Tag size={20} />}
                    bgClass="bg-[#d8e9ff]"
                    textClass="text-[#1D4ED8]"
                    iconClass="text-blue-600"
                    blobColor1="bg-[#83ACE5]"
                    blobColor2="bg-[#1447EA]"
                />
                <SummaryCard
                    title="Active Offers"
                    value={activeCount}
                    icon={<CheckCircle size={20} />}
                    bgClass="bg-[#e9fedf]"
                    textClass="text-[#207238]"
                    iconClass=""
                    blobColor1="bg-[#A3FF63]"
                    blobColor2="bg-[#33CB6C]"
                />
                <SummaryCard
                    title="Inactive Offers"
                    value={inactiveCount}
                    icon={<XCircle size={20} />}
                    bgClass="bg-[#f2ecbb]"
                    textClass="text-[#846018]"
                    iconClass=""
                    blobColor1="bg-[#D08700]"
                    blobColor2="bg-[#733E0A]"
                />
            </div>

            {/* ── Table ── */}
            <div className="bg-white rounded-2xl shadow-sm overflow-hidden mb-6">
                <div className="overflow-x-auto overflow-y-auto max-h-[400px]">
                    <table className="min-w-[900px] w-full text-left">
                        <thead className="bg-[#DCE4EA] text-gray-600 text-xs uppercase tracking-wide sticky top-0 z-10">
                            <tr>
                                <th className="px-6 py-4">Offer ID</th>
                                <th className="px-6">Title</th>
                                <th className="px-6">Description</th>
                                <th className="px-6">Valid Period</th>
                                <th className="px-6">Placement</th>
                                <th className="px-6">Status</th>
                                <th className="px-6">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm text-gray-700">
                            {filteredOffers.length === 0 ? (
                                <tr>
                                    <td
                                        colSpan={7}
                                        className="px-6 py-10 text-center text-gray-400"
                                    >
                                        No offers found.
                                    </td>
                                </tr>
                            ) : (
                                filteredOffers.map((offer, index) => (
                                    <tr
                                        key={offer.id}
                                        className={`${index % 2 === 0 ? "bg-white" : "bg-[#F4F6F8]"
                                            } hover:bg-[#EEF2F6] transition`}
                                    >
                                        <td className="px-6 py-4 font-semibold text-[#127690]">
                                            {offer.id}
                                        </td>
                                        <td className="px-6 font-medium">{offer.title}</td>
                                        <td className="px-6 text-gray-500">{offer.description}</td>
                                        <td className="px-6">
                                            <span className="text-xs text-gray-500 block">
                                                {offer.validFrom}
                                            </span>
                                            <span className="text-xs text-gray-400">
                                                to {offer.validTo}
                                            </span>
                                        </td>
                                        <td className="px-6">
                                            <span className="bg-blue-50 text-blue-600 text-xs font-medium px-2 py-0.5 rounded-full">
                                                {offer.placement}
                                            </span>
                                        </td>
                                        <td className="px-6">
                                            <span
                                                className={`px-3 py-1 rounded-full text-xs font-semibold ${statusStyle(
                                                    offer.status
                                                )}`}
                                            >
                                                {offer.status}
                                            </span>
                                        </td>
                                        <td className="px-6">
                                            <div className="flex items-center gap-3">
                                                <button
                                                    onClick={() => handleEdit(offer)}
                                                    className="text-[#127690] hover:text-[#0f5f75] transition-colors"
                                                    title="Edit"
                                                >
                                                    <Pencil size={16} />
                                                </button>
                                                <button
                                                    onClick={() => handleToggleStatus(offer.id)}
                                                    className={`transition-colors ${offer.status === "Active"
                                                            ? "text-yellow-500 hover:text-yellow-700"
                                                            : "text-green-500 hover:text-green-700"
                                                        }`}
                                                    title={
                                                        offer.status === "Active"
                                                            ? "Deactivate"
                                                            : "Activate"
                                                    }
                                                >
                                                    <Ban size={16} />
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(offer.id)}
                                                    className="text-red-400 hover:text-red-600 transition-colors"
                                                    title="Delete"
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* ── Banner Preview Section ── */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <LayoutTemplate size={18} className="text-[#127690]" />
                        <h2 className="text-base font-semibold text-[#505050]">
                            Preview –{" "}
                            <span className="text-[#127690]">{previewPlacement}</span>
                        </h2>
                    </div>

                    {/* Placement switcher for preview */}
                    <div className="flex items-center gap-2">
                        {PLACEMENT_OPTIONS.filter((p) => p !== "All").map((p) => (
                            <button
                                key={p}
                                onClick={() => setPreviewPlacement(p)}
                                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors border ${previewPlacement === p
                                        ? "bg-[#127690] text-white border-[#127690]"
                                        : "bg-white text-gray-500 border-gray-200 hover:bg-gray-50"
                                    }`}
                            >
                                {p}
                            </button>
                        ))}
                    </div>
                </div>

                {previewOffers.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 text-gray-400 gap-2">
                        <LayoutTemplate size={36} className="opacity-30" />
                        <p className="text-sm">
                            No active offers for{" "}
                            <span className="font-medium">{previewPlacement}</span>.
                        </p>
                    </div>
                ) : (
                    <div className="flex flex-wrap gap-5">
                        {previewOffers.map((offer) => (
                            <BannerCard key={offer.id} offer={offer} />
                        ))}
                    </div>
                )}

                <p className="text-xs text-gray-400 mt-4">
                    This is how the banner will appear on the retailer mobile app homepage.
                </p>
            </div>

            {/* ── Modal ── */}
            {showModal && (
                <OfferModal
                    offer={editingOffer}
                    onClose={() => {
                        setShowModal(false);
                        setEditingOffer(null);
                    }}
                    onSave={handleSave}
                />
            )}
        </div>
    );
}
