import React, { useState, useEffect } from "react";
import { Search, Package, Archive, Edit, Trash2, Plus, X, Upload } from "lucide-react";
import SummaryCard from "../components/SummaryCard";
import { getCategoriesAPI, addCategoryAPI, updateCategoryAPI, deleteCategoryAPI } from "../services/allAPI";

export default function Categories() {
    const [search, setSearch] = useState("");
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

    const [categoriesData, setCategoriesData] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchCategories = async () => {
        setLoading(true);
        try {
            const response = await getCategoriesAPI();
            setCategoriesData(response.data.data || []);
            console.log("Fetched categories:", response.data.data);
        } catch (error) {
            console.error("Error fetching categories:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCategories();
    }, []);

    const [toast, setToast] = useState({ show: false, message: "", type: "success" });
    const showToast = (message, type = "success") => {
        setToast({ show: true, message, type });
        setTimeout(() => setToast({ show: false, message: "", type: "success" }), 3000);
    };

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isEditMode, setIsEditMode] = useState(false);
    const [selectedCategoryId, setSelectedCategoryId] = useState(null);
    const [categoryToDelete, setCategoryToDelete] = useState(null);
    const [formState, setFormState] = useState({
        name: "",
        is_active: true,
        icon: null,
        icon_preview: null
    });

    const handleSearch = (e) => {
        setSearch(e.target.value);
        setCurrentPage(1);
    };

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setFormState(prev => ({
                ...prev,
                icon: file,
                icon_preview: URL.createObjectURL(file)
            }));
        }
    };

    const handleOpenModal = (category = null) => {
        if (category) {
            setIsEditMode(true);
            setSelectedCategoryId(category.id);
            setFormState({
                name: category.name,
                is_active: category.is_active,
                icon: null,
                icon_preview: category.icon
            });
        } else {
            setIsEditMode(false);
            setSelectedCategoryId(null);
            setFormState({
                name: "",
                is_active: true,
                icon: null,
                icon_preview: null
            });
        }
        setIsModalOpen(true);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            const formData = new FormData();
            formData.append("name", formState.name);
            formData.append("is_active", formState.is_active ? "True" : "False");
            if (formState.icon) {
                formData.append("icon", formState.icon);
            }

            if (isEditMode) {
                if (selectedCategoryId && !selectedCategoryId.toString().startsWith("CAT")) {
                    await updateCategoryAPI(selectedCategoryId, formData);
                }
                showToast("Category updated successfully!", "success");
            } else {
                await addCategoryAPI(formData);
                showToast("Category created successfully!", "success");
            }
            setIsModalOpen(false);
            fetchCategories();

        } catch (error) {
            console.error("Error submitting category:", error);
            showToast("Failed to save category.", "error");
        }
    };

    const handleDelete = (id) => {
        setCategoryToDelete(id);
    };

    const confirmDelete = async () => {
        if (!categoryToDelete) return;
        try {
            if (categoryToDelete && !categoryToDelete.toString().startsWith("CAT")) {
                await deleteCategoryAPI(categoryToDelete);
            }
            showToast("Category deleted successfully!", "success");
            fetchCategories();
        } catch (error) {
            console.error("Error deleting category:", error);
            showToast("Failed to delete category.", "error");
        }
        setCategoryToDelete(null);
    };

    const filteredCategories = categoriesData.filter((cat) =>
        cat.name?.toLowerCase().includes(search.toLowerCase())
    );

    const totalPages = Math.ceil(filteredCategories.length / itemsPerPage);
    const paginatedCategories = filteredCategories.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    return (
        <div className="h-full overflow-hidden flex flex-col relative ml-2 mt-3">
            {toast.show && (
                <div className={`fixed top-6 right-6 z-[200] px-4 py-3 rounded-xl shadow-xl flex items-center gap-3 transition-all duration-300 animate-in fade-in slide-in-from-top-4 ${toast.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
                    {toast.type === 'success' ? <Package size={20} className="text-green-600" /> : <X size={20} className="text-red-600" />}
                    <span className="text-sm font-semibold">{toast.message}</span>
                    <button onClick={() => setToast({ show: false, message: "", type: "success" })} className="p-1 hover:bg-white/50 rounded-lg transition-colors"><X size={16} /></button>
                </div>
            )}

            {/* Header Section */}
            <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-semibold text-[#505050]">Category Management</h1>
                    <p className="text-sm text-[#505050]">Manage product categories and brands</p>
                </div>

                <div className="flex items-center gap-3 border border-gray-200 bg-white rounded-xl px-4 py-2 shadow-sm w-full md:w-[400px]">
                    <Search size={18} className="text-gray-400 shrink-0" />
                    <input
                        type="text"
                        placeholder="Search categories..."
                        value={search}
                        onChange={handleSearch}
                        className="flex-1 bg-transparent border-none outline-none px-3 text-sm text-[#505050] placeholder:text-[#9EA2A7]"
                    />
                </div>
            </div>

            {/* Summary Cards */}
            <div className="flex flex-col md:flex-row gap-4 lg:gap-6 mb-6">
                <SummaryCard
                    title="Total Categories"
                    value={categoriesData.length.toString()}
                    icon={<Archive size={20} />}
                    bgClass="bg-[#e9fedf]"
                    textClass="text-[#207238]"
                    iconClass=""
                    blobColor1="bg-[#A3FF63]"
                    blobColor2="bg-[#33CB6C]"
                />
                <SummaryCard
                    title="Active Categories"
                    value={categoriesData.filter(c => c.is_active).length.toString()}
                    icon={<Package size={20} />}
                    bgClass="bg-[#d8e9ff]"
                    textClass="text-[#1D4ED8]"
                    iconClass="text-blue-600"
                    blobColor1="bg-[#83ACE5]"
                    blobColor2="bg-[#1447EA]"
                />
                <div className="flex-1 flex justify-end items-end">
                    <button
                        onClick={() => handleOpenModal()}
                        className="flex items-center justify-center h-12 gap-2 px-6 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-xl transition-all shadow-sm"
                    >
                        <Plus size={18} />
                        Add Category
                    </button>
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.04)] border border-gray-100 flex-1 overflow-hidden flex flex-col">
                <div className="flex-1 overflow-auto">
                    <table className="min-w-full w-full text-left border-collapse">
                        <thead className="bg-[#e7f1f4] text-[#505050] text-xs   top-0 z-10">
                            <tr>
                                <th className="px-6 py-2 font-medium text-center w-16">ID</th>
                                <th className="px-6 py-2 font-medium w-32">ICON</th>
                                <th className="px-6 py-2 font-medium">CATEGORY NAME</th>
                                <th className="px-6 py-2 font-medium">STATUS</th>
                                <th className="px-6 py-2 font-medium text-center w-32">ACTION</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm text-gray-700 divide-y divide-gray-50">
                            {loading ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-10 text-center text-gray-400">
                                        Loading categories...
                                    </td>
                                </tr>
                            ) : paginatedCategories.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-10 text-center text-gray-400">
                                        No categories found.
                                    </td>
                                </tr>
                            ) : (
                                paginatedCategories.map((cat, index) => (
                                    <tr key={cat.id} className={`${index % 2 === 0 ? "bg-white" : "bg-[#F7F9FB]"} hover:bg-[#EEF2F6] transition`}>
                                        <td className="px-6 py-3 text-[13px] font-bold text-gray-500 text-center">{cat.id}</td>
                                        <td className="px-6 py-3">
                                            {cat.icon ? (
                                                <img src={cat.icon} alt={cat.name} className="w-10 h-10 object-contain rounded-md border border-gray-200 bg-white p-1" />
                                            ) : (
                                                <div className="w-10 h-10 rounded-md bg-gray-100 flex items-center justify-center border border-gray-200">
                                                    <Archive size={16} className="text-gray-400" />
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-6 py-2 text-[14px] font-medium text-gray-900">{cat.name}</td>
                                        <td className="px-6 py-2 text-[13px]">
                                            <span className={`px-2 py-1 rounded-full text-[11px] font-semibold ${cat.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                                {cat.is_active ? "Active" : "Inactive"}
                                            </span>
                                        </td>
                                        <td className="px-6 py-2 text-center">
                                            <div className="flex items-center justify-center gap-2">
                                                <button onClick={() => handleOpenModal(cat)} className="p-1 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Edit Category">
                                                    <Edit size={16} />
                                                </button>
                                                <button onClick={() => handleDelete(cat.id)} className="p-1 text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Delete Category">
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

                {/* Pagination Controls */}
                <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-center bg-white">
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                            disabled={currentPage === 1}
                            className={`px-4 py-1.5 rounded-lg border border-gray-200 text-sm font-semibold transition-all ${currentPage === 1 ? 'bg-gray-50 text-gray-300 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50 active:scale-95 shadow-sm'}`}
                        >
                            Previous
                        </button>
                        <span className="text-sm font-bold text-[#505050] px-2">Page {currentPage} of {totalPages || 1}</span>
                        <button
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            disabled={currentPage === totalPages || totalPages === 0}
                            className={`px-4 py-1.5 rounded-lg border border-gray-200 text-sm font-semibold transition-all ${currentPage === totalPages || totalPages === 0 ? 'bg-gray-50 text-gray-300 cursor-not-allowed' : 'bg-white text-gray-700 hover:bg-gray-50 active:scale-95 shadow-sm'}`}
                        >
                            Next
                        </button>
                    </div>
                </div>
            </div>

            {/* Create / Edit Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={() => setIsModalOpen(false)}>
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden relative" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                            <h2 className="text-lg font-semibold text-gray-800">{isEditMode ? "Edit Category" : "Add New Category"}</h2>
                            <button onClick={() => setIsModalOpen(false)} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 transition-colors">
                                <X size={20} />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6">
                            <div className="space-y-4">
                                {/* Name Input */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Category Name *</label>
                                    <input
                                        type="text"
                                        value={formState.name}
                                        onChange={(e) => setFormState({ ...formState, name: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm"
                                        placeholder="e.g. Analgesics..."
                                        required
                                    />
                                </div>

                                {/* Active Toggle */}
                                <div className="flex items-center gap-3">
                                    <label className="text-sm font-medium text-gray-700">Status</label>
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={formState.is_active}
                                            onChange={(e) => setFormState({ ...formState, is_active: e.target.checked })}
                                            className="sr-only peer"
                                        />
                                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal-600"></div>
                                        <span className="ml-3 text-sm font-medium text-gray-700">{formState.is_active ? "Active" : "Inactive"}</span>
                                    </label>
                                </div>

                                {/* Image Upload */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Category Icon</label>
                                    <div className="flex items-center gap-4 mt-2">
                                        <div className="w-16 h-16 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center overflow-hidden bg-gray-50 relative group">
                                            {formState.icon_preview ? (
                                                <img src={formState.icon_preview} alt="Preview" className="w-full h-full object-contain p-1" />
                                            ) : (
                                                <Upload size={20} className="text-gray-400" />
                                            )}
                                            <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Upload size={16} className="text-white" />
                                            </div>
                                            <input type="file" accept="image/*" onChange={handleImageChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                                        </div>
                                        <div className="flex-1 text-xs text-gray-500">
                                            <p>Upload a square icon for the category.</p>
                                            <p className="mt-1">Format: JPG, PNG</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="mt-8 flex justify-end gap-3">
                                <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                                    Cancel
                                </button>
                                <button type="submit" className="px-5 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors flex items-center gap-2">
                                    {isEditMode ? "Update" : "Save"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {categoryToDelete && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in" onClick={() => setCategoryToDelete(null)}>
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden text-center p-6 relative animate-in zoom-in-95 duration-200" onClick={(e) => e.stopPropagation()}>
                        <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Trash2 size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Delete Category?</h3>
                        <p className="text-sm text-gray-500 mb-6">Are you sure you want to delete this category? This action cannot be undone.</p>
                        <div className="flex gap-3 justify-center">
                            <button onClick={() => setCategoryToDelete(null)} className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors flex-1">
                                Cancel
                            </button>
                            <button onClick={confirmDelete} className="px-5 py-2.5 text-sm font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors flex-1 shadow-sm">
                                Yes, Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}