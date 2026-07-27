import React, { useState, useEffect } from 'react';
import { Plus, Search, MapPin, Phone, Mail, User, Shield, Activity, MoreVertical, X, LayoutGrid, List, Building2, Database, Globe, Eye, Settings, Edit, Trash2, ChevronDown } from 'lucide-react';
import { getWarehousesAPI, addWarehouseAPI, updateWarehouseAPI, deleteWarehouseAPI } from '../services/allAPI';

const Warehouse = () => {
    const [warehouses, setWarehouses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState('all');
    const [viewMode, setViewMode] = useState('list');
    const [showAddModal, setShowAddModal] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [editId, setEditId] = useState(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(null); // stores ID of warehouse to delete
    const [showViewModal, setShowViewModal] = useState(false);
    const [selectedWarehouse, setSelectedWarehouse] = useState(null);

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage] = useState(10); // Adjusted for grid visibility

    // Form state
    const [formData, setFormData] = useState({
        name: "", address: "", city: "", state: "", pincode: "",
        latitude: "", longitude: "", c2_code: "", store_id: "",
        prod_code: "02", security_key: "", phone: "", email: "",
        manager_name: "", manager_phone: "", is_primary: false, is_active: true
    });

    const fetchWarehouses = async () => {
        setLoading(true);
        try {
            const res = await getWarehousesAPI();
            console.log("Warehouses: ", res.data);

            if (res.status >= 200 && res.status < 300) {
                setWarehouses(res.data);
            }
        } catch (err) {
            console.error("Error fetching warehouses:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchWarehouses();
    }, []);

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    // Auto-fetch location based on pincode
    useEffect(() => {
        const fetchLocation = async () => {
            const pincode = formData.pincode;
            if (pincode && pincode.length === 6 && /^\d+$/.test(pincode)) {
                try {
                    // Using Nominatim (OpenStreetMap) for free geocoding
                    const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&postalcode=${pincode}&country=India&addressdetails=1`);
                    const data = await response.json();

                    if (data && data.length > 0) {
                        const location = data[0];
                        const address = location.address;

                        setFormData(prev => ({
                            ...prev,
                            latitude: location.lat,
                            longitude: location.lon,
                            // Only update city/state if they are currently empty to avoid overwriting user intent
                            city: prev.city || address.city || address.town || address.village || address.state_district || "",
                            state: prev.state || address.state || ""
                        }));
                    }
                } catch (error) {
                    console.error("Error fetching location data:", error);
                }
            }
        };

        const timeoutId = setTimeout(fetchLocation, 500); // Debounce to avoid excessive API calls
        return () => clearTimeout(timeoutId);
    }, [formData.pincode]);

    const handleView = (warehouse) => {
        setSelectedWarehouse(warehouse);
        setShowViewModal(true);
    };

    const handleEdit = (warehouse) => {
        setEditId(warehouse.id);
        setFormData({
            name: warehouse.name || "",
            address: warehouse.address || "",
            city: warehouse.city || "",
            state: warehouse.state || "",
            pincode: warehouse.pincode || "",
            latitude: warehouse.latitude || "",
            longitude: warehouse.longitude || "",
            c2_code: warehouse.c2_code || "",
            store_id: warehouse.store_id || "",
            prod_code: warehouse.prod_code || "02",
            security_key: warehouse.security_key || "",
            phone: warehouse.phone || "",
            email: warehouse.email || "",
            manager_name: warehouse.manager_name || "",
            manager_phone: warehouse.manager_phone || "",
            is_primary: warehouse.is_primary || false,
            is_active: warehouse.is_active !== false
        });
        setShowAddModal(true);
    };

    const handleDelete = async (id) => {
        setIsSubmitting(true);
        try {
            const res = await deleteWarehouseAPI(id);
            if (res.status >= 200 && res.status < 300) {
                setShowDeleteConfirm(null);
                fetchWarehouses();
            }
        } catch (err) {
            console.error("Error deleting warehouse:", err);
            alert("Failed to delete warehouse.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            const submissionData = {
                ...formData,
                latitude: formData.latitude ? parseFloat(formData.latitude) : null,
                longitude: formData.longitude ? parseFloat(formData.longitude) : null
            };

            let res;
            if (editId) {
                res = await updateWarehouseAPI(editId, submissionData);
            } else {
                res = await addWarehouseAPI(submissionData);
            }

            if (res.status >= 200 && res.status < 300) {
                closeModal();
                fetchWarehouses();
            }
        } catch (err) {
            console.error("Error saving warehouse:", err);
            alert("Failed to save warehouse. Please check the details.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const closeModal = () => {
        setShowAddModal(false);
        setEditId(null);
        setFormData({
            name: "", address: "", city: "", state: "", pincode: "",
            latitude: "", longitude: "", c2_code: "", store_id: "",
            prod_code: "02", security_key: "", phone: "", email: "",
            manager_name: "", manager_phone: "", is_primary: false, is_active: true
        });
    };

    const filteredWarehouses = warehouses.filter(w => {
        const matchesSearch = w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            w.city.toLowerCase().includes(searchQuery.toLowerCase()) ||
            w.store_id.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesStatus = statusFilter === 'all' ||
            (statusFilter === 'active' && w.is_active) ||
            (statusFilter === 'inactive' && !w.is_active);

        return matchesSearch && matchesStatus;
    });

    // Pagination logic
    const totalPages = Math.ceil(filteredWarehouses.length / itemsPerPage);
    const indexOfLastItem = currentPage * itemsPerPage;
    const indexOfFirstItem = indexOfLastItem - itemsPerPage;
    const currentItems = filteredWarehouses.slice(indexOfFirstItem, indexOfLastItem);

    // Reset to first page when search changes
    useEffect(() => {
        setCurrentPage(1);
    }, [searchQuery, statusFilter]);

    const paginate = (pageNumber) => setCurrentPage(pageNumber);

    return (
        <div className=" ml-2 mt-2">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                <div>
                    <h1 className="text-xl md:text-2xl font-bold text-gray-800">Warehouse Management</h1>
                    <p className="text-gray-500 text-sm">Manage and monitor distribution centers and stock points</p>
                </div>
            </div>

            {/* Stats Overview  */}
            <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
                <div className="bg-white p-3 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between hover:border-[#127690]/30 transition-all group">
                    <div>
                        <p className="text-[9px] font-bold text-gray-800 uppercase tracking-widest mb-0.5">Total Warehouses</p>
                        <p className="text-xl font-semibold text-gray-800 leading-none">{warehouses.length}</p>
                    </div>
                    <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center text-[#127690] group-hover:scale-110 transition-transform">
                        <Building2 size={16} />
                    </div>
                </div>

                <div className="bg-white p-3 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between hover:border-amber-200 transition-all group">
                    <div>
                        <p className="text-[9px] font-bold text-gray-800 uppercase tracking-widest mb-0.5">Primary Hubs</p>
                        <p className="text-xl font-semibold text-gray-800 leading-none">{warehouses.filter(w => w.is_primary).length}</p>
                    </div>
                    <div className="w-8 h-8 bg-amber-50 rounded-lg flex items-center justify-center text-amber-600 group-hover:scale-110 transition-transform">
                        <Globe size={16} />
                    </div>
                </div>

                <div className="bg-white p-3 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between hover:border-green-200 transition-all group">
                    <div>
                        <p className="text-[9px] font-bold text-gray-800 uppercase tracking-widest mb-0.5">Active Units</p>
                        <p className="text-xl font-semibold text-gray-800 leading-none">{warehouses.filter(w => w.is_active).length}</p>
                    </div>
                    <div className="w-8 h-8 bg-green-50 rounded-lg flex items-center justify-center text-green-600 group-hover:scale-110 transition-transform">
                        <Activity size={16} />
                    </div>
                </div>

                <div className="bg-white p-3 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between hover:border-red-200 transition-all group">
                    <div>
                        <p className="text-[9px] font-bold text-gray-800 uppercase tracking-widest mb-0.5">Offline Points</p>
                        <p className="text-xl font-semibold text-gray-800 leading-none">{warehouses.filter(w => !w.is_active).length}</p>
                    </div>
                    <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center text-red-600 group-hover:scale-110 transition-transform">
                        <X size={14} />
                    </div>
                </div>
            </div>

            {/* Filter & Search Bar - View Toggles on left */}
            <div className="mb-2 flex flex-row md:flex-row justify-between gap-4 items-center">
                <div className="flex items-center bg-gray-100 p-1 rounded-xl shadow-sm border border-gray-200">
                    <button
                        onClick={() => setViewMode('grid')}
                        className={`p-1.5 md:p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-white shadow-sm text-[#127690]' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        <LayoutGrid className="w-3.5 h-3.5 md:w-5 md:h-4" />
                    </button>
                    <button
                        onClick={() => setViewMode('list')}
                        className={`p-1.5 md:p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white shadow-sm text-[#127690]' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                        <List className="w-3.5 h-3.5 md:w-5 md:h-4" />
                    </button>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl shadow-sm flex items-center pl-4 transition-all">
                    <div className="flex items-center">
                        <Search className="text-gray-400 mr-3" size={18} />
                        <input
                            type="text"
                            placeholder="Search by name, city or ID..."
                            className="w-[150px] sm:w-[100px] md:w-[380px] py-2.5 bg-transparent outline-none text-[10px] md:text-sm text-gray-700 placeholder:text-gray-400"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="flex items-center gap-2 bg-[#127690] text-white px-3 md:px-5 py-2 rounded-lg hover:bg-[#0e5e73] transition-all shadow-sm active:scale-95 text-sm font-medium whitespace-nowrap"
                    >
                        <Plus size={18} />
                        <span className="hidden md:inline">Add Warehouse</span>
                    </button>
                </div>
            </div>

            {/* Content Area */}
            {loading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <div className="w-12 h-12 border-4 border-[#127690] border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-gray-500 font-medium animate-pulse">Fetching warehouse data...</p>
                </div>
            ) : filteredWarehouses.length === 0 ? (
                <div className="bg-white rounded-3xl p-20 text-center border border-dashed border-gray-200">
                    <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Building2 className="text-gray-300" size={40} />
                    </div>
                    <h3 className="text-lg font-bold text-gray-700">No Warehouses Found</h3>
                    <p className="text-gray-500 max-w-xs mx-auto mt-2">
                        {searchQuery ? "We couldn't find any warehouses matching your search criteria." : "Start by adding your first distribution center to manage your inventory."}
                    </p>
                </div>
            ) : viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {currentItems.map((warehouse) => (
                        <div key={warehouse.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all group relative overflow-hidden">
                            {warehouse.is_primary && (
                                <div className="absolute top-0 right-0 overflow-hidden w-20 h-20 pointer-events-none">
                                    <div className="absolute top-0 right-0 bg-[#127690] text-white text-[9px] font-bold py-1 w-[100px] text-center rotate-45 translate-x-[30px] translate-y-[12px] shadow-sm uppercase tracking-widest">Primary</div>
                                </div>
                            )}

                            <div className="p-3">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${warehouse.is_active ? 'bg-blue-50 text-[#127690]' : 'bg-gray-100 text-gray-400'}`}>
                                            <Building2 size={24} />
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{warehouse.store_id}</p>
                                            <h3 className="font-bold text-gray-800 group-hover:text-[#127690] transition-colors">{warehouse.name}</h3>
                                        </div>
                                    </div>
                                    <div className="relative group/menu">
                                        <button className="text-gray-400 hover:text-gray-600 p-1 hover:bg-gray-50 rounded-lg">
                                            <MoreVertical size={18} />
                                        </button>
                                        <div className="absolute right-0 top-full mt-1 w-32 bg-white rounded-xl shadow-xl border border-gray-100 py-1 hidden group-hover/menu:block z-20">
                                            <button onClick={() => handleView(warehouse)} className="w-full px-4 py-2 text-left text-xs font-bold text-gray-600 hover:bg-gray-50 hover:text-teal-600">View Details</button>
                                            <button onClick={() => handleEdit(warehouse)} className="w-full px-4 py-2 text-left text-xs font-bold text-gray-600 hover:bg-gray-50 hover:text-[#127690]">Edit Details</button>
                                            <button onClick={() => setShowDeleteConfirm(warehouse.id)} className="w-full px-4 py-2 text-left text-xs font-bold text-red-500 hover:bg-red-50">Delete</button>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3 mt-6">
                                    <div className="flex items-start gap-3 text-sm text-gray-600">
                                        <MapPin size={16} className="mt-0.5 text-gray-400 shrink-0" />
                                        <span>{warehouse.address}, {warehouse.city}, {warehouse.pincode}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-sm text-gray-600">
                                        <Phone size={16} className="text-gray-400 shrink-0" />
                                        <span>{warehouse.phone || "No phone provided"}</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-sm text-gray-600">
                                        <User size={16} className="text-gray-400 shrink-0" />
                                        <span className="font-medium">{warehouse.manager_name || "Unassigned"}</span>
                                    </div>
                                </div>

                                <div className="mt-2 pt-1 border-t border-gray-50 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className={`w-2 h-2 rounded-full ${warehouse.is_active ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`}></div>
                                        <span className={`text-xs font-bold ${warehouse.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                                            {warehouse.is_active ? 'Operational' : 'Inactive'}
                                        </span>
                                    </div>

                                    <div className="flex gap-2 text-[10px] font-mono font-bold text-gray-400">
                                        <span className="bg-gray-50 px-2 py-1 rounded border border-gray-100">{warehouse.c2_code}</span>
                                        <span className="bg-gray-50 px-2 py-1 rounded border border-gray-100">{warehouse.prod_code}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="bg-white rounded-xl border border-gray-100 overflow-x-auto shadow-sm mt-2 custom-scrollbar">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-[#e9eff4] border-b border-gray-100">
                                <th className="px-2 py-2 text-[12px] font-bold text-[#505050] uppercase tracking-wide">S.No</th>
                                <th className="px-5 py-2 text-[12px] font-bold text-[#505050] uppercase tracking-wide">ID</th>
                                <th className="px-4 py-2 text-[12px] font-bold text-[#505050] uppercase tracking-wide">Warehouse Name</th>
                                <th className="px-4 py-2 text-[12px] font-bold text-[#505050] uppercase tracking-wide">City</th>
                                <th className="px-4 py-2 text-[12px] font-bold text-[#505050] uppercase tracking-wide">Contact</th>
                                <th className="px-4 py-2 text-[12px] font-bold text-[#505050] uppercase tracking-wide">Email</th>
                                <th className="px-4 py-2 text-[12px] font-bold text-[#505050] uppercase tracking-wide">Status</th>
                                <th className="px-1 py-2 text-[12px] font-bold text-[#505050] uppercase tracking-wide text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {currentItems.map((warehouse, index) => (
                                <tr key={warehouse.id} className="hover:bg-gray-50/50 transition-colors">
                                    <td className="text-center py-2">
                                        <span className="font-medium text-[#127690] text-xs md:text-xs">{indexOfFirstItem + index + 1}</span>
                                    </td>
                                    <td className="text-center px-4 py-2 whitespace-nowrap">
                                        <span className="font-medium text-[#127690] text-xs md:text-sm tracking-tight">{warehouse.store_id}</span>
                                    </td>
                                    <td className="px-3 py-2">
                                        <p className="font-semibold text-[#127690] text-sm">{warehouse.name}</p>
                                    </td>
                                    <td className="px-3 py-2 text-sm font-semibold text-gray-700">
                                        {warehouse.city}
                                    </td>
                                    <td className="px-3 py-2 text-sm font-semibold text-gray-700">
                                        {warehouse.phone || "---"}
                                    </td>
                                    <td className="px-3 py-2 text-sm font-semibold text-gray-700">
                                        {warehouse.email || "---"}
                                    </td>
                                    <td className="px-1 py-2">
                                        {warehouse.is_active ? (
                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#e8fbf3] text-[#10b981] text-xs font-bold border border-[#d1fae5] uppercase tracking-wider">
                                                <div className="w-1 h-1 rounded-full bg-[#10b981]"></div>
                                                Active
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#fef2f2] text-[#ef4444] text-xs font-bold border border-[#fee2e2] uppercase tracking-wider">
                                                <div className="w-1 h-1 rounded-full bg-[#ef4444]"></div>
                                                Inactive
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-2 text-right">
                                        <div className="flex justify-end gap-3">
                                            <button
                                                onClick={() => handleView(warehouse)}
                                                className="text-gray-400 hover:text-teal-600 transition-colors"
                                                title="View Details"
                                            >
                                                <Eye size={18} />
                                            </button>
                                            <button
                                                onClick={() => handleEdit(warehouse)}
                                                className="text-gray-400 hover:text-blue-600 transition-colors"
                                                title="Edit Warehouse"
                                            >
                                                <Edit size={17} />
                                            </button>
                                            <button
                                                onClick={() => setShowDeleteConfirm(warehouse.id)}
                                                className="text-gray-400 hover:text-red-500 transition-colors"
                                                title="Delete Warehouse"
                                            >
                                                <Trash2 size={17} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

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
                            // Basic logic to show first, last, and pages around current
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

            {/* Add/Edit Warehouse Modal - Optimized for one-screen view */}
            {showAddModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-2">
                    <div className="bg-white w-full max-w-6xl max-h-[95vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in duration-300">
                        <div className="px-6 py-3 border-b border-gray-100 flex items-center justify-between bg-white sticky top-0 z-10">
                            <div>
                                <h2 className="text-lg font-bold text-gray-800">{editId ? 'Edit Warehouse' : 'Add New Warehouse'}</h2>
                                <p className="text-xs text-gray-500">Distribution center and ERP configuration</p>
                            </div>
                            <button
                                onClick={closeModal}
                                className="p-1.5 hover:bg-gray-50 rounded-full transition-colors text-gray-400"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto px-6 py-4">
                            <form id="warehouseForm" onSubmit={handleSubmit} className="h-full">
                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
                                    {/* Left Column - Basic Information */}
                                    <div className="lg:col-span-7 space-y-4">
                                        <section>
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-1 h-3.5 bg-[#127690] rounded-full"></div>
                                                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">Basic Information</h3>
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1">WAREHOUSE NAME *</label>
                                                    <input
                                                        required name="name" value={formData.name} onChange={handleInputChange}
                                                        className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm"
                                                        placeholder="e.g. Bangalore Main Hub"
                                                    />
                                                </div>
                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1">STORE / WAREHOUSE ID *</label>
                                                    <input
                                                        required name="store_id" value={formData.store_id} onChange={handleInputChange}
                                                        className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm font-mono"
                                                        placeholder="e.g. WH-001"
                                                    />
                                                </div>
                                                <div className="md:col-span-2 space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1">FULL ADDRESS *</label>
                                                    <textarea
                                                        required name="address" value={formData.address} onChange={handleInputChange}
                                                        className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm min-h-[60px] resize-none"
                                                        placeholder="Enter complete street address..."
                                                    />
                                                </div>
                                                <div className="grid grid-cols-3 gap-3 md:col-span-2">
                                                    <div className="space-y-1">
                                                        <label className="text-[10px] font-bold text-gray-500 ml-1">CITY *</label>
                                                        <input
                                                            required name="city" value={formData.city} onChange={handleInputChange}
                                                            className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm"
                                                        />
                                                    </div>
                                                    <div className="space-y-1">
                                                        <label className="text-[10px] font-bold text-gray-500 ml-1">STATE *</label>
                                                        <input
                                                            required name="state" value={formData.state} onChange={handleInputChange}
                                                            className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm"
                                                        />
                                                    </div>
                                                    <div className="space-y-1">
                                                        <label className="text-[10px] font-bold text-gray-500 ml-1">PINCODE *</label>
                                                        <input
                                                            required name="pincode" value={formData.pincode} onChange={handleInputChange}
                                                            className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </section>

                                        <section>
                                            <div className="flex items-center gap-2 mb-3 pt-2">
                                                <div className="w-1 h-3.5 bg-[#127690] rounded-full"></div>
                                                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">Contact & Personnel</h3>
                                            </div>
                                            <div className="grid grid-cols-2 gap-3">
                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1">MANAGER NAME</label>
                                                    <div className="relative">
                                                        <User className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                                                        <input
                                                            name="manager_name" value={formData.manager_name} onChange={handleInputChange}
                                                            className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm"
                                                        />
                                                    </div>
                                                </div>
                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1">MANAGER PHONE</label>
                                                    <div className="relative">
                                                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                                                        <input
                                                            name="manager_phone" value={formData.manager_phone} onChange={handleInputChange}
                                                            className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm"
                                                        />
                                                    </div>
                                                </div>
                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1">WH PHONE</label>
                                                    <div className="relative">
                                                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                                                        <input
                                                            name="phone" value={formData.phone} onChange={handleInputChange}
                                                            className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm"
                                                        />
                                                    </div>
                                                </div>
                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1">EMAIL ADDRESS</label>
                                                    <div className="relative">
                                                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
                                                        <input
                                                            type="email" name="email" value={formData.email} onChange={handleInputChange}
                                                            className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-[#127690] focus:bg-white transition-all text-sm"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </section>
                                    </div>

                                    {/* Right Column - System Configuration */}
                                    <div className="lg:col-span-5 bg-gray-50/50 rounded-2xl p-4 border border-gray-100 space-y-4">
                                        <section>
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-1 h-3.5 bg-[#127690] rounded-full"></div>
                                                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">ERP Configuration</h3>
                                            </div>
                                            <div className="space-y-3">
                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1 flex items-center gap-1">
                                                        <Database size={10} /> C2 CODE *
                                                    </label>
                                                    <input
                                                        required name="c2_code" value={formData.c2_code} onChange={handleInputChange}
                                                        className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl outline-none focus:border-[#127690] transition-all text-base font-mono"
                                                        placeholder="e.g. 03C000"
                                                    />
                                                </div>
                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1">PROD CODE</label>
                                                    <input
                                                        name="prod_code" value={formData.prod_code} onChange={handleInputChange}
                                                        className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl outline-none focus:border-[#127690] transition-all text-base font-mono"
                                                        placeholder="e.g. 02"
                                                    />
                                                </div>

                                                <div className="space-y-1">
                                                    <label className="text-[10px] font-bold text-gray-500 ml-1 flex items-center gap-1">
                                                        <Shield size={10} /> SECURITY KEY *
                                                    </label>
                                                    <input
                                                        required name="security_key" value={formData.security_key} onChange={handleInputChange}
                                                        className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl outline-none focus:border-[#127690] transition-all text-base font-mono"
                                                        placeholder="ERP Security Key"
                                                    />
                                                </div>
                                                <div className="grid grid-cols-2 gap-3 pt-2">
                                                    <div className="space-y-1">
                                                        <label className="text-[10px] font-bold text-gray-500 ml-1">LATITUDE</label>
                                                        <input
                                                            type="number" step="any" name="latitude" value={formData.latitude} onChange={handleInputChange}
                                                            className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl outline-none focus:border-[#127690] transition-all text-base"
                                                        />
                                                    </div>
                                                    <div className="space-y-1">
                                                        <label className="text-[10px] font-bold text-gray-500 ml-1">LONGITUDE</label>
                                                        <input
                                                            type="number" step="any" name="longitude" value={formData.longitude} onChange={handleInputChange}
                                                            className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl outline-none focus:border-[#127690] transition-all text-base"
                                                        />
                                                    </div>
                                                </div>

                                                <div className="flex flex-wrap items-center gap-4 pt-4">
                                                    <label className="flex items-center gap-2 cursor-pointer group">
                                                        <div className="relative">
                                                            <input
                                                                type="checkbox" name="is_primary" checked={formData.is_primary} onChange={handleInputChange}
                                                                className="sr-only peer"
                                                            />
                                                            <div className="w-9 h-4.5 bg-gray-200 rounded-full peer peer-checked:bg-[#127690] transition-all duration-300"></div>
                                                            <div className="absolute left-1 top-0.5 w-3.5 h-3.5 bg-white rounded-full transition-all peer-checked:translate-x-4.5"></div>
                                                        </div>
                                                        <span className="text-[10px] font-bold text-gray-600 group-hover:text-gray-800 transition-colors uppercase">Primary Hub</span>
                                                    </label>
                                                    <label className="flex items-center gap-2 cursor-pointer group">
                                                        <div className="relative">
                                                            <input
                                                                type="checkbox" name="is_active" checked={formData.is_active} onChange={handleInputChange}
                                                                className="sr-only peer"
                                                            />
                                                            <div className="w-9 h-4.5 bg-gray-200 rounded-full peer peer-checked:bg-green-500 transition-all duration-300"></div>
                                                            <div className="absolute left-1 top-0.5 w-3.5 h-3.5 bg-white rounded-full transition-all peer-checked:translate-x-4.5"></div>
                                                        </div>
                                                        <span className="text-[10px] font-bold text-gray-600 group-hover:text-gray-800 transition-colors uppercase">Active</span>
                                                    </label>
                                                </div>
                                            </div>
                                        </section>
                                    </div>
                                </div>
                            </form>
                        </div>

                        <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-end gap-3 sticky bottom-0 z-10">
                            <button
                                onClick={closeModal}
                                className="px-5 py-2 rounded-xl border border-gray-200 text-gray-600 font-bold text-sm hover:bg-white hover:border-gray-300 transition-all active:scale-95"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit" form="warehouseForm"
                                disabled={isSubmitting}
                                className="px-6 py-2 rounded-xl bg-[#127690] text-white font-bold text-sm hover:bg-[#0e5e73] transition-all shadow-md active:scale-95 flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {isSubmitting ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                        <span>Saving...</span>
                                    </>
                                ) : (
                                    <span>{editId ? 'Update Warehouse' : 'Create Warehouse'}</span>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
                    <div className="bg-white w-full max-w-md rounded-3xl shadow-2xl p-4 animate-in fade-in zoom-in duration-200">
                        <h2 className="text-xl font-bold text-gray-800 text-center mb-2">Delete Warehouse?</h2>
                        <p className="text-gray-500 text-center text-sm mb-5">
                            This action cannot be undone. All data associated with this distribution center will be permanently removed.
                        </p>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowDeleteConfirm(null)}
                                className="flex-1 px-6 py-3 rounded-xl border border-gray-200 text-gray-600 font-bold text-sm hover:bg-gray-50 transition-all"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleDelete(showDeleteConfirm)}
                                disabled={isSubmitting}
                                className="flex-1 px-6 py-3 rounded-xl bg-red-700 text-white font-bold text-sm hover:bg-red-800 transition-all shadow-lg shadow-red-200 active:scale-95 disabled:opacity-70"
                            >
                                {isSubmitting ? "Deleting..." : "Yes, Delete"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* View Details Modal */}
            {showViewModal && selectedWarehouse && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 overflow-y-auto">
                    <div className="bg-white w-full max-w-4xl rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200 my-4">
                        {/* Header */}
                        <div className="bg-[#127690] p-2 text-white relative">
                            <button
                                onClick={() => setShowViewModal(false)}
                                className="absolute top-4 right-4 p-2 hover:bg-white/10 rounded-full transition-colors"
                            >
                                <X size={20} />
                            </button>
                            <div className="flex items-center gap-4">
                                <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center">
                                    <Building2 size={32} />
                                </div>
                                <div>
                                    <p className="text-white/70 text-xs font-bold uppercase tracking-widest mb-1">{selectedWarehouse.store_id}</p>
                                    <h2 className="text-2xl font-bold">{selectedWarehouse.name}</h2>
                                    <div className="flex gap-2 mt-2">
                                        {selectedWarehouse.is_primary && (
                                            <span className="bg-white/20 px-2 py-0.5 rounded text-[10px] font-bold uppercase">Primary Hub</span>
                                        )}
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${selectedWarehouse.is_active ? 'bg-green-400/20 text-green-100' : 'bg-red-400/20 text-red-100'}`}>
                                            {selectedWarehouse.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Body */}
                        <div className="p-5 max-h-[70vh] overflow-y-auto custom-scrollbar text-[#505050]">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {/* Basic Info */}
                                <div>
                                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                        <Building2 size={14} /> Basic Information
                                    </h3>
                                    <div className="space-y-4">
                                        <div className='space-y-1'>
                                            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Warehouse Name</p>
                                            <p className="text-base font-medium text-gray-700">{selectedWarehouse.name}</p>
                                        </div>
                                        <div className='space-y-2'>
                                            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Location</p>
                                            <p className="text-base font-medium text-gray-700">{selectedWarehouse.address}</p>
                                            <p className="text-base text-gray-500">{selectedWarehouse.city}, {selectedWarehouse.state} - {selectedWarehouse.pincode}</p>
                                        </div>
                                        <div className='space-y-2'>
                                            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Contact Details</p>
                                            <p className="text-base font-medium text-gray-700 flex items-center gap-2"><Phone size={14} className="text-gray-400" /> {selectedWarehouse.phone || "---"}</p>
                                            <p className="text-base font-medium text-gray-700 flex items-center gap-2"><Mail size={14} className="text-gray-400" /> {selectedWarehouse.email || "---"}</p>
                                        </div>
                                    </div>
                                </div>

                                {/* Management Info */}
                                <div>
                                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                        <User size={14} /> Management & ERP
                                    </h3>
                                    <div className="space-y-4">
                                        <div className='space-y-1'>
                                            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Manager</p>
                                            <p className="text-base font-medium text-gray-700">{selectedWarehouse.manager_name || "Unassigned"}</p>
                                            {selectedWarehouse.manager_phone && (
                                                <p className="text-base text-gray-500">{selectedWarehouse.manager_phone}</p>
                                            )}
                                        </div>
                                        <div className="bg-gray-50 p-4 rounded-2xl border border-gray-100">
                                            <p className="text-[11px] font-semibold text-[#127690] uppercase mb-3 flex items-center gap-2">
                                                <Database size={12} /> ERP Configuration
                                            </p>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div className='space-y-1'>
                                                    <p className="text-[12px] font-semibold text-gray-500 uppercase tracking-wide">C2 Code</p>
                                                    <p className="text-base font-mono font-bold text-gray-700">{selectedWarehouse.c2_code}</p>
                                                </div>
                                                <div className='space-y-1'>
                                                    <p className="text-[12px] font-semibold text-gray-500 uppercase tracking-wide">Prod Code</p>
                                                    <p className="text-base font-mono font-bold text-gray-700">{selectedWarehouse.prod_code}</p>
                                                </div>
                                                <div className="col-span-2 pt-2 border-t border-gray-100">
                                                    <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Lattitude</p>
                                                    <p className="text-base font-mono text-gray-600 break-all">{selectedWarehouse.latitude || "Not Set"}</p>
                                                </div>
                                                <div className="col-span-2 pt-2 border-t border-gray-100">
                                                    <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Longitude</p>
                                                    <p className="text-base font-mono text-gray-600 break-all">{selectedWarehouse.longitude || "Not Set"}</p>
                                                </div>
                                                {/* <div className="col-span-2 pt-2 border-t border-gray-100">
                                                    <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">Security Key</p>
                                                    <p className="text-base font-mono text-gray-600 break-all">{selectedWarehouse.security_key || "Not Set"}</p>
                                                </div> */}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Additional Metadata */}
                            <div className="mt-8 pt-6 border-t border-gray-100 flex flex-wrap gap-6 text-[11px] font-bold text-gray-700 uppercase tracking-widest">
                                <div className="flex items-center gap-2">
                                    <Activity size={14} />
                                    Last Updated: {new Date(selectedWarehouse.created_at).toLocaleDateString()}
                                </div>
                                <div className="flex items-center gap-2">
                                    <Globe size={14} />
                                    Region: {selectedWarehouse.state}
                                </div>
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="p-2 bg-gray-50 border-t border-gray-100 flex justify-end">
                            <button
                                onClick={() => setShowViewModal(false)}
                                className="px-8 py-2 bg-[#127690] text-white rounded-xl font-bold text-sm hover:bg-[#0e5e73] transition-all active:scale-95 shadow-lg shadow-[#127690]/20"
                            >
                                Close View
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Warehouse;

