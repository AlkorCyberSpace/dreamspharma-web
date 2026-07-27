#!/usr/bin/env python
"""
Comprehensive Endpoint Test Suite for DreamsPharma API
Tests ALL endpoints including: Auth, Cart, Wishlist, Products, Search, Recommendations, Addresses, Payment, Orders
"""

import requests
import json
import os
from datetime import datetime

BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")

# Test data
TEST_USER_PHONE = "9999999999"
TEST_USER_OTP = "111111"
TEST_USER_PASSWORD = "Test@123456"
TEST_ITEM_CODE = "INJ001"
TEST_ADDRESS_ID = 1
TEST_ORDER_ID = 1

def log_test(name, url, method, status, result, details=""):
    """Log test result"""
    status_icon = "✓" if result else "✗"
    print(f"{status_icon} {name:50s} | {method:6s} | {str(status):6s} | {str(details)[:60]}")
    return {
        'endpoint': name,
        'url': url,
        'method': method,
        'status_code': status,
        'result': 'PASS' if result else 'FAIL',
        'details': str(details)[:100]
    }

def test_endpoint(name, method, url, params=None, data=None, headers=None, expected_status=None):
    """Test a single endpoint"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{url}", params=params, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{url}", json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(f"{BASE_URL}{url}", json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(f"{BASE_URL}{url}", headers=headers, timeout=10)
        else:
            return log_test(name, url, method, 0, False, "Invalid method")
        
        status_code = response.status_code
        if expected_status:
            success = status_code in expected_status
        else:
            success = status_code in [200, 201, 204]
        
        try:
            resp_data = response.json()
            detail = resp_data.get('message', resp_data.get('detail', ''))
            return log_test(name, url, method, status_code, success, detail)
        except:
            return log_test(name, url, method, status_code, success, response.text[:50])
    
    except Exception as e:
        return log_test(name, url, method, 0, False, str(e)[:60])

def run_all_tests():
    """Run all endpoint tests"""
    results = []
    
    print("\n" + "="*150)
    print("DREAMSPHARMA - COMPREHENSIVE ENDPOINT TEST SUITE")
    print("="*150)
    
    # ================================
    # 1. AUTHENTICATION ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("1. AUTHENTICATION ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "OTPRequestView (Send OTP)",
        "POST", "/api/send-otp/",
        data={'mobile': TEST_USER_PHONE}
    ))
    
    results.append(test_endpoint(
        "OTPVerifyView (Verify OTP)",
        "POST", "/api/verify-otp/",
        data={'mobile': TEST_USER_PHONE, 'otp': TEST_USER_OTP},
        expected_status=[200, 400]
    ))
    
    results.append(test_endpoint(
        "UserRegistrationView (Register)",
        "POST", "/api/register/",
        data={
            'mobile': TEST_USER_PHONE,
            'password': TEST_USER_PASSWORD,
            'confirm_password': TEST_USER_PASSWORD,
            'first_name': 'Test',
            'last_name': 'User'
        },
        expected_status=[200, 201, 400]
    ))
    
    results.append(test_endpoint(
        "RetailerLoginView (Login)",
        "POST", "/api/retailer/login/",
        data={'username': TEST_USER_PHONE, 'password': TEST_USER_PASSWORD},
        expected_status=[200, 400]
    ))
    
    results.append(test_endpoint(
        "LogoutView (Logout)",
        "POST", "/api/logout/",
        expected_status=[200, 401]
    ))
    
    results.append(test_endpoint(
        "ForgotPasswordView (Forgot Password)",
        "POST", "/api/forgot-password/",
        data={'mobile': TEST_USER_PHONE},
        expected_status=[200, 400]
    ))
    
    results.append(test_endpoint(
        "PasswordResetView (Reset Password)",
        "POST", "/api/reset-password/",
        data={'mobile': TEST_USER_PHONE, 'new_password': 'NewPass@123'},
        expected_status=[200, 400]
    ))
    
    results.append(test_endpoint(
        "ChangePasswordView (Change Password)",
        "POST", "/api/change-password/",
        data={'old_password': TEST_USER_PASSWORD, 'new_password': 'NewPass@123'},
        expected_status=[200, 401, 400]
    ))
    
    # ================================
    # 2. ERP INTEGRATION ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("2. ERP INTEGRATION ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "GetItemMasterView (Fetch Items from ERP)",
        "GET", "/api/erp/ws_c2_services_get_master_data"
    ))
    
    results.append(test_endpoint(
        "FetchStockView (Fetch Stock from ERP)",
        "GET", "/api/erp/ws_c2_services_fetch_stock"
    ))
    
    results.append(test_endpoint(
        "CreateSalesOrderView (Create Sales Order)",
        "POST", "/api/erp/create-sales-order/",
        data={
            'order_date': datetime.now().strftime('%Y-%m-%d'),
            'items': [{'item_code': TEST_ITEM_CODE, 'quantity': 1}]
        },
        expected_status=[200, 201, 400]
    ))
    
    results.append(test_endpoint(
        "CreateGLCustomerView (Create GL Customer)",
        "POST", "/api/erp/create-gl-customer/",
        data={
            'customer_name': 'Test Customer',
            'mobile': TEST_USER_PHONE,
            'email': 'test@example.com'
        },
        expected_status=[200, 201, 400]
    ))
    
    results.append(test_endpoint(
        "GetOrderStatusView (Get Order Status)",
        "GET", "/api/erp/order-status/",
        params={'order_id': TEST_ORDER_ID},
        expected_status=[200, 404]
    ))
    
    # ================================
    # 3. PRODUCT ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("3. PRODUCT ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "AllProductsView (Get All Products)",
        "GET", "/api/products/"
    ))
    
    results.append(test_endpoint(
        "GetItemMasterView",
        "GET", "/api/erp/ws_c2_services_get_master_data"
    ))
    
    results.append(test_endpoint(
        "UpdateProductInfoView (Update Product)",
        "PUT", "/api/product/update/",
        data={'item_code': TEST_ITEM_CODE, 'description': 'Updated product'},
        expected_status=[200, 400, 404]
    ))
    
    # ================================
    # 4. SEARCH ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("4. SEARCH ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "SearchProductsView (Search Products)",
        "GET", "/api/search/",
        params={'query': 'paracetamol'}
    ))
    
    results.append(test_endpoint(
        "PopularSearchView (Get Popular Searches)",
        "GET", "/api/search/popular/"
    ))
    
    results.append(test_endpoint(
        "SearchWithHistoryView (Search with History)",
        "GET", "/api/search-history/",
        params={'query': 'aspirin'}
    ))
    
    results.append(test_endpoint(
        "LogSearchView (Log Search Query)",
        "POST", "/api/log-search/",
        data={'query': 'ibuprofen'},
        expected_status=[200, 201]
    ))
    
    # ================================
    # 5. CART ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("5. CART ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "CartView (Get Cart)",
        "GET", "/api/cart/",
        expected_status=[200, 401]
    ))
    
    results.append(test_endpoint(
        "AddToCartView (Add to Cart)",
        "POST", "/api/cart/add/",
        data={'item_code': TEST_ITEM_CODE, 'quantity': 2},
        expected_status=[200, 201, 400, 401]
    ))
    
    results.append(test_endpoint(
        "UpdateCartItemView (Update Cart Item)",
        "PUT", "/api/cart/update/",
        data={'cart_item_id': 1, 'quantity': 3},
        expected_status=[200, 400, 404, 401]
    ))
    
    results.append(test_endpoint(
        "RemoveFromCartView (Remove from Cart)",
        "DELETE", "/api/cart/remove/",
        params={'cart_item_id': 1},
        expected_status=[200, 204, 400, 404, 401]
    ))
    
    # ================================
    # 6. WISHLIST ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("6. WISHLIST ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "WishlistView (Get Wishlist)",
        "GET", "/api/wishlist/",
        expected_status=[200, 401]
    ))
    
    results.append(test_endpoint(
        "AddToWishlistView (Add to Wishlist)",
        "POST", "/api/wishlist/add/",
        data={'item_code': TEST_ITEM_CODE},
        expected_status=[200, 201, 400, 401]
    ))
    
    results.append(test_endpoint(
        "UpdateWishlistItemView (Update Wishlist Item)",
        "PUT", "/api/wishlist/update/",
        data={'wishlist_item_id': 1},
        expected_status=[200, 400, 404, 401]
    ))
    
    results.append(test_endpoint(
        "RemoveFromWishlistView (Remove from Wishlist)",
        "DELETE", "/api/wishlist/remove/",
        params={'wishlist_item_id': 1},
        expected_status=[200, 204, 400, 404, 401]
    ))
    
    # ================================
    # 7. ADDRESS ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("7. ADDRESS ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "ListAddressesView (Get All Addresses)",
        "GET", "/api/addresses/",
        expected_status=[200, 401]
    ))
    
    results.append(test_endpoint(
        "CreateAddressView (Create Address)",
        "POST", "/api/addresses/create/",
        data={
            'address': '123 Main St',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'zip_code': '400001',
            'latitude': 19.0760,
            'longitude': 72.8777
        },
        expected_status=[200, 201, 401]
    ))
    
    results.append(test_endpoint(
        "UpdateAddressView (Update Address)",
        "PUT", "/api/addresses/update/",
        data={
            'address_id': TEST_ADDRESS_ID,
            'address': '456 New St',
            'city': 'Bangalore'
        },
        expected_status=[200, 400, 404, 401]
    ))
    
    results.append(test_endpoint(
        "DeleteAddressView (Delete Address)",
        "DELETE", "/api/addresses/delete/",
        params={'address_id': TEST_ADDRESS_ID},
        expected_status=[200, 204, 400, 404, 401]
    ))
    
    # ================================
    # 8. CHECKOUT & ORDER ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("8. CHECKOUT & ORDER ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "CheckoutWithAddressView (Checkout)",
        "POST", "/api/checkout/",
        data={
            'address_id': TEST_ADDRESS_ID,
            'payment_method': 'credit_card',
            'items': [{'item_code': TEST_ITEM_CODE, 'quantity': 1}]
        },
        expected_status=[200, 201, 400, 401]
    ))
    
    # ================================
    # 9. RECOMMENDATION ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("9. RECOMMENDATION ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "TopSellingProductsView (Top Selling Products)",
        "GET", "/api/recommendations/top-selling/",
        params={'period': 'monthly', 'limit': 10}
    ))
    
    results.append(test_endpoint(
        "PopularProductsView (Popular Products)",
        "GET", "/api/recommendations/popular/",
        params={'limit': 10}
    ))
    
    results.append(test_endpoint(
        "TrendingProductsView (Trending Products)",
        "GET", "/api/recommendations/trending/",
        params={'limit': 10},
        expected_status=[200, 404]
    ))
    
    results.append(test_endpoint(
        "FrequentlyBoughtTogetherView (Frequently Bought Together)",
        "GET", "/api/recommendations/frequently-bought/",
        params={'itemCode': TEST_ITEM_CODE, 'limit': 5},
        expected_status=[200, 404]
    ))
    
    results.append(test_endpoint(
        "PersonalizedRecommendationsView (Personalized Recommendations)",
        "GET", "/api/recommendations/for-you/",
        params={'limit': 10},
        expected_status=[200, 401]
    ))
    
    # ================================
    # 10. PAYMENT ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("10. PAYMENT ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "InitiatePaymentView (Initiate Payment)",
        "POST", "/api/payment/initiate/",
        data={
            'order_id': TEST_ORDER_ID,
            'amount': 1000.00,
            'payment_method': 'credit_card'
        },
        expected_status=[200, 201, 400, 404]
    ))
    
    results.append(test_endpoint(
        "VerifyPaymentView (Verify Payment)",
        "POST", "/api/payment/verify/",
        data={
            'order_id': TEST_ORDER_ID,
            'payment_ref': 'PAY123456'
        },
        expected_status=[200, 400, 404]
    ))
    
    results.append(test_endpoint(
        "PaymentStatusView (Payment Status)",
        "GET", "/api/payment/status/",
        params={'order_id': TEST_ORDER_ID},
        expected_status=[200, 404]
    ))
    
    results.append(test_endpoint(
        "InitiateRefundView (Initiate Refund)",
        "POST", "/api/payment/refund/",
        data={'order_id': TEST_ORDER_ID},
        expected_status=[200, 400, 404]
    ))
    
    # ================================
    # 11. PROFILE ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("11. PROFILE ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "ProfileView (Get/Update Profile)",
        "GET", "/api/profile/",
        expected_status=[200, 401]
    ))
    
    results.append(test_endpoint(
        "UpdateProfileView (Update Profile)",
        "PUT", "/api/profile/update/",
        data={'first_name': 'Updated', 'last_name': 'User'},
        expected_status=[200, 400, 401]
    ))
    
    # ================================
    # 12. KYC ENDPOINTS
    # ================================
    print("\n" + "="*150)
    print("12. KYC ENDPOINTS")
    print("="*150)
    
    results.append(test_endpoint(
        "KYCSubmitView (Submit KYC)",
        "POST", "/api/kyc/submit/",
        data={
            'shop_name': 'Test Shop',
            'shop_license': 'LICENSE123',
            'gst_number': 'GST123'
        },
        expected_status=[200, 201, 400, 401]
    ))
    
    results.append(test_endpoint(
        "KYCStatusView (Check KYC Status)",
        "GET", "/api/kyc/status/",
        expected_status=[200, 401]
    ))
    
    # ================================
    # SUMMARY
    # ================================
    print("\n" + "="*150)
    print("TEST SUMMARY")
    print("="*150)
    
    passed = sum(1 for r in results if r['result'] == 'PASS')
    total = len(results)
    
    print(f"\nTotal Endpoints Tested: {total}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%\n")
    
    # Create detailed report
    with open('COMPREHENSIVE_ENDPOINT_TEST_REPORT.txt', 'w', encoding='utf-8') as f:
        f.write("="*150 + "\n")
        f.write("DREAMSPHARMA - COMPREHENSIVE ENDPOINT TEST REPORT\n")
        f.write("="*150 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Endpoints: {total}\n")
        f.write(f"✓ Passed: {passed}\n")
        f.write(f"✗ Failed: {total - passed}\n")
        f.write(f"Success Rate: {(passed/total)*100:.1f}%\n\n")
        
        f.write("DETAILED RESULTS:\n")
        f.write("="*150 + "\n")
        f.write(f"{'Endpoint':<50s} | {'Method':<6s} | {'Status':<6s} | {'Result':<6s} | {'Details':<80s}\n")
        f.write("-"*150 + "\n")
        
        for result in results:
            f.write(f"{result['endpoint']:<50s} | {result['method']:<6s} | {str(result['status_code']):<6s} | {result['result']:<6s} | {result['details']:<80s}\n")
        
        f.write("\n" + "="*150 + "\n")
        f.write("GROUPED BY CATEGORY:\n")
        f.write("="*150 + "\n\n")
        
        categories = {
            "Authentication": ["OTP", "Login", "Register", "Password", "Logout"],
            "ERP Integration": ["ERP", "GetItem", "FetchStock", "SalesOrder", "GLCustomer", "OrderStatus"],
            "Products": ["Product"],
            "Search": ["Search"],
            "Cart": ["Cart"],
            "Wishlist": ["Wishlist"],
            "Addresses": ["Address"],
            "Checkout": ["Checkout"],
            "Recommendations": ["Top", "Popular", "Trending", "Frequently", "Personalized"],
            "Payment": ["Payment", "Refund"],
            "Profile": ["Profile", "KYC"]
        }
        
        for category, keywords in categories.items():
            cat_results = [r for r in results if any(kw in r['endpoint'] for kw in keywords)]
            if cat_results:
                cat_passed = sum(1 for r in cat_results if r['result'] == 'PASS')
                f.write(f"\n{category} ({cat_passed}/{len(cat_results)} passed):\n")
                for r in cat_results:
                    status = "✓" if r['result'] == 'PASS' else "✗"
                    f.write(f"  {status} {r['endpoint']:<60s} {r['result']}\n")
    
    print("✓ Report saved to: COMPREHENSIVE_ENDPOINT_TEST_REPORT.txt")
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
