import React, { useEffect, useState, useCallback, useRef } from "react";
import { Search, Package, AlertTriangle, Archive, Eye, X, Edit, Upload } from "lucide-react";
import SummaryCard from "../components/SummaryCard";
import { getProductsAPI, updateProductInfoAPI, getCategoriesAPI, assignBrandToProductAPI, fetchStockAPI, searchProductsAPI } from "../services/allAPI";
import { mediaUrl } from "../services/serverUrl";


export default function Products() {
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("All Brands");
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [totalPages, setTotalPages] = useState(1);
    const [summaryStats, setSummaryStats] = useState({
        totalProducts: 0,
        lowStockCount: 0,
        totalWarehouses: 0
    });
    const [productsData, setProductsData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Edit Modal states
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [savingProduct, setSavingProduct] = useState(false);
    const [editFormState, setEditFormState] = useState({
        subheading: "",
        description: "",
        type_label: "",
        image_1: null,
        image_1_preview: null,
        image_2: null,
        image_2_preview: null,
        image_3: null,
        image_3_preview: null,
    });

    const [brands, setBrands] = useState([]);
    const [selectedBrandId, setSelectedBrandId] = useState("");
    const [isBrandDropdownOpen, setIsBrandDropdownOpen] = useState(false);

    const [stockData, setStockData] = useState({});
    const [stockLoading, setStockLoading] = useState(false);

    const fetchStock = async (c_item_code) => {
        if (!c_item_code || c_item_code.length === 0) return;
        setStockLoading(true);
        try {
            const response = await fetchStockAPI({ item_codes: c_item_code.join(",") });
            // Extract stock array depending on whether it's wrapped in stockDetails, data, or is a direct array
            const stockList = response.data?.stockDetails || (Array.isArray(response.data) ? response.data : (response.data?.data || []));

            if (stockList && stockList.length > 0) {
                const stockMap = {};
                stockList.forEach((stockItem) => {
                    const code = stockItem.c_item_code || stockItem.itemCode;
                    stockMap[code] = stockItem;
                });
                setStockData(stockMap);
            }
        } catch (error) {
            console.error("Error fetching stock:", error);
        } finally {
            setStockLoading(false);
        }
    };

    const fetchProducts = async () => {
        setLoading(true);
        try {
            let response;
            if (debouncedSearch) {
                const searchParams = {
                    search: debouncedSearch,
                    limit: 100,
                };
                response = await searchProductsAPI(searchParams);
            } else {
                const params = {
                    page: currentPage
                };
                if (categoryFilter && categoryFilter !== "All Brands") {
                    params.brand = categoryFilter;
                }
                response = await getProductsAPI(params);
            }

            if (response.data && response.data.data) {
                const mappedData = response.data.data.map((item) => {
                    return {
                        id: item.c_item_code,
                        name: item.itemName,
                        shortName: item.itemShortName,
                        erpBrand: item.brandName || item.brand_name,
                        erpCategory: item.categoryName || item.type_label,
                        erpContent: item.contentName,
                        erpPack: item.packName,
                        hsnCode: item.hsnSacCode,
                        hsnName: item.hsnSacName,
                        itemAddedDate: item.itemAddedDate,
                        itemUpdatedDate: item.itemUpdatedDate ? item.itemUpdatedDate.split(' ')[0] : null,
                        category: item.brand_name || "not choose",
                        mrp: item.mrp,
                        stock: item.stockBalQty || 0,
                        lowStock: (item.stockBalQty || 0) < 5,
                        description: item.description,
                        subheading: item.subheading,
                        type_label: item.type_label,
                        brand: item.brand_name,
                        brandId: item.brand_id,
                        brandLogo: item.brand_logo,
                        images: item.images,
                        itemQtyPerBox: item.itemQtyPerBox,
                        cartStatus: item.cart_status,
                        wishlistStatus: item.wishlist_status,
                        batchDetails: item.batchDetails || [],
                        max_disc: item.maxDiscPer,
                        std_disc: item.stdDiscRate,
                    };
                });

                setProductsData(mappedData);

                // Fetch stock for all product item codes
                const c_item_code = mappedData.map((p) => p.id).filter(Boolean);
                fetchStock(c_item_code);

                if (response.data.pagination) {
                    setTotalPages(response.data.pagination.total_pages || 1);
                    setPageSize(response.data.pagination.page_size || 20);
                } else {
                    setTotalPages(1);
                    setPageSize(20);
                }
                if (response.data.summary) {
                    setSummaryStats({
                        totalProducts: response.data.summary.total_products || 0,
                        lowStockCount: response.data.summary.low_stock_count || 0,
                        totalWarehouses: response.data.summary.total_warehouses || 1
                    });
                    console.log(response.data.summary);

                }
            }
        } catch (error) {
            console.error("Error fetching products:", error);
        } finally {
            setLoading(false);
        }
    };
    const fetchBrands = async () => {
        try {
            const response = await getCategoriesAPI();
            if (response.data && response.data.data) {
                setBrands(response.data.data);
            }
        } catch (error) {
            console.error("Error fetching brands:", error);
        }
    };

    // Debounce search term and reset page to 1
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedSearch(search);
            setCurrentPage(1);
        }, 500);

        return () => {
            clearTimeout(handler);
        };
    }, [search]);

    // Fetch brands once on mount
    useEffect(() => {
        fetchBrands();
    }, []);

    // Re-fetch products when pagination/filters change
    useEffect(() => {
        fetchProducts();
    }, [currentPage, debouncedSearch, categoryFilter]);
    const handleUpdateSubmit = async (e) => {
        e.preventDefault();
        setSavingProduct(true);
        try {
            const formData = new FormData();
            formData.append("c_item_code", selectedProduct.id);
            formData.append("subheading", editFormState.subheading);
            formData.append("description", editFormState.description);
            formData.append("type_label", editFormState.type_label);

            if (editFormState.image_1) formData.append("image_1", editFormState.image_1);
            if (editFormState.image_2) formData.append("image_2", editFormState.image_2);
            if (editFormState.image_3) formData.append("image_3", editFormState.image_3);

            const res = await updateProductInfoAPI(formData);

            if (selectedBrandId !== (selectedProduct.brandId || "")) {
                await assignBrandToProductAPI({
                    c_item_code: selectedProduct.id,
                    brand_id: selectedBrandId
                });
            }

            if (res.status === 200) {
                setIsModalOpen(false);
                fetchProducts();
            }
        } catch (error) {
            console.error("Failed to update product:", error);
            let errorMessage = "Failed to update product information.";
            if (error.response?.data) {
                const data = error.response.data;
                if (data.errors) {
                    const firstError = Object.values(data.errors)[0]?.[0];
                    if (firstError) {
                        errorMessage = firstError;
                    }
                } else if (data.message) {
                    errorMessage = data.message;
                }
            }
            alert(errorMessage);
        } finally {
            setSavingProduct(false);
        }
    };

    const handleImageChange = (e, imageKey) => {
        const file = e.target.files[0];
        if (file) {
            const previewUrl = URL.createObjectURL(file);
            setEditFormState(prev => ({
                ...prev,
                [imageKey]: file,
                [`${imageKey}_preview`]: previewUrl
            }));
        }
    };
    // Merge stock data into products
    const paginatedProducts = productsData.map((product) => {
        const stock = stockData[product.id] || {};
        
        // Merge batches from both search API (product.batchDetails) and stock API (stock.batchDetails)
        let batchDetails = [...(product.batchDetails || [])];
        if (stock.batchDetails && stock.batchDetails.length > 0) {
            const batchMap = new Map(batchDetails.map(b => [b.batchNo, b]));
            stock.batchDetails.forEach(b => {
                batchMap.set(b.batchNo, { ...batchMap.get(b.batchNo), ...b });
            });
            batchDetails = Array.from(batchMap.values());
        }

        let totalStock = product.stock;
        let mrp = product.mrp ? `₹${product.mrp}` : null;

        if (batchDetails.length > 0) {
            totalStock = batchDetails.reduce((acc, curr) => acc + (curr.totalBalLsQty || 0), 0);
            if (!mrp && batchDetails[0].mrp) {
                mrp = `₹${batchDetails[0].mrp}`;
            }
        } else if (stock.totalBalLsQty !== undefined) {
            totalStock = stock.totalBalLsQty;
        }

        return {
            ...product,
            stock: totalStock,
            lowStock: totalStock < 5,
            mrp: mrp,
            qtyBox: stock.qtyBox !== undefined ? stock.qtyBox : product.itemQtyPerBox,
            contCode: stock.contCode,
            contName: stock.contName,
            batchDetails: batchDetails,
            packQty: stock.packQty,
            looseQty: stock.looseQty,
            totalBalLsQty: stock.totalBalLsQty,
            stockLastModified: stock.lastModifiedDateTime,
        };
    });

    const handleSearch = (e) => {
        setSearch(e.target.value);
    };

    const handleCategoryChange = (cat) => {
        setCategoryFilter(cat);
        setCurrentPage(1);
        setIsDropdownOpen(false);
    };

    const hasChanges = selectedProduct ? (
        editFormState.subheading !== (selectedProduct.subheading || "") ||
        editFormState.description !== (selectedProduct.description || "") ||
        editFormState.type_label !== (selectedProduct.category || "") ||
        selectedBrandId !== (selectedProduct.brandId || "") ||
        editFormState.image_1 !== null ||
        editFormState.image_2 !== null ||
        editFormState.image_3 !== null
    ) : false;

    const handleOpenViewModal = (product) => {
        setSelectedProduct(product);
        setEditFormState({
            subheading: product.subheading || "",
            description: product.description || "",
            type_label: product.category || "",
            image_1: null,
            image_1_preview: product.images?.[0]?.image || null,
            image_2: null,
            image_2_preview: product.images?.[1]?.image || null,
            image_3: null,
            image_3_preview: product.images?.[2]?.image || null,
        });
        setSelectedBrandId(product.brandId || "");
        setIsModalOpen(true);
    };

    return (
        <div className="min-h-full flex flex-col ml-2 mt-3 mb-8">

            <div className="mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4 ">
                <div>
                    <h1 className="text-2xl sm:text-2xl md:text-2xl font-semibold text-[#505050]">
                        Product & Inventory View
                    </h1>
                    <p className="text-sm sm:text-base text-[#505050] mt-1">
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
                        className="flex-1 bg-transparent border-none outline-none px-3 text-base text-[#505050] placeholder:text-[#9EA2A7]"
                    />

                    {/* Custom Dropdown */}
                    <div className="relative border border-gray-100 rounded-lg bg-white">
                        <button
                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                            className="flex items-center gap-2 px-4 py-1.5 text-[#505050] text-base font-medium hover:bg-gray-50 rounded-lg transition-colors whitespace-nowrap min-w-[140px] justify-between"
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
                                    <button
                                        onClick={() => handleCategoryChange("All Brands")}
                                        className={`w-full text-left px-4 py-2.5 text-base transition-colors hover:bg-[#EEF1F5] ${categoryFilter === "All Brands" ? 'bg-[#EEF1F5] text-[#000000] font-semibold' : 'text-[#505050]'
                                            }`}
                                    >
                                        All Brands
                                    </button>
                                    {brands.map((brand) => (
                                        <button
                                            key={brand.id}
                                            onClick={() => handleCategoryChange(brand.name)}
                                            className={`w-full text-left px-4 py-2.5 text-base transition-colors hover:bg-[#EEF1F5] ${categoryFilter === brand.name ? 'bg-[#EEF1F5] text-[#000000] font-semibold' : 'text-[#505050]'
                                                }`}
                                        >
                                            {brand.name}
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
                    value={summaryStats.totalProducts.toString()}
                    icon={<Package size={20} />}
                    bgClass="bg-[#f2ecbb]"
                    textClass="text-[#846018]"
                    iconClass=""
                    blobColor1="bg-[#D08700]"
                    blobColor2="bg-[#733E0A]"
                />
                <SummaryCard
                    title="Low Stock Items"
                    value={summaryStats.lowStockCount.toString()}
                    icon={<AlertTriangle size={20} />}
                    bgClass="bg-[#d8e9ff]"
                    textClass="text-[#1D4ED8]"
                    iconClass="text-blue-600"
                    blobColor1="bg-[#83ACE5]"
                    blobColor2="bg-[#1447EA]"
                />
                <SummaryCard
                    title="Total Warehouses"
                    value={summaryStats.totalWarehouses.toString()}
                    icon={<Archive size={20} />}
                    bgClass="bg-[#e9fedf]"
                    textClass="text-[#207238]"
                    iconClass=""
                    blobColor1="bg-[#A3FF63]"
                    blobColor2="bg-[#33CB6C]"
                />
            </div>

            {/* Table */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 flex-1 flex flex-col">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-[#DCE4EA] text-gray-500 text-sm uppercase font-bold tracking-wider sticky top-0 z-10">
                            <tr>
                                <th className="px-2 py-4 text-center whitespace-nowrap">SI NO</th>
                                <th className="whitespace-nowrap">PRODUCT ID</th>
                                <th className="px-4 min-w-[200px]">PRODUCT NAME</th>
                                <th className="px-2 whitespace-nowrap">BRAND NAME</th>
                                <th className="px-2 whitespace-nowrap">HSN CODE</th>
                                <th className="px-2 whitespace-nowrap">PACK</th>
                                <th className="px-2 whitespace-nowrap">ADDED DATE</th>
                                <th className="px-2 whitespace-nowrap">UPDATED DATE</th>
                                <th className="px-2 text-center whitespace-nowrap">STATUS</th>
                                <th className="px-2 text-center whitespace-nowrap">ACTION</th>
                            </tr>
                        </thead>
                        <tbody className="text-base text-gray-700 divide-y divide-gray-50">
                            {loading ? (
                                <tr>
                                    <td colSpan={10} className="px-6 py-10 text-center text-gray-400">
                                        <div className="flex items-center justify-center gap-2">
                                            <div className="w-5 h-5 border-2 border-[#505050] border-t-transparent rounded-full animate-spin" />
                                            Loading products...
                                        </div>
                                    </td>
                                </tr>
                            ) : paginatedProducts.length === 0 ? (
                                <tr>
                                    <td colSpan={10} className="px-6 py-10 text-center text-gray-400">
                                        No products found.
                                    </td>
                                </tr>
                            ) : (
                                paginatedProducts.map((product, index) => (
                                    <tr
                                        key={index}
                                        className={`${index % 2 === 0 ? "bg-white" : "bg-[#F4F6F8]"} hover:bg-[#EEF2F6] transition`}
                                    >
                                        <td className="px-3 py-2 text-sm font-bold text-gray-800 text-center">{(currentPage - 1) * pageSize + index + 1}</td>
                                        <td 
                                            className="px-2 text-base text-[#127690] font-bold cursor-pointer hover:underline transition-colors"
                                            onClick={() => handleOpenViewModal(product)}
                                        >
                                            {product.id}
                                        </td>
                                        <td 
                                            className="px-3 text-base text-gray-800 font-medium cursor-pointer hover:text-[#127690] hover:underline transition-colors"
                                            onClick={() => handleOpenViewModal(product)}
                                        >
                                            {product.name}
                                        </td>
                                        <td className="px-2 text-base text-gray-800">{product.category || "-"}</td>
                                        <td className="px-2 py-4 text-base text-gray-800">{product.hsnCode || "-"}</td>
                                        <td className="px-2 py-4 text-base text-gray-800">{product.erpPack || "-"}</td>
                                        <td className="px-2 py-4 text-base text-gray-600 font-bold whitespace-nowrap">{product.itemAddedDate || "-"}</td>
                                        <td className="px-2 py-4 text-base whitespace-nowrap">
                                            <span className="text-gray-600 font-semibold">{product.itemUpdatedDate || "-"}</span>
                                        </td>
                                        <td className="px-2 py-4 text-center whitespace-nowrap">
                                            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full whitespace-nowrap inline-block ${product.lowStock ? "bg-red-100 text-red-600" : "bg-green-100 text-green-800"}`}>
                                                {product.lowStock ? "Low Stock" : "Sufficient"}
                                            </span>
                                        </td>
                                        <td className="px-2 text-base text-center">
                                            <button
                                                onClick={() => handleOpenViewModal(product)}
                                                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors text-[#127690]"
                                                title="View / Edit Details"
                                            >
                                                <Eye size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination UI - Numbered Design */}
                {totalPages > 1 && (
                    <div className="mt-4 mb-4 flex items-center justify-end px-6 border-t border-gray-50 pt-4">
                        <div className="flex gap-1.5">
                            <button
                                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                disabled={currentPage === 1}
                                className="p-2 rounded-xl border border-gray-200 text-gray-400 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="rotate-90"><path d="m6 9 6 6 6-6" /></svg>
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
                                            onClick={() => setCurrentPage(pageNum)}
                                            className={`w-9 h-9 rounded-xl font-bold text-sm transition-all ${currentPage === pageNum
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
                                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                                disabled={currentPage === totalPages}
                                className="p-2 rounded-xl border border-gray-200 text-gray-400 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="-rotate-90"><path d="m6 9 6 6 6-6" /></svg>
                            </button>
                        </div>
                    </div>
                )}
            </div>
            {/* Product Details Modal */}
            {isModalOpen && selectedProduct && (
                <div
                    className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm overflow-y-auto py-6"
                    onClick={() => setIsModalOpen(false)}
                >
                    <div
                        className="bg-white rounded-2xl shadow-2xl w-full max-w-7xl mx-4 lg:m-auto relative"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Modal Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                            <div>
                                <h2 className="text-xl font-semibold text-gray-800">{selectedProduct.name}</h2>
                                <p className="text-sm text-gray-400 mt-0.5">Product ID: {selectedProduct.id}</p>
                            </div>
                            <div className="flex items-center gap-3">
                                {selectedProduct.lowStock && (
                                    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-600">
                                        <AlertTriangle size={12} /> Low Stock
                                    </span>
                                )}
                                <button
                                    onClick={() => setIsModalOpen(false)}
                                    className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                                >
                                    <X size={20} />
                                </button>
                            </div>
                        </div>

                        {/* Modal Body — 3-column no-scroll layout */}
                        <div className="max-h-[80vh] overflow-y-auto lg:max-h-none lg:overflow-visible text-gray-800">
                            <div className="grid grid-cols-1 md:grid-cols-3">

                                {/* COL 1: Images + Brand + Description */}
                                <div className="flex flex-col gap-3 p-4 border-r border-gray-100">
                                    {/* Images */}
                                    <div>
                                        <p className="text-sm font-bold text-[#127690] uppercase tracking-widest mb-2">
                                            Product Images
                                            <span className="block text-xs text-gray-600 normal-case tracking-normal mt-0.5 font-medium">Format: JPG, PNG, WEBP (Max 5MB)</span>
                                        </p>

                                        <div className="flex flex-wrap lg:flex-nowrap gap-3">
                                            {[1, 2, 3].map((num) => {
                                                const previewKey = `image_${num}_preview`;
                                                const fileKey = `image_${num}`;
                                                const hasImage = editFormState[previewKey];

                                                return (
                                                    <div
                                                        key={num}
                                                        className="relative group w-34  h-34 sm:w-34 sm:h-30 md:w-28 md:h-28 lg:w-30 lg:h-40 aspect-square shrink-0"
                                                    >
                                                        <div
                                                            className={`w-full h-full rounded-xl border flex items-center justify-center overflow-hidden transition-all 
            ${hasImage
                                                                    ? "border-transparent bg-gray-100"
                                                                    : "border-dashed border-gray-300 hover:border-[#127690] hover:bg-teal-50"
                                                                }`}
                                                        >
                                                            {hasImage ? (
                                                                <img
                                                                    src={hasImage && typeof hasImage === 'string' && (hasImage.startsWith('http') || hasImage.startsWith('blob:')) ? hasImage : `${mediaUrl}${hasImage}`}
                                                                    className="w-full h-full object-cover"
                                                                />
                                                            ) : (
                                                                <Upload
                                                                    size={14}
                                                                    className="text-gray-400 group-hover:text-[#127690]"
                                                                />
                                                            )}

                                                            <input
                                                                type="file"
                                                                accept=".jpg,.jpeg,.png,.gif,.webp"
                                                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                                                onChange={(e) => handleImageChange(e, fileKey)}
                                                            />
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* Description */}
                                    <div className="bg-gray-50 rounded-xl p-3 flex-1 flex flex-col">
                                        <label className="text-sm font-bold text-[#127690] uppercase tracking-widest mb-1.5 cursor-pointer">Description</label>
                                        <textarea
                                            value={editFormState.description}
                                            onChange={(e) => setEditFormState({ ...editFormState, description: e.target.value })}
                                            className="w-full flex-1 min-h-[80px] px-3 py-2 bg-white border border-gray-200 rounded-lg text-base focus:outline-none focus:ring-1 focus:ring-[#127690] focus:border-[#127690] transition-all placeholder:text-gray-800 resize-none"
                                            placeholder="Add product description..."
                                        />
                                    </div>
                                </div>

                                {/* COL 2: Product Info + Batch & Expiry */}
                                <div className="flex flex-col gap-3 p-4 border-r border-gray-100">
                                    {/* Product Info */}
                                    <div className="space-y-2">
                                        <p className="text-sm font-bold text-[#127690] uppercase tracking-widest">Product Info</p>
                                        <ModalRow label="Product Code" value={selectedProduct.id} />
                                        <ModalRow label="Product Name" value={selectedProduct.name} />
                                        <ModalRow label="Short Name" value={selectedProduct.shortName} />
                                        <ModalRow label="ERP Brand" value={selectedProduct.erpBrand} />
                                        <ModalRow label="ERP Category" value={selectedProduct.erpCategory} />
                                        {/* <ModalRow label="Content" value={selectedProduct.erpContent} />
                                        <ModalRow label="Pack" value={selectedProduct.erpPack} /> */}
                                        <ModalRow label="HSN Code" value={selectedProduct.hsnCode} />
                                        <ModalRow label="HSN Name" value={selectedProduct.hsnName} />
                                        {/* <div className="flex flex-col sm:flex-row sm:items-start gap-1">
                                            <span className="text-sm font-semibold text-gray-400 uppercase tracking-wide w-40 shrink-0 mt-1.5">Category</span>
                                            <input type="text" value={editFormState.type_label} onChange={e => setEditFormState({ ...editFormState, type_label: e.target.value })} className="flex-1 text-base bg-gray-50 rounded px-2 py-1 border border-gray-200 focus:outline-none focus:border-[#127690] hover:bg-gray-100 transition-colors" placeholder="Category" />
                                        </div> */}
                                        <div className="flex flex-col sm:flex-row sm:items-start gap-1">
                                            <span className="text-sm font-semibold uppercase tracking-wide w-40 shrink-0 mt-1.5">Subheading</span>
                                            <input type="text" value={editFormState.subheading} onChange={e => setEditFormState({ ...editFormState, subheading: e.target.value })} className="flex-1 text-base bg-gray-50  text-[#020202] rounded px-2 py-1 border border-gray-200 focus:outline-none focus:border-[#127690] hover:bg-gray-100 transition-colors" placeholder="Subheading" />
                                        </div>
                                    </div>

                                    {/* Brand Selection */}
                                    <div className="bg-gray-50 rounded-xl p-3 space-y-2">
                                        <p className="text-sm font-bold text-[#127690] uppercase tracking-widest">Category</p>
                                        <div className="relative">
                                            <button
                                                type="button"
                                                onClick={() => setIsBrandDropdownOpen(!isBrandDropdownOpen)}
                                                className="w-full flex items-center gap-2 p-2 bg-white border border-gray-200 rounded-lg hover:border-[#127690] transition-colors text-left"
                                            >
                                                {brands.find(b => b.id === selectedBrandId) ? (
                                                    <div className="flex items-center gap-2 flex-1">
                                                        {brands.find(b => b.id === selectedBrandId).logo ? (
                                                            <img src={brands.find(b => b.id === selectedBrandId).logo} alt="" className="w-8 h-8 rounded-lg object-contain border border-gray-100 p-0.5" />
                                                        ) : (
                                                            <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                                                                <Archive size={14} className="text-gray-400" />
                                                            </div>
                                                        )}
                                                        <div>
                                                            <p className="text-base font-semibold">{brands.find(b => b.id === selectedBrandId)?.name || "Unknown Brand"}</p>
                                                            <p className="text-xs text-gray-500 font-medium">Brand ID: {selectedBrandId}</p>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="flex items-center gap-2 flex-1 py-1">
                                                        <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                                                            <Archive size={14} className="text-gray-400" />
                                                        </div>
                                                        <span className="text-base text-gray-400 font-medium">Select category</span>
                                                    </div>
                                                )}
                                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                                                    className={`text-gray-400 transition-transform ${isBrandDropdownOpen ? 'rotate-180' : ''}`}
                                                >
                                                    <path d="m6 9 6 6 6-6" />
                                                </svg>
                                            </button>

                                            {isBrandDropdownOpen && (
                                                <>
                                                    <div className="fixed inset-0 z-40" onClick={() => setIsBrandDropdownOpen(false)} />
                                                    <div className="absolute bottom-full left-0 mb-2 w-51 max-h-60 overflow-y-auto bg-white border border-gray-100 rounded-xl shadow-xl z-50 py-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
                                                        <div className="px-3 pb-2 border-b border-gray-50 mb-1">
                                                            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Select a Brand</p>
                                                        </div>
                                                        {/* <button
                                                            onClick={() => { setSelectedBrandId(""); setIsBrandDropdownOpen(false); }}
                                                            className="w-full text-left px-4 py-2 text-base hover:bg-gray-50 text-gray-500 italic"
                                                        >
                                                            No Brand
                                                        </button> */}
                                                        {brands.map((brand) => (
                                                            <button
                                                                key={brand.id}
                                                                onClick={() => {
                                                                    setSelectedBrandId(brand.id);
                                                                    setIsBrandDropdownOpen(false);
                                                                }}
                                                                className={`w-full text-left flex items-center px-4 py-2 text-base transition-colors hover:bg-blue-50 ${selectedBrandId === brand.id ? 'bg-blue-50 text-blue-700 font-semibold border-r-4 border-blue-600' : 'text-gray-700'}`}
                                                            >
                                                                {/* {brand.logo ? (
                                                                    <img src={brand.logo} alt="" className="w-8 h-8 rounded-lg object-contain border border-gray-100 bg-white p-0.5" />
                                                                ) :null} */}
                                                                <div className="flex-1 text-left">
                                                                    <p className="text-base font-medium">{brand.name}</p>
                                                                    <p className="text-xs text-gray-400">ID: {brand.id}</p>
                                                                </div>
                                                            </button>
                                                        ))}
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    </div>

                                    {/* Batch & Expiry */}
                                    {selectedProduct.batchDetails && selectedProduct.batchDetails.length > 0 ? (
                                        <div className="bg-gray-50 rounded-xl p-3 space-y-3 max-h-[300px] overflow-y-auto">
                                            <p className="text-sm font-bold text-[#127690] uppercase tracking-widest sticky top-0 bg-gray-50 z-10 pb-1">Batch Details</p>
                                            {selectedProduct.batchDetails.map((batch, idx) => (
                                                <div key={idx} className="border border-gray-200 rounded-lg p-2 space-y-2 bg-white">
                                                    <div className="flex justify-between items-center border-b border-gray-100 pb-1 mb-1">
                                                        <span className="text-sm font-bold text-gray-800">Batch: {batch.batchNo}</span>
                                                        <span className="text-xs text-gray-500 font-semibold">Exp: {batch.expiryDate ? batch.expiryDate.split(' ')[0] : 'N/A'}</span>
                                                    </div>
                                                    <ModalRow label="MRP" value={batch.mrp} />
                                                    <ModalRow label="MRP Box" value={batch.mrpBox} />
                                                    <ModalRow label="Total Bal Qty" value={batch.totalBalLsQty} />
                                                    <ModalRow label="Pack Qty" value={batch.packQty} />
                                                    <ModalRow label="Loose Qty" value={batch.looseQty} />
                                                    <ModalRow label="Last Modified" value={batch.lastModifiedDateTime ? batch.lastModifiedDateTime.split(' ')[0] : '-'} />
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="bg-gray-50 rounded-xl p-3 space-y-2">
                                            <p className="text-sm font-bold text-[#127690] uppercase tracking-widest">Batch & Expiry</p>
                                            <ModalRow label="Batch Number" value={selectedProduct.batch} />
                                            <ModalRow label="Expiry Date" value={selectedProduct.expiry} />
                                        </div>
                                    )}
                                </div>

                                {/* COL 3: Pricing + Inventory + Status */}
                                <div className="flex flex-col gap-3 p-4">
                                    {/* Pricing */}
                                    <div className="bg-gray-50 rounded-xl p-3 space-y-2">
                                        <p className="text-sm font-bold text-[#127690] uppercase tracking-widest">Pricing</p>
                                        <ModalRow label="MRP" value={selectedProduct.mrp} />
                                        <ModalRow label="Max Discount" value={selectedProduct.max_disc != null ? `${selectedProduct.max_disc}%` : null} />
                                        <ModalRow label="Standard Discount" value={selectedProduct.std_disc != null ? `${selectedProduct.std_disc}%` : null} />
                                    </div>

                                    {/* Stock Details */}
                                    <div className="bg-gray-50 rounded-xl p-3 space-y-2">
                                        <p className="text-sm font-bold text-[#127690] uppercase tracking-widest">Item Stock Info</p>
                                        <ModalRow label="Qty Per Box" value={selectedProduct.qtyBox} />
                                        <ModalRow label="Content Code" value={selectedProduct.contCode} />
                                        <ModalRow label="Content Name" value={selectedProduct.contName} />
                                        {(!selectedProduct.batchDetails || selectedProduct.batchDetails.length === 0) && (
                                            <>
                                                <ModalRow label="Total Balance Qty" value={selectedProduct.totalBalLsQty} />
                                                <ModalRow label="Pack Qty" value={selectedProduct.packQty} />
                                                <ModalRow label="Loose Qty" value={selectedProduct.looseQty} />
                                                <ModalRow label="Last Modified" value={selectedProduct.stockLastModified} />
                                            </>
                                        )}
                                    </div>

                                    {/* Status */}
                                    <div className="bg-gray-50 rounded-xl p-3 space-y-2">
                                        <p className="text-sm font-bold text-[#127690] uppercase tracking-widest">Status</p>
                                        {/* <div className="flex items-center gap-2">
                                            <span className="text-xs font-semibold uppercase tracking-wide w-28 shrink-0">Cart Status</span>
                                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${selectedProduct.cartStatus ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-800"}`}>
                                                {selectedProduct.cartStatus ? "In Cart" : "Not In Cart"}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-semibold uppercase tracking-wide w-28 shrink-0">Wishlist</span>
                                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${selectedProduct.wishlistStatus ? "bg-pink-100 text-pink-700" : "bg-gray-200 text-gray-800"}`}>
                                                {selectedProduct.wishlistStatus ? "Wishlisted" : "Not Wishlisted"}
                                            </span>
                                        </div> */}
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-semibold uppercase tracking-wide w-28 shrink-0"> Stock</span>
                                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${selectedProduct.lowStock ? "bg-red-100 text-red-600" : "bg-green-100 text-green-800"}`}>
                                                {selectedProduct.lowStock ? "Low Stock" : "Sufficient"}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>{/* end scroll wrapper */}

                        {/* Modal Footer */}
                        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-3 bg-gray-50/50 rounded-b-2xl">
                            <button
                                onClick={() => setIsModalOpen(false)}
                                className="px-5 py-2 text-base font-medium bg-white border border-gray-200 hover:bg-gray-50 text-gray-600 rounded-lg transition-colors shadow-sm"
                                disabled={savingProduct}
                            >
                                Close
                            </button>
                            {hasChanges && (
                                <button
                                    onClick={handleUpdateSubmit}
                                    disabled={savingProduct}
                                    className="px-6 py-2 text-base font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all shadow-sm shadow-blue-600/20 flex items-center gap-2 disabled:bg-blue-400"
                                >
                                    {savingProduct && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                                    {savingProduct ? 'Saving...' : 'Save Changes'}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}


        </div>
    );
}

// Helper Component for Modal Detail Rows (matches Retailer modal style)
function ModalRow({ label, value }) {
    const isMissing = value === undefined || value === null || value === "" || value === "-";
    return (
        <div className="flex flex-col sm:flex-row sm:items-start gap-1">
            <span className="text-sm font-semibold uppercase tracking-wide w-40 shrink-0">
                {label}
            </span>
            <span className={`text-base font-medium break-all ${isMissing ? 'text-orange-500 italic text-sm py-0.5' : 'text-gray-900'}`}>
                {isMissing ? "Not provided by backend" : value}
            </span>
        </div>
    );
}
