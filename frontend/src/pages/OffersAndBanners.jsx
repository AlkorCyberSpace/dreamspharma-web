import React, { useState, useMemo, useEffect } from "react";
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
import { addOfferAPI, getOffersAPI, getCategoriesAPI, getProductsAPI, updateOfferAPI, deleteOfferAPI, getOfferDetailAPI } from "../services/allAPI";
import { serverUrl, mediaUrl } from "../services/serverUrl";


const initialOffers = [];

const PLACEMENT_OPTIONS = ["All", "Homepage Banner", "Category Page"];
const STATUS_OPTIONS = ["All", "Active", "Inactive"];

const PLACEMENT_MAP = {
    "homepage": "Homepage Banner",
    "category": "Category Page",
};

const PLACEMENT_REVERSE_MAP = {
    "Homepage Banner": "homepage",
    "Category Page": "category",
};

const statusStyle = (status) =>
    status === "Active"
        ? "bg-green-100 text-green-700"
        : "bg-gray-200 text-gray-500";

/* ── Banner Preview Card ─────────────────────────────────────────────────── */
function BannerCard({ offer }) {
    const hasImage = !!offer.banner_image;

    return (
        <div
            className="relative rounded-2xl overflow-hidden shadow-lg"
            style={{
                background: hasImage
                    ? "#f3f4f6" // Light gray background if image exists
                    : "linear-gradient(135deg, #1a5276 0%, #1abc9c 60%, #2ecc71 100%)",
                minWidth: "240px",
                maxWidth: "300px",
                minHeight: "140px",
            }}
        >
            {/* Show image properly if it exists */}
            {hasImage ? (
                <>
                    <img
                        src={offer.banner_image.startsWith('http') ? offer.banner_image : `${mediaUrl}${offer.banner_image}`}
                        alt={offer.title}
                        className="absolute inset-0 w-full h-full object-cover z-0"
                    />
                    {/* Subtle overlay for text readability */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent z-10" />
                </>
            ) : (
                <>
                    {/* Decorative design shown in "second picture" */}
                    <div className="absolute -top-6 -left-6 w-28 h-28 rounded-full bg-white/10 blur-sm" />
                    <div className="absolute -bottom-8 -right-8 w-36 h-36 rounded-full bg-white/10 blur-sm" />
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
                </>
            )}

            <div className="relative z-20 p-5 flex flex-col justify-between h-full min-h-[140px]">
                <div>
                    <p className="text-white/80 text-[10px] font-bold tracking-widest uppercase">
                        Medicines
                    </p>
                    <h3 className="text-white font-extrabold text-xl leading-tight mt-0.5 drop-shadow-sm">
                        Up To {parseFloat(offer.discount_percentage || 0).toFixed(2)}% OFF
                    </h3>
                    <p className="text-white/70 text-[11px] mt-1 line-clamp-2 leading-tight">
                        {offer.description || ""}
                    </p>
                </div>

                <button className="mt-3 self-start bg-yellow-400 hover:bg-yellow-300 text-gray-900 font-bold text-[10px] px-4 py-1.5 rounded-full transition-all shadow-md active:scale-95">
                    ORDER NOW
                </button>
            </div>
        </div>
    );
}

/* ── Modal ──*/
function OfferModal({ offer, onClose, onSave }) {
    const [form, setForm] = useState(() => {
        if (offer) {
            // Transform products array from objects to IDs for selection
            // Handle both product_id (from offer detail) and c_item_code (from product list)
            const selectedProductIds = Array.isArray(offer.products)
                ? offer.products.map(p => {
                    // Normalize to always use item code/product_id
                    if (typeof p === 'string' || typeof p === 'number') {
                        return String(p);
                    }
                    const id = String(p.product_id || p.c_item_code || p.item_code || '');
                    console.log('Extracted product ID:', id, 'from object:', p);
                    return id;
                })
                : [];
            
            console.log('Selected product IDs from offer:', selectedProductIds);

            return {
                ...offer,
                placement: offer.placement || "homepage",
                category: offer.category || "",
                discount_percentage: offer.discount_percentage || 0,
                products: selectedProductIds
            };
        }

        return {
            offer_id: `OFF-00${Math.floor(Math.random() * 900) + 100}`,
            title: "",
            description: "",
            valid_from: "",
            valid_to: "",
            placement: "homepage",
            status: true,
            discount_percentage: 0,
            category: "",
            products: [],
            banner_image: null
        };
    });

    const [categories, setCategories] = useState([]);
    const [productsList, setProductsList] = useState([]);

    useEffect(() => {
        const fetchMetadata = async () => {
            try {
                const [catRes, prodRes] = await Promise.all([getCategoriesAPI(), getProductsAPI()]);
                const categoriesData = catRes.data?.data || catRes.data?.results || catRes.data || [];
                setCategories(Array.isArray(categoriesData) ? categoriesData : []);

                const productsData = prodRes.data?.data || prodRes.data?.results || prodRes.data || [];
                setProductsList(Array.isArray(productsData) ? productsData : []);
            } catch (error) {
                console.error("Error fetching metadata:", error);
            }
        };
        fetchMetadata();
    }, []);

    const handleChange = (e) => {
        const { name, value, type, checked, files } = e.target;
        if (type === "checkbox") {
            setForm((prev) => ({ ...prev, [name]: checked }));
        } else if (type === "file") {
            setForm((prev) => ({ ...prev, [name]: files[0] }));
        } else {
            setForm((prev) => ({ ...prev, [name]: value ?? "" }));
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(form);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <div className="bg-white rounded-3xl shadow-2xl w-full max-w-4xl flex flex-col max-h-[95vh] overflow-hidden">
                {/* Modal Header */}
                <div className="bg-gradient-to-r from-[#127690] to-[#1abc9c] px-8 py-2 flex items-center justify-between shrink-0">
                    <div>
                        <h2 className="text-white font-bold text-xl">
                            {offer ? "Edit Offer" : "Create New Offer"}
                        </h2>
                        <p className="text-white/70 text-xs mt-0.5 font-medium tracking-wide">
                            {offer ? "Update existing campaign details" : "Launch a new marketing campaign"}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-full transition-all active:scale-95"
                    >
                        <XCircle size={24} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-6">
                        {/* Left Column */}
                        <div className="space-y-3">
                            <div>
                                <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                    Offer ID
                                </label>
                                <input
                                    name="offer_id"
                                    value={form.offer_id}
                                    onChange={handleChange}
                                    placeholder="e.g. FESTIVE2026"
                                    required
                                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all font-medium"
                                />
                            </div>

                            <div>
                                <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                    Offer Title
                                </label>
                                <input
                                    name="title"
                                    value={form.title}
                                    onChange={handleChange}
                                    placeholder="e.g. Medicines Upto 70% off"
                                    required
                                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all font-medium"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                        Valid From
                                    </label>
                                    <input
                                        type="date"
                                        name="valid_from"
                                        value={form.valid_from}
                                        onChange={handleChange}
                                        required
                                        className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                        Valid To
                                    </label>
                                    <input
                                        type="date"
                                        name="valid_to"
                                        value={form.valid_to}
                                        onChange={handleChange}
                                        required
                                        className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                    Banner Image (Optional)
                                </label>
                                <div className="mt-1 flex flex-col gap-3">
                                    {(form.banner_image || offer?.banner_image) && (
                                        <div className="relative w-full h-32 rounded-2xl bg-gray-50 border border-dashed border-gray-300 overflow-hidden group">
                                            <img
                                                src={
                                                    form.banner_image instanceof File
                                                        ? URL.createObjectURL(form.banner_image)
                                                        : form.banner_image?.startsWith('http')
                                                            ? form.banner_image
                                                            : `${mediaUrl}${form.banner_image || offer?.banner_image}`
                                                }
                                                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                                                alt="Banner Preview"
                                            />
                                            <div className="absolute top-2 right-2 bg-black/60 text-white text-[9px] px-2 py-1 rounded-full backdrop-blur-sm">
                                                {form.banner_image instanceof File ? 'New Selection' : 'Current Banner'}
                                            </div>
                                        </div>
                                    )}

                                    <div className="flex items-center gap-3">
                                        <div className="relative overflow-hidden flex-1">
                                            <input
                                                type="file"
                                                name="banner_image"
                                                onChange={handleChange}
                                                accept="image/*"
                                                className="absolute inset-0 opacity-0 px-4 py-2 cursor-pointer z-10"
                                            />
                                            <div className="flex items-center gap-2 px-4 py-2 bg-teal-50 border border-teal-100 rounded-xl text-teal-700 text-xs font-bold hover:bg-teal-100 transition-all text-center justify-center">
                                                <Plus size={14} />
                                                {form.banner_image ? 'Change Image' : 'Select Banner Image'}
                                            </div>
                                        </div>
                                        {form.banner_image && (
                                            <button
                                                type="button"
                                                onClick={() => setForm(f => ({ ...f, banner_image: offer?.banner_image || null }))}
                                                className="p-2 text-red-500 hover:bg-red-50 rounded-xl transition-all"
                                                title="Reset Image"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right Column */}
                        <div className="space-y-2">
                            <div>
                                <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                    Description
                                </label>
                                <textarea
                                    name="description"
                                    value={form.description}
                                    onChange={handleChange}
                                    placeholder="Enter short offer description..."
                                    required
                                    rows={1}
                                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all min-h-[45px] resize-none"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                        Placement
                                    </label>
                                    <select
                                        name="placement"
                                        value={form.placement || "homepage"}
                                        onChange={handleChange}
                                        className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all bg-white cursor-pointer font-medium"
                                    >
                                        <option value="homepage">Homepage Banner</option>
                                        <option value="category">Category Page</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                        Discount (%)
                                    </label>
                                    <input
                                        type="number"
                                        name="discount_percentage"
                                        value={form.discount_percentage || 0}
                                        onChange={handleChange}
                                        placeholder="0.00"
                                        required
                                        className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all font-semibold"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2 block">
                                        Category
                                    </label>
                                    <select
                                        name="category"
                                        value={form.category || ""}
                                        onChange={handleChange}
                                        className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all bg-white cursor-pointer"
                                    >
                                        <option value="">No Filter</option>
                                        {categories.map((cat) => (
                                            <option key={cat.id} value={cat.id}>
                                                {cat.category_name || cat.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="flex items-center pt-6">
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            name="status"
                                            checked={form.status}
                                            onChange={handleChange}
                                            className="sr-only peer"
                                        />
                                        <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-teal-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal-600"></div>
                                        <span className="ml-3 text-xs font-bold text-gray-500 uppercase tracking-widest">Active</span>
                                    </label>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <label className="text-[11px] font-bold text-gray-400 uppercase tracking-widest block">
                                        Apply to Products
                                    </label>
                                    <span className="text-[10px] font-medium text-teal-600 bg-teal-50 px-2 py-0.5 rounded-full uppercase tracking-tighter">
                                        {form.products?.length || 0} selected
                                    </span>
                                </div>

                                <div className="border border-gray-100 rounded-xl overflow-hidden bg-white shadow-inner">
                                    <div className="max-h-[168px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-200">
                                        {productsList.length === 0 ? (
                                            <div className="py-8 text-center text-gray-400 text-xs">
                                                No products available
                                            </div>
                                        ) : (
                                            <div className="grid grid-cols-1 gap-px bg-gray-50">
                                                {productsList.map((prod) => {
                                                    // Normalize product ID - handle both c_item_code and product_id
                                                    const prodId = String(prod.c_item_code || prod.product_id || prod.item_code || '');
                                                    const prodName = String(prod.itemName || prod.product_name || prod.name || '').toLowerCase();
                                                    
                                                    // Check if selected by ID
                                                    let isSelected = form.products?.includes(prodId);
                                                    
                                                    // Fallback: check if any selected product matches by name
                                                    if (!isSelected && form.products && form.products.length > 0 && prodName) {
                                                        isSelected = form.products.some(selectedId => {
                                                            const selectedProd = productsList.find(p => 
                                                                String(p.c_item_code || p.product_id || p.item_code || '') === selectedId
                                                            );
                                                            return selectedProd && 
                                                                String(selectedProd.itemName || selectedProd.product_name || selectedProd.name || '').toLowerCase() === prodName;
                                                        });
                                                    }
                                                    
                                                    return (
                                                        <div
                                                            key={prodId}
                                                            onClick={() => {
                                                                const current = form.products || [];
                                                                const updated = isSelected
                                                                    ? current.filter(id => id !== prodId)
                                                                    : [...current, prodId];
                                                                setForm(prev => ({ ...prev, products: updated }));
                                                            }}
                                                            className={`
                                                                flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-all border-l-4
                                                                ${isSelected
                                                                    ? "bg-[#1abc9c] border-[#a5e0d5] text-white"
                                                                    : "bg-white border-transparent hover:bg-gray-50 text-gray-800"
                                                                }
                                                            `}
                                                        >
                                                            <div className={`
                                                                w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors
                                                                ${isSelected ? "bg-white border-white" : "border-gray-300 bg-white"}
                                                            `}>
                                                                {isSelected && <CheckCircle size={12} className="text-[#09705b]" fill="currentColor" />}
                                                            </div>
                                                            <div className="flex flex-col flex-1">
                                                                <span className="text-xs font-bold leading-tight uppercase tracking-tight">
                                                                    {prod.itemName}
                                                                </span>
                                                                <span className={`text-[9px] font-medium mt-0.5 ${isSelected ? "text-blue-100" : "text-gray-400"}`}>
                                                                    PID: {prodId}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-end gap-4 pt-3 border-t border-gray-100 mt-6">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-8 py-2.5 rounded-xl border border-gray-200 text-sm font-bold text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-all active:scale-95"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-10 py-2.5 rounded-xl bg-gradient-to-r from-[#127690] to-[#1abc9c] text-white text-sm font-bold hover:shadow-lg hover:shadow-teal-500/20 transition-all active:scale-95"
                        >
                            {offer ? "Update Campaign" : "Launch Offer"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

/* ── Main Page ── */
export default function OffersAndBanners() {
    const [offers, setOffers] = useState(initialOffers);
    const [search, setSearch] = useState("");
    const [placementFilter, setPlacementFilter] = useState("All");
    const [statusFilter, setStatusFilter] = useState("All");
    const [showModal, setShowModal] = useState(false);
    const [editingOffer, setEditingOffer] = useState(null);
    const [previewPlacement, setPreviewPlacement] = useState("Homepage Banner");
    const [deleteConfirmId, setDeleteConfirmId] = useState(null);

    useEffect(() => {
        const fetchOffers = async () => {
            try {
                const response = await getOffersAPI();

                const offersData =
                    response.data?.results ||
                    response.data?.data ||
                    response.data ||
                    [];

                setOffers(Array.isArray(offersData) ? offersData : []);
                console.log(offersData);


            } catch (error) {
                console.error("Error fetching offers:", error);
                setOffers([]);
            }
        };

        fetchOffers();
    }, []);

    const filteredOffers = useMemo(() => {
        return offers.filter((o) => {
            const q = search.toLowerCase();
            const matchSearch =
                o.title.toLowerCase().includes(q) ||
                (o.offer_id && o.offer_id.toLowerCase().includes(q)) ||
                o.description.toLowerCase().includes(q);
            const matchPlacement =
                placementFilter === "All" || PLACEMENT_MAP[o.placement] === placementFilter;
            const matchStatus =
                statusFilter === "All" ||
                (o.status ? "Active" : "Inactive") === statusFilter;
            return matchSearch && matchPlacement && matchStatus;
        });
    }, [offers, search, placementFilter, statusFilter]);

    const previewOffers = useMemo(
        () =>
            offers.filter(
                (o) => (PLACEMENT_MAP[o.placement] === previewPlacement || o.placement === previewPlacement) && o.status
            ),
        [offers, previewPlacement]
    );

    const handleSave = async (form) => {
        try {
            const formData = new FormData();
            formData.append("offer_id", form.offer_id);
            formData.append("title", form.title);
            formData.append("description", form.description);
            formData.append("valid_from", form.valid_from);
            formData.append("valid_to", form.valid_to);
            formData.append("placement", form.placement);
            formData.append("status", form.status);
            formData.append("discount_percentage", parseFloat(form.discount_percentage) || 0);
            if (form.category) formData.append("category", form.category);
            if (form.banner_image && typeof form.banner_image !== 'string') {
                formData.append("banner_image", form.banner_image);
            }
            if (form.products && form.products.length > 0) {
                formData.append("products", JSON.stringify(form.products));
            }

            if (editingOffer) {
                await updateOfferAPI(editingOffer.offer_id, formData);
                console.log("Offer updated successfully");
            } else {
                await addOfferAPI(formData);
                console.log("Offer created successfully");
            }

            // Refresh data
            const response = await getOffersAPI();
            const offersData = response.data?.results || response.data?.data || response.data || [];
            setOffers(Array.isArray(offersData) ? offersData : []);

            setShowModal(false);
            setEditingOffer(null);
        } catch (error) {
            console.error("Failed to save offer:", error.response?.data || error);
            const errorMsg = error.response?.data
                ? JSON.stringify(error.response.data)
                : "Failed to save the offer. Please try again.";
            alert(`Error: ${errorMsg}`);
        }
    };

    const handleDelete = (id) => {
        setDeleteConfirmId(id);
    };

    const confirmDelete = async () => {
        if (!deleteConfirmId) return;
        try {
            await deleteOfferAPI(deleteConfirmId);
            setOffers((prev) => prev.filter((o) => o.offer_id !== deleteConfirmId));
        } catch (error) {
            console.error("Failed to delete offer:", error);
        } finally {
            setDeleteConfirmId(null);
        }
    };

    const handleToggleStatus = async (offer) => {
        try {
            const formData = new FormData();
            formData.append("status", !offer.status);
            await updateOfferAPI(offer.offer_id, formData);
            setOffers((prev) =>
                prev.map((o) =>
                    o.offer_id === offer.offer_id
                        ? { ...o, status: !o.status }
                        : o
                )
            );
        } catch (error) {
            console.error("Failed to toggle status:", error);
        }
    };

    const handleEdit = async (offer) => {
        // Use the offer data from the list (which includes products)
        // Don't refetch detail as it doesn't include product data
        setEditingOffer(offer);
        setShowModal(true);
    };

    const activeCount = offers.filter((o) => o.status === true || o.status === "Active").length;
    const inactiveCount = offers.filter((o) => o.status === false || o.status === "Inactive").length;

    return (
        <div className="ml-2 mt-3 min-h-screen">
            {/* ── Header ── */}
            <div className="mb-5 flex flex-col xl:flex-row xl:items-center justify-between gap-6">
                <div>
                    <h1 className="text-xl font-semibold text-[#505050] tracking-tight">
                        Offers &amp; Banners Management
                    </h1>
                    <p className="text-xs text-gray-500 ">
                        Monitor and manage pharmacy marketing campaigns and seasonal offers.
                    </p>
                </div>

                <div className="flex flex-col lg:flex-row items-center gap-4 w-full xl:w-auto">
                    <div className="flex items-center bg-white border border-[#E5E7EB] rounded-2xl p-1 shadow-sm focus-within:ring-2 focus-within:ring-teal-500/20 focus-within:border-teal-500 transition-all w-full lg:w-auto overflow-hidden">
                        <div className="flex items-center px-4 py-1.5 min-w-[100px] md:min-w-[220px]">
                            <Search size={18} className="text-[#9EA2A7] shrink-0" />
                            <input
                                type="text"
                                placeholder="Search campaigns..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="ml-3 w-full bg-transparent outline-none text-sm text-[#4B5563] placeholder:text-[#9EA2A7]"
                            />
                        </div>

                        <div className="h-6 w-[1px] bg-gray-200 mx-1 hidden sm:block" />

                        <div className="relative shrink-0 hidden sm:block">
                            <select
                                value={placementFilter}
                                onChange={(e) => setPlacementFilter(e.target.value)}
                                className="appearance-none bg-transparent hover:bg-gray-50 rounded-xl px-5 py-2.5 pr-10 text-[10px] font-bold text-gray-400 uppercase tracking-widest cursor-pointer transition-colors"
                            >
                                {PLACEMENT_OPTIONS.map((p) => (
                                    <option key={p} value={p}>
                                        {p === "All" ? "Placements" : p}
                                    </option>
                                ))}
                            </select>
                            <ChevronDown
                                size={12}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                            />
                        </div>

                        <div className="h-6 w-[1px] bg-gray-200 mx-1 hidden sm:block" />

                        <div className="relative shrink-0 pr-2">
                            <select
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                                className="appearance-none bg-transparent hover:bg-gray-50 rounded-xl px-5 py-2.5 pr-10 text-[10px] font-bold text-gray-400 uppercase tracking-widest cursor-pointer transition-colors"
                            >
                                {STATUS_OPTIONS.map((s) => (
                                    <option key={s} value={s}>
                                        {s === "All" ? "Status" : s}
                                    </option>
                                ))}
                            </select>
                            <ChevronDown
                                size={12}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
                            />
                        </div>
                         <button
                    onClick={() => {
                        setEditingOffer(null);
                        setShowModal(true);
                    }}
                    className="flex items-center justify-center gap-1 bg-[#127690] hover:bg-[#0f5f75] text-white text-sm font-bold px-2 py-2 rounded-xl shadow-md shadow-teal-900/10 transition-all active:scale-95 shrink-0"
                >
                    <Plus size={17} />
                    <span></span>
                </button>
                    </div>
                </div>
            </div>

            {/* ── Summary Cards ── */}
            {/* <div className="flex flex-col md:flex-row gap-4 lg:gap-6 mb-4">
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
            </div> */}

            {/* ── Table Header ── */}
            {/* <div className="flex items-center justify-between mb-4 mt-4">
                <button
                    onClick={() => {
                        setEditingOffer(null);
                        setShowModal(true);
                    }}
                    className="flex items-center justify-center gap-2 bg-[#127690] hover:bg-[#0f5f75] text-white text-sm font-bold px-6 py-2.5 rounded-2xl shadow-md shadow-teal-900/10 transition-all active:scale-95 shrink-0"
                >
                    <Plus size={18} />
                    <span>Create Offer</span>
                </button>
            </div> */}

            {/* ── Table ── */}
            <div className="bg-white rounded-xl shadow-sm overflow-hidden mb-6">
                <div className="overflow-x-auto overflow-y-auto max-h-[400px]">
                    <table className="min-w-[900px] w-full text-left">
                        <thead className="bg-[#DCE4EA] text-gray-600 text-xs uppercase tracking-wide sticky top-0 z-10">
                            <tr>
                                <th className="px-6 py-4text-center">SI NO</th>
                                <th className="px-6 py-4">Offer ID</th>
                                <th className="px-6">Title</th>
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
                                        colSpan={8}
                                        className="px-6 py-10 text-center text-gray-400"
                                    >
                                        No offers found.
                                    </td>
                                </tr>
                            ) : (
                                filteredOffers.map((offer, index) => (
                                    <tr
                                        key={offer.offer_id}
                                        className={`${index % 2 === 0 ? "bg-white" : "bg-[#F4F6F8]"} hover:bg-[#EEF2F6] transition`}
                                    >
                                        <td className="px-6 py-2 font-bold text-[#127690] text-center">
                                            {index + 1}
                                        </td>

                                        <td className="px-6 py-2 font-semibold text-[#127690]">
                                            {offer.offer_id}
                                        </td>

                                        <td className="px-6 font-medium">{offer.title}</td>
                                        <td className="px-6">
                                            <span className="text-xs text-gray-500 block">
                                                {offer.valid_from}
                                            </span>
                                            <span className="text-xs text-gray-400">
                                                to {offer.valid_to}
                                            </span>
                                        </td>

                                        <td className="px-6">
                                            <span className="bg-blue-50 text-blue-600 text-xs font-medium px-2 py-0.5 rounded-full">
                                                {PLACEMENT_MAP[offer.placement] || offer.placement}
                                            </span>
                                        </td>

                                        <td className="px-6">
                                            <span
                                                className={`px-3 py-1 rounded-full text-xs font-semibold ${offer.status ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-500"
                                                    }`}
                                            >
                                                {offer.status ? "Active" : "Inactive"}
                                            </span>
                                        </td>

                                        <td className="px-6">
                                            <div className="flex items-center gap-3">
                                                <button onClick={() => handleEdit(offer)} title="Edit">
                                                    <Pencil size={16} className="text-blue-500" />
                                                </button>

                                                <button onClick={() => handleToggleStatus(offer)} title="Toggle Status">
                                                    <Ban size={16} className={offer.status ? "text-orange-500" : "text-gray-400"} />
                                                </button>

                                                <button onClick={() => handleDelete(offer.offer_id)} title="Delete">
                                                    <Trash2 size={16} className="text-red-500" />
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
            <div className="bg-white rounded-2xl shadow-sm p-3">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <LayoutTemplate size={18} className="text-[#127690]" />
                        <h2 className="text-xs sm:text-xs font-semibold text-[#505050]">
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
                            <BannerCard key={offer.offer_id} offer={offer} />
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

            {/* ── Delete Confirmation Modal ── */}
            {deleteConfirmId && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center p-2 bg-gray-900/40 backdrop-blur-sm transition-opacity duration-300">
                    <div className="bg-white rounded-[1rem] shadow-2xl w-full max-w-sm overflow-hidden transform transition-all scale-100 flex flex-col p-4 items-center text-center">
                        <div className="w-10 h-10 bg-red-50 rounded-full flex items-center justify-center mb-2">
                            <Trash2 size={20} className="text-red-500" />
                        </div>
                        <h3 className="text-xl font-semibold text-gray-900">Delete Offer?</h3>
                        <p className="text-sm text-gray-500 mb-1 px-2 leading-relaxed">
                            Are you sure you want to delete offer <span className="font-semibold text-gray-700">{deleteConfirmId}</span>? This action cannot be undone.
                        </p>
                        <div className="flex w-full gap-3">
                            <button
                                onClick={() => setDeleteConfirmId(null)}
                                className="flex-1 px-3 py-2 rounded-2xl border border-gray-200 text-sm font-bold text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-all active:scale-95"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={confirmDelete}
                                className="flex-1 px-3 py-2 rounded-2xl bg-gradient-to-r from-red-500 to-red-600 text-white text-sm font-bold hover:shadow-lg hover:shadow-red-500/30 transition-all active:scale-95"
                            >
                                Yes, Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
