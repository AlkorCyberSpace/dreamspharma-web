# DreamsPharma — Complete API & Database Documentation

**Base URL:** `http://<server>:8000/api/`  
**Auth:** JWT Bearer Token (unless marked Public)  
**Header:** `Authorization: Bearer <access_token>`

---

## TABLE OF CONTENTS

1. [Authentication](#1-authentication)
2. [Profile & KYC](#2-profile--kyc)
3. [Store & Location](#3-store--location)
4. [ERP / Products](#4-erp--products)
5. [Cart](#5-cart)
6. [Wishlist](#6-wishlist)
7. [Address](#7-address)
8. [Orders & Checkout](#8-orders--checkout)
9. [Payment (Razorpay + COD)](#9-payment)
10. [Recommendations](#10-recommendations)
11. [Notifications](#11-notifications)
12. [Credit Notes](#12-credit-notes)
13. [Wallet](#13-wallet)
14. [SuperAdmin APIs](#14-superadmin-apis)
15. [Database Models](#15-database-models)
16. [Location Flow Diagram](#16-location-based-flow)
17. [Error Codes](#17-error-codes)

---

## 1. AUTHENTICATION

### 1.1 SuperAdmin Login
`POST /api/auth/login/` — Public

```json
// Request
{ "username": "admin_or_email", "password": "password123" }

// Response 200
{ "message": "Login successful", "access": "jwt_token", "refresh": "jwt_token" }
```

### 1.2 Retailer Login (Step 1)
`POST /api/retailer-auth/login/` — Public

```json
// Request
{ "email": "retailer@example.com", "password": "password123" }

// Response 200 — OTP sent to email
{
  "message": "Email and password verified. OTP sent to your email.",
  "email": "retailer@example.com", "otp_expires_in": 60,
  "user": { "id": 1, "username": "retailer1", "email": "...", "phone_number": "..." }
}
```

### 1.3 Verify OTP (Step 2)
`POST /api/retailer-auth/verify-otp/` — Public

```json
// Request
{ "email": "retailer@example.com", "otp": "1234" }

// Response 200
{ "message": "Login successful", "access": "jwt_token", "refresh": "jwt_token",
  "user": { "id": 1, "username": "...", "role": "RETAILER", "status": "APPROVED" } }
```

### 1.4 Resend OTP
`POST /api/retailer-auth/resend-otp/` — Public  
Request: `{ "email": "retailer@example.com" }`

### 1.5 Token Refresh
`POST /api/retailer-auth/token/refresh/` — Public  
Request: `{ "refresh": "jwt_refresh_token" }`  
Response: `{ "access": "new_access_token" }`

### 1.6 Register
`POST /api/auth/register/` — Public

```json
// Request
{ "username": "newuser", "email": "new@example.com", "password": "pass123", "phone_number": "9876543210" }

// Response 201
{ "message": "Registration successful! 4-digit OTP sent to your email.", "otp_expires_in": 60,
  "user": { "id": 2, "username": "newuser", "email": "...", "phone_number": "..." } }
```

### 1.7 OTP Request / Verify
- `POST /api/otp/request_otp/` — `{ "email": "..." }`
- `POST /api/otp/verify_otp/` — `{ "email": "...", "otp": "1234" }`

### 1.8 Forgot / Reset Password
- `POST /api/auth/forgot-password/` — `{ "email": "..." }`
- `POST /api/auth/verify-reset-otp/` — `{ "email": "...", "otp": "1234" }`
- `POST /api/auth/reset-password/` — `{ "email": "...", "new_password": "..." }`

### 1.9 Change Password
- `PUT /api/auth/change-password/<user_id>/` — JWT — `{ "old_password": "...", "new_password": "..." }`
- `PUT /api/auth/superadmin-change-password/` — JWT (SuperAdmin)

### 1.10 Logout
`POST /api/auth/logout/` — JWT — `{ "refresh": "jwt_refresh_token" }`

---

## 2. PROFILE & KYC

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/profile/` | GET/PUT | JWT | Get/update own profile |
| `/api/profile/<user_id>/` | GET | JWT | Get profile by ID |
| `/api/kyc/submit/<user_id>/` | POST | JWT | Submit KYC (multipart: shop_name, gst_number, drug_license, id_proof, store_photo) |
| `/api/kyc/status/` | GET | JWT | Check KYC status |

---

## 3. STORE & LOCATION

### 3.1 List Stores
`GET /api/stores/` — Public

### 3.2 Find Nearest Store
`POST /api/stores/find-nearest/` — Public

```json
// Request (GPS)
{ "latitude": 12.93, "longitude": 77.62 }
// OR (Pincode)
{ "pincode": "560038" }

// Response 200
{ "success": true, "store": {
    "store_id": 2, "store_name": "DreamsPharma - Koramangala",
    "distance": 0.76, "c2_code": "03C001", "erp_store_id": "002"
}}
```

### 3.3 Find Nearby Stores
`POST /api/stores/find-nearby/` — Public  
Request: `{ "latitude": 12.93, "longitude": 77.62, "radius": 15 }`

### 3.4 Store Details / ERP Config
- `GET /api/stores/<store_id>/details/` — Public
- `GET /api/stores/<store_id>/erp-config/` — JWT (SuperAdmin)

---

## 4. ERP / PRODUCTS

### 4.1 Get Products (Item Master) — Paginated
`GET /api/erp/ws_c2_services_get_master_data` — Public

**Query Params:** `page`, `pageSize`, `userId`, `storeId`, `latitude`, `longitude`

```json
// Response 200
{
  "code": "200", "data": [
    { "c_item_code": "IT001", "itemName": "Paracetamol 500mg", "mrp": 25.50,
      "std_disc": 10.0, "stockBalQty": 100, "expiryDate": "2027-06-15",
      "subheading": "Pain Relief", "images": [], "cart_status": false, "wishlist_status": false }
  ],
  "pagination": { "page": 1, "pageSize": 10, "totalItems": 28, "totalPages": 3 }
}
```

### 4.2 Other Product Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/erp/ws_c2_services_fetch_stock` | GET | Real-time stock from ERP (?storeId=001) |
| `/api/products/` | GET | All products (?search=para&limit=50) |
| `/api/search/<user_id>/` | GET | Search products (?q=paracetamol) |
| `/api/search/popular/` | GET | Popular search terms |
| `/api/search/log/` | POST | Log search query |
| `/api/categories/` | GET | List all categories/brands |
| `/api/products/<product_id>/related/<user_id>/` | GET | Related products |
| `/api/erp/update_product_info/` | POST | Update product info (SuperAdmin, multipart) |
| `/api/erp/upload_product_image/` | POST | Upload product image (SuperAdmin, multipart) |

---

## 5. CART

### 5.1 Get Cart
`GET /api/cart/<user_id>/` — Public

```json
// Response 200
{ "success": true, "data": {
    "id": 1, "items": [
      { "id": 1, "itemCode": "IT001", "itemName": "Paracetamol 500mg",
        "mrp": 25.50, "quantity": 2, "discountPercentage": 10.0,
        "discountedPrice": 22.95, "itemTotalMrp": 51.0,
        "itemTotalDiscounted": 45.90, "itemSavings": 5.10 }
    ],
    "bagTotal": 51.0, "bagSavings": 5.10, "subtotal": 45.90,
    "convenienceFee": 0.0, "deliveryFee": 0.0, "platformFee": 29.0,
    "grandTotal": 74.90, "itemCount": 1
}}
```

### 5.2 Add to Cart
`POST /api/cart/add/<user_id>/` — Public

```json
// Request
{ "itemCode": "IT001", "quantity": 2, "batchNo": "B001", "storeId": "001" }

// Response 201
{ "success": true, "message": "Paracetamol 500mg added to cart",
  "data": { "id": 1, "itemCode": "IT001", "mrp": 25.50, "quantity": 2,
    "availability": "In Stock", "available_qty": 100, "in_stock": true }}
```

### 5.3 Update / Delete Cart Item
`PUT/DELETE /api/cart/item/<item_id>/?userId=<user_id>` — Public  
PUT body: `{ "quantity": 3 }`

---

## 6. WISHLIST

| Endpoint | Method | Body |
|----------|--------|------|
| `/api/wishlist/<user_id>/` | GET | — |
| `/api/wishlist/add/<user_id>/` | POST | `{ "itemCode": "IT001", "storeId": "001" }` |
| `/api/wishlist/item/<item_id>/` | DELETE | — |
| `/api/wishlist/item/<item_id>/update/` | PUT | `{ "quantity": 2 }` |
| `/api/wishlist/move-to-cart/` | POST | `{ "itemCode": "IT001", "quantity": 1 }` |

---

## 7. ADDRESS

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/address/<user_id>/` | GET | List addresses |
| `/api/address/create/<user_id>/` | POST | Create address |
| `/api/address/<user_id>/<address_id>/` | PUT | Update address |
| `/api/address/<user_id>/<address_id>/delete/` | DELETE | Delete address |
| `/api/address/<user_id>/<address_id>/default/` | PUT | Set as default |

**Create Address Body:**
```json
{ "name": "John", "phone": "9876543210", "pincode": "560038",
  "city": "Bangalore", "state": "Karnataka", "locality": "Indiranagar",
  "flat_building": "Apt 101", "landmark": "Near Metro",
  "address_type": "HOME", "is_default": true,
  "latitude": 12.97, "longitude": 77.64 }
```

---

## 8. ORDERS & CHECKOUT

### 8.1 Checkout Preview
`POST /api/checkout/preview/<user_id>/` — `{ "address_id": 1 }`

### 8.2 Create Sales Order
`POST /api/erp/ws_c2_services_create_sale_order` — Public

```json
{ "storeId": "001", "paymentMode": "COD",
  "mobileNo": "9876543210", "patientName": "John",
  "orderTotal": 74.90, "use_wallet": false,
  "materialInfo": [
    { "item_code": "IT001", "item_name": "Paracetamol",
      "total_loose_qty": 2, "sale_rate": 22.95, "disc_per": 10.0 }
  ] }
```

### 8.3 Other Order Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/checkout/address/` | POST | Checkout with address |
| `/api/erp/ws_c2_services_get_orderstatus?orderId=ORD-xxx` | GET | Order status |
| `/api/orders/<user_id>/?status=all\|active\|completed` | GET | Retailer orders |
| `/api/orders/<order_id>/invoice/` | GET | Download invoice PDF |

---

## 9. PAYMENT

### 9.1 Razorpay Flow

| Step | Endpoint | Body |
|------|----------|------|
| 1. Initiate | `POST /api/payment/initiate/<user_id>/` | `{ "order_id": "ORD-xxx" }` |
| 2. Verify | `POST /api/payment/verify/<user_id>/` | `{ "payment_id": "uuid", "razorpay_order_id": "...", "razorpay_payment_id": "...", "razorpay_signature": "..." }` |
| 3. Status | `GET /api/payment/status/<user_id>/` | — |
| 4. Refund | `POST /api/payment/refund/<user_id>/` | `{ "payment_id": "uuid", "amount": 50.0, "reason": "..." }` |

### 9.2 COD Flow

| Step | Endpoint | Body |
|------|----------|------|
| 1. Initiate | `POST /api/payment/cod/initiate/<user_id>/` | `{ "order_id": "ORD-xxx" }` |
| 2. Confirm | `POST /api/payment/cod/confirm/<user_id>/` | `{ "payment_id": "uuid", "collected_by": "Agent" }` |

### 9.3 Webhook
`POST /api/payment/webhook/` — Razorpay signature verified

---

## 10. RECOMMENDATIONS

| Endpoint | Description |
|----------|-------------|
| `GET /api/recommendations/for-you/<user_id>/` | Personalized |
| `GET /api/recommendations/frequently-bought/<user_id>/` | Frequently bought together |
| `GET /api/recommendations/top-selling/` | Top selling |
| `GET /api/recommendations/popular/` | Popular products |
| `GET /api/recommendations/recently-viewed/<user_id>/` | Recently viewed |
| `GET /api/recommendations/user-activity/<user_id>/` | User activity |

---

## 11. NOTIFICATIONS

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notifications/register/<user_id>/` | POST | Register FCM token: `{ "token": "...", "device_type": "android" }` |
| `/api/retailer-notifications/` | GET | List notifications (JWT) |
| `/api/retailer-notifications/<id>/` | GET | Detail |
| `/api/retailer-notifications/count/` | GET | Unread count |

---

## 12. CREDIT NOTES

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/credit-notes/order-products/<user_id>/?order_id=ORD-xxx` | GET | Products for return |
| `/api/credit-notes/create/<user_id>/` | POST | Create credit note |
| `/api/credit-notes/<user_id>/` | GET | List my credit notes |
| `/api/admin/credit-notes/` | GET | Admin: list all |
| `/api/admin/credit-notes/<id>/` | GET | Admin: detail |
| `/api/admin/credit-notes/<id>/approve/` | POST | Admin: approve |
| `/api/admin/credit-notes/<id>/reject/` | POST | Admin: reject |

---

## 13. WALLET

`GET /api/wallet/<user_id>/` — Get wallet balance & transactions.  
Wallet applied during order creation via `"use_wallet": true` in CreateSalesOrder.

---

## 14. SUPERADMIN APIs

All require JWT with `role=SUPERADMIN`.

### Dashboard & Profile

| Endpoint | Method |
|----------|--------|
| `/api/superadmin/dashboard/statistics/` | GET |
| `/api/superadmin/dashboard/daily-volume/` | GET |
| `/api/superadmin/profile/` | GET |
| `/api/superadmin/profile/image/` | POST/DELETE |
| `/api/superadmin/change-password/` | POST |
| `/api/superadmin/logout/` | POST |

### Retailers & KYC

| Endpoint | Method |
|----------|--------|
| `/api/superadmin/retailers/` | GET |
| `/api/superadmin/kyc/approve/<user_id>/` | POST |
| `/api/superadmin/kyc/reject/<user_id>/` | POST |

### Orders

| Endpoint | Method |
|----------|--------|
| `/api/superadmin/orders/` | GET |
| `/api/superadmin/orders/update-status/` | POST |
| `/api/superadmin/orders/cod-delivered/` | POST |

### Categories & Offers

| Endpoint | Method |
|----------|--------|
| `/api/superadmin/add-category/` | GET/POST |
| `/api/superadmin/add-category/<id>/` | PUT/DELETE |
| `/api/superadmin/assign-brand/` | POST |
| `/api/offers/` | GET/POST |
| `/api/offers/<offer_id>/` | GET/PUT/DELETE |
| `/api/offers/homepage/` | GET (Public) |
| `/api/offers/category/<category_id>/` | GET (Public) |

### Audit, Notifications, Reports

| Endpoint | Method |
|----------|--------|
| `/api/superadmin/audit-logs/` | GET |
| `/api/superadmin/notifications/` | GET |
| `/api/superadmin/notifications/<id>/mark-read/` | POST |
| `/api/superadmin/reports/summary/` | GET |
| `/api/superadmin/reports/kyc/?format=json\|excel` | GET |
| `/api/superadmin/reports/orders/?format=json\|excel` | GET |
| `/api/superadmin/reports/retailer-activity/` | GET |
| `/api/superadmin/reports/revenue/` | GET |
| `/api/superadmin/reports/refund-trends/` | GET |

---

## 15. DATABASE MODELS

### Entity Relationship Diagram

```
CustomUser ──1:1── KYC
CustomUser ──1:1── Cart ──1:N── CartItem ──N:1── ItemMaster
CustomUser ──1:1── Wishlist ──1:N── WishlistItem ──N:1── ItemMaster
CustomUser ──1:1── RetailerWallet ──1:N── WalletTransaction
CustomUser ──1:N── Address
CustomUser ──1:N── Payment
CustomUser ──N:1── Store (preferred_store)

Store ──1:N── ProductStore ──N:1── ItemMaster
Store ──1:N── SalesOrder
Store ──1:N── ProductCache

ItemMaster ──1:1── ProductInfo ──1:N── ProductImage
ItemMaster ──1:N── Stock
ProductInfo ──N:1── Category

SalesOrder ──1:N── SalesOrderItem
SalesOrder ──1:N── Invoice ──1:N── InvoiceDetail
SalesOrder ──1:N── Payment ──1:N── PaymentLog
Payment ──1:N── PaymentRefund

Category ──1:N── Offer ──1:N── RetailerNotification
CreditNote ──N:1── CustomUser
```

### Model Details (28 models, 3 apps)

#### CustomUser
| Field | Type | Notes |
|-------|------|-------|
| role | CharField(20) | SUPERADMIN / RETAILER |
| status | CharField(30) | PENDING_OTP → REGISTERED → KYC_SUBMITTED → APPROVED |
| phone_number | CharField(15) | unique |
| preferred_store | FK → Store | Auto-set from location |
| last_latitude/longitude | FloatField | GPS coordinates |
| is_kyc_approved | BooleanField | |

#### Store
| Field | Type | Notes |
|-------|------|-------|
| name | CharField(255) | unique |
| latitude/longitude | FloatField | Auto-geocoded from pincode |
| c2_code | CharField(20) | unique, ERP company code |
| store_id | CharField(20) | unique, ERP store ID |
| security_key | CharField(255) | ERP auth key |
| is_active | BooleanField | |
| is_primary | BooleanField | Fallback store |

#### ItemMaster (PK: item_code)
| Field | Type | Notes |
|-------|------|-------|
| item_code | CharField(50) | **Primary Key** |
| item_name | CharField(255) | |
| mrp | Decimal(10,2) | Max Retail Price |
| std_disc | Decimal(10,2) | Standard discount % |
| max_disc | Decimal(10,2) | Max discount % |
| expiry_date | DateField | |
| batch_no | CharField(100) | |

#### ProductStore (per-store pricing & stock)
| Field | Type | Notes |
|-------|------|-------|
| product | FK → ItemMaster | unique_together with store |
| store | FK → Store | |
| price | Decimal(10,2) | Store-specific |
| stock_quantity | IntegerField | Real-time count |
| is_available | BooleanField | |

#### Cart / CartItem
- Cart: OneToOne with User. Has `convenience_fee`, `delivery_fee`, `platform_fee` (default ₹29)
- CartItem: FK to Cart + ItemMaster. Has `quantity`, `batch_no`, `version` (optimistic lock)
- Computed: `get_discounted_price()`, `get_item_total_discounted()`, `get_item_savings()`

#### SalesOrder
| Field | Type | Notes |
|-------|------|-------|
| order_id | CharField(100) | unique, auto: ORD-YYYYMMDD-XXXXXXXX |
| status | CharField(20) | pending/confirmed/processing/completed/failed |
| fulfilling_store | FK → Store | Which store fulfilled |
| order_total | Decimal(12,2) | |
| ord_conversion_flag | BooleanField | True = Confirmed |
| dc_conversion_flag | BooleanField | True = Delivered |
| invoice_sync_status | CharField(20) | pending/syncing/found/failed |

#### Payment
| Field | Type | Notes |
|-------|------|-------|
| payment_id | UUID | unique, auto |
| razorpay_order_id | CharField(100) | unique |
| razorpay_payment_id | CharField(100) | unique |
| payment_method | CharField(20) | RAZORPAY/COD/UPI/WALLET/NETBANKING |
| status | CharField(20) | INITIATED/PENDING/SUCCESS/FAILED/REFUNDED |
| amount | Decimal(12,2) | |
| retry_count | IntegerField | Max 5 |
| cod_collected | BooleanField | COD specific |

#### CreditNote
| Field | Type | Notes |
|-------|------|-------|
| credit_note_id | CharField(20) | Auto: CN001, CN002... |
| status | CharField(20) | PENDING/APPROVED/REJECTED/DELIVERED |
| reason | CharField(20) | DAMAGED/EXPIRED/WRONG_ITEM/BILLING/OTHER |
| quantity_to_return | IntegerField | |
| amount | Decimal(10,2) | Refund amount |

#### RetailerWallet / WalletTransaction
- Wallet: OneToOne with User. `balance` Decimal(12,2), `version` for locking
- Transaction: `type` (CREDIT/DEBIT), `source` (CREDIT_NOTE/ORDER_PAYMENT/MANUAL), `closing_balance`

#### Other Models
- **KYC**: drug_license, id_proof, store_photo, gst_number (files + text)
- **Address**: name, phone, pincode, city, state, locality, lat/lng, address_type (HOME/OFFICE/OTHER)
- **Category**: name, icon image (brands like Cipla, Mankind)
- **ProductInfo**: subheading, description, type_label → linked to ItemMaster
- **ProductImage**: up to 3 images per product (image_order 1-3)
- **Stock**: per-item per-store stock levels from ERP
- **Offer**: banners with valid_from/valid_to, placement (homepage/category)
- **AuditLog**: log_id (AUD-001), action, category, performed_by
- **AdminNotification**: type (USER/ORDER/INVENTORY/PAYMENT), priority (CRITICAL/HIGH/MEDIUM/LOW)
- **FCMDevice**: Firebase push notification tokens
- **RetailerNotification**: per-retailer notifications for offers

---

## 16. LOCATION-BASED FLOW

```
┌─────────────┐     POST /stores/find-nearest/     ┌──────────────┐
│ Flutter App  │ ─────────────────────────────────► │ Django API   │
│ (GPS lat/lng)│ ◄───────────────────────────────── │ Returns:     │
└──────┬───────┘   { store_id, c2_code, distance }  │ nearest store│
       │                                            └──────┬───────┘
       │                                                   │
       │  GET /erp/ws_c2_services_get_master_data          │
       │  ?storeId=002&userId=1&page=1                     │
       │ ──────────────────────────────────────────────────►│
       │                                                   │──► ERP Server
       │ ◄──────────────────────────────────────────────────│    (store 002)
       │   Products + pagination + cart/wishlist status     │
       │                                                   │
       │  POST /cart/add/1/                                 │
       │  { "itemCode":"IT001", "storeId":"002" }          │
       │ ──────────────────────────────────────────────────►│
       │                                                   │──► Verify stock
       │ ◄──────────────────────────────────────────────────│    at store 002
       │   { success: true }                               │
       │                                                   │
       │  POST /erp/ws_c2_services_create_sale_order       │
       │  { storeId:"002", paymentMode:"COD", ... }        │
       │ ──────────────────────────────────────────────────►│
       │                                                   │──► Create order
       │ ◄──────────────────────────────────────────────────│    at store 002
       │   { order_id: "ORD-xxx" }                         │
```

---

## 17. ERROR CODES

| HTTP | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request / Validation Error |
| 401 | Unauthorized (missing/invalid JWT) |
| 403 | Forbidden (wrong role) |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | ERP Service Unavailable |

**Error Response Format:**
```json
{ "success": false, "message": "Human-readable error", "errors": { "field": ["detail"] } }
```

**Content Types:**
- `application/json` — All JSON endpoints
- `multipart/form-data` — File uploads (KYC, images, offers)

---

*Generated: 2026-05-04 | DreamsPharma Backend v1.0*
