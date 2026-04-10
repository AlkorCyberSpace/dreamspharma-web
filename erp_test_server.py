"""
ERP Test Server - Flask Application
Run this to simulate the client's ERP system for testing

Usage:
    pip install flask
    python erp_test_server.py

Server will run on: http://192.168.1.63:8000/
"""

from flask import Flask, request, jsonify
import base64
from datetime import datetime

app = Flask(__name__)

# ==================== DUMMY DATA ====================

# API Tokens storage
API_TOKENS = {}

# Item Master Data
ITEMS = [
    {
        "c_item_code": "I00003",
        "itemName": "DOLO 250MG SUSP",
        "itemQtyPerBox": 1,
        "batchNo": "DOLN096",
        "stockBalQty": 984,
        "std_disc": 24.24,
        "max_disc": 0.00,
        "expiryDate": "2027-11-01",
        "mrp": 75.03
    },
    {
        "c_item_code": "I00017",
        "itemName": "AMALGIN",
        "itemQtyPerBox": 1,
        "batchNo": "AMG001",
        "stockBalQty": 2000,
        "std_disc": 15.00,
        "max_disc": 0.00,
        "expiryDate": "2027-12-01",
        "mrp": 85.50
    },
    {
        "c_item_code": "I00049",
        "itemName": "ASPIRIN 500MG",
        "itemQtyPerBox": 10,
        "batchNo": "ASP001",
        "stockBalQty": 500,
        "std_disc": 20.00,
        "max_disc": 5.00,
        "expiryDate": "2027-10-15",
        "mrp": 6.81
    },
    {
        "c_item_code": "I00048",
        "itemName": "PARACETAMOL 650MG",
        "itemQtyPerBox": 10,
        "batchNo": "PARA001",
        "stockBalQty": 1200,
        "std_disc": 18.00,
        "max_disc": 3.00,
        "expiryDate": "2027-09-30",
        "mrp": 16.81
    },
    {
        "c_item_code": "513556",
        "itemName": "1 PARA 650MG TAB",
        "itemQtyPerBox": 10,
        "batchNo": "PARA002",
        "stockBalQty": 9970,
        "std_disc": 22.00,
        "max_disc": 4.00,
        "expiryDate": "2027-08-20",
        "mrp": 45.00
    },
    {
        "c_item_code": "648538",
        "itemName": "&ME PCOS CRANBERRY DRINK",
        "itemQtyPerBox": 1,
        "batchNo": "3030",
        "stockBalQty": 150,
        "std_disc": 10.00,
        "max_disc": 2.00,
        "expiryDate": "2029-07-01",
        "mrp": 170.00
    },
    {
        "c_item_code": "I00099",
        "itemName": "AMOXICILLIN 500MG - OUT OF STOCK",
        "itemQtyPerBox": 10,
        "batchNo": "AMX001",
        "stockBalQty": 0,
        "std_disc": 20.00,
        "max_disc": 5.00,
        "expiryDate": "2027-06-30",
        "mrp": 45.50
    },
    {
        "c_item_code": "I00077",
        "itemName": "IBUPROFEN 400MG - EXPIRED",
        "itemQtyPerBox": 10,
        "batchNo": "IBU001",
        "stockBalQty": 500,
        "std_disc": 15.00,
        "max_disc": 3.00,
        "expiryDate": "2025-01-15",
        "mrp": 12.50
    }
]

# Stock Data
STOCK = [
    {
        "itemCode": "I00017",
        "itemName": "AMALGIN",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 1,
        "totalBalLsQty": 2000,
        "packQty": 2000,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-12-08 16:57:25.162"
    },
    {
        "itemCode": "513556",
        "itemName": "1 PARA 650MG TAB",
        "contCode": "P008",
        "contName": "PARACETAMOL",
        "qtyBox": 10,
        "totalBalLsQty": 9970,
        "packQty": 997,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-08-11 16:39:41.296"
    },
    {
        "itemCode": "I00003",
        "itemName": "DOLO 250MG SUSP",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 1,
        "totalBalLsQty": 984,
        "packQty": 984,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-11-01 10:00:00.000"
    },
    {
        "itemCode": "I00049",
        "itemName": "ASPIRIN 500MG",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 5,
        "totalBalLsQty": 500,
        "packQty": 50,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-10-15 12:00:00.000"
    },
    {
        "itemCode": "I00048",
        "itemName": "PARACETAMOL 650MG",
        "contCode": "P008",
        "contName": "PARACETAMOL",
        "qtyBox": 10,
        "totalBalLsQty": 1200,
        "packQty": 120,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-09-30 14:00:00.000"
    },
    {
        "itemCode": "648538",
        "itemName": "&ME PCOS CRANBERRY DRINK",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 150,
        "totalBalLsQty": 150,
        "packQty": 150,
        "looseQty": 0,
        "lastModifiedDateTime": "2029-07-01 10:00:00.000"
    },
    {
        "itemCode": "I00099",
        "itemName": "AMOXICILLIN 500MG - OUT OF STOCK",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 10,
        "totalBalLsQty": 0,
        "packQty": 0,
        "looseQty": 0,
        "lastModifiedDateTime": "2026-03-10 10:00:00.000"
    },
    {
        "itemCode": "I00077",
        "itemName": "IBUPROFEN 400MG - EXPIRED",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 10,
        "totalBalLsQty": 500,
        "packQty": 50,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-01-15 10:00:00.000"
    }
]

# Orders storage
ORDERS = {
    "aditya001": {
        "orderId": "aditya001",
        "custCode": "GC01",
        "customerName": "Lawrence Nadar",
        "fromGstNo": "07NQQAE5107K2ZW",
        "toGstNo": "07NQQAE5107K2ZW",
        "customerType": "Un - Registered",
        "doctorName": "-",
        "documentPk": "24001540035",
        "brCode": "001",
        "tranYear": "24",
        "tranPrefix": "6",
        "tranSrno": "35",
        "createdDate": "2024-07-24",
        "billTotal": "254.18",
        "invoices": [
            {
                "docNo": "001/25/S/105",
                "docDate": "2025-09-20",
                "docStatus": "Invoice Created",
                "createdBy": "MYBOSS",
                "docDiscount": "0.00",
                "docTotal": "106.00",
                "detail": [
                    {
                        "productId": "648538",
                        "productName": "&ME PCOS CRANBERRY DRINK",
                        "hsnCode": "21069099",
                        "qtyPerBox": "1",
                        "batch": "3030",
                        "qty": "1.000",
                        "expiryDate": "2029-07-01",
                        "mrp": "170.000",
                        "saleRate": "90.000",
                        "discAmt": "0.00",
                        "discPer": "0.00",
                        "itemTotal": "170.000000",
                        "cgstPer": "0.00",
                        "cgstAmt": "0.00",
                        "sgstPer": "0.00",
                        "sgstAmt": "0.00",
                        "igstPer": "18.00",
                        "igstAmt": "16.20",
                        "cessPer": "0.00",
                        "cessAmt": "0.00"
                    }
                ]
            }
        ]
    }
}

# Customers storage
CUSTOMERS = {
    "GC01": {
        "code": "GC01",
        "ipName": "Lawrence Nadar",
        "mail": "lawrence@pharmacy.com",
        "gender": "M",
        "city": "Mumbai",
        "ipState": "Maharashtra"
    }
}

# Order counter for generating document numbers
ORDER_COUNTER = 100


# ==================== API ENDPOINTS ====================

@app.route('/ws_c2_services_generate_token', methods=['GET', 'POST'])
def generate_token():
    """Generate API Token"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        c2_code = data.get('c2Code')
        store_id = data.get('storeId')
        prod_code = data.get('prodCode', '02')
        security_key = data.get('securityKey')
        
        if not all([c2_code, store_id, security_key]):
            return jsonify({
                "code": "400",
                "type": "generateToken",
                "message": "Missing required parameters"
            }), 400
        
        # Generate API key
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        api_key = base64.b64encode(f"{c2_code}{store_id}^{timestamp}".encode()).decode()
        
        # Store token
        API_TOKENS[api_key] = {
            "c2_code": c2_code,
            "store_id": store_id,
            "created_at": timestamp
        }
        
        print(f"[TOKEN] Generated for {c2_code}: {api_key}")
        
        return jsonify({
            "code": "200",
            "type": "generateToken",
            "apiKey": api_key
        })
    except Exception as e:
        return jsonify({
            "code": "500",
            "type": "generateToken",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_get_master_data', methods=['GET', 'POST'])
def get_master_data():
    """Get Item Master Data"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        api_key = data.get('apiKey')
        index_id = data.get('indexId')
        
        # For testing, accept any API key or check if it exists
        # In production, validate properly
        
        print(f"[MASTER DATA] Request received with apiKey: {api_key[:20] if api_key else 'None'}...")
        
        response_data = ITEMS
        
        # Filter by indexId if provided
        if index_id:
            try:
                idx = int(index_id)
                if 0 <= idx < len(ITEMS):
                    response_data = [ITEMS[idx]]
            except ValueError:
                pass
        
        return jsonify({
            "code": "200",
            "type": "getMasterData",
            "data": response_data
        })
    except Exception as e:
        return jsonify({
            "code": "400",
            "type": "getMasterData",
            "message": str(e)
        }), 400


@app.route('/ws_c2_services_fetch_stock', methods=['GET', 'POST'])
def fetch_stock():
    """Fetch Stock Data"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        api_key = data.get('apiKey')
        store_id = data.get('storeId')
        
        print(f"[STOCK] Request for store: {store_id}")
        
        return jsonify(STOCK)
    except Exception as e:
        return jsonify({
            "code": "500",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_create_sale_order', methods=['POST'])
def create_sale_order():
    """Create Sales Order"""
    global ORDER_COUNTER
    
    try:
        data = request.get_json()
        
        api_key = data.get('apiKey')
        order_id = data.get('orderId')
        patient_name = data.get('patientName')
        order_total = data.get('orderTotal')
        material_info = data.get('materialInfo', [])
        
        print(f"[ORDER] Creating order {order_id} for {patient_name}")
        
        # Generate document number
        ORDER_COUNTER += 1
        year = datetime.now().strftime("%y")
        doc_pk = f"{year}001540{ORDER_COUNTER:03d}"
        
        # Store order
        order_data = {
            "orderId": str(order_id),
            "custCode": data.get('actCode', 'GC01'),
            "customerName": data.get('actName', patient_name),
            "fromGstNo": "07NQQAE5107K2ZW",
            "toGstNo": "07NQQAE5107K2ZW",
            "customerType": "Un - Registered",
            "doctorName": data.get('drName', '-'),
            "documentPk": doc_pk,
            "brCode": data.get('storeId', '001'),
            "tranYear": year,
            "tranPrefix": "6",
            "tranSrno": str(ORDER_COUNTER),
            "createdDate": data.get('ordDate', datetime.now().strftime("%Y-%m-%d")),
            "billTotal": str(order_total),
            "invoices": []
        }
        
        ORDERS[str(order_id)] = order_data
        
        return jsonify({
            "code": "200",
            "type": "SaleOrderCreate",
            "message": f"Document No. : {doc_pk} successfully processed.",
            "documentDetails": [{
                "brCode": order_data["brCode"],
                "tranYear": order_data["tranYear"],
                "tranPrefix": order_data["tranPrefix"],
                "tranSrno": order_data["tranSrno"],
                "documentPk": doc_pk,
                "OrderId": order_id,
                "createdDate": order_data["createdDate"],
                "billTotal": order_data["billTotal"]
            }]
        }), 201
    except Exception as e:
        return jsonify({
            "code": "500",
            "type": "SaleOrderCreate",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_gl_cust_creation', methods=['GET', 'POST'])
def create_gl_customer():
    """Create Global Local Customer"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        code = data.get('Code')
        ip_name = data.get('ipName')
        
        if not code:
            return jsonify({
                "code": "400",
                "type": "glcustcreation",
                "message": "LcCode Cannot be Null or empty."
            }), 400
        
        if code in CUSTOMERS:
            return jsonify({
                "code": "400",
                "type": "glcustcreation",
                "message": f"LcCode Already Exists:{code}"
            }), 400
        
        # Store customer
        CUSTOMERS[code] = {
            "code": code,
            "ipName": ip_name,
            "mail": data.get('Mail'),
            "gender": data.get('Gender'),
            "city": data.get('City'),
            "ipState": data.get('ipState'),
            "mobile": data.get('Mobile'),
            "gstNo": data.get('Gstno')
        }
        
        print(f"[CUSTOMER] Created: {code} - {ip_name}")
        
        return jsonify({
            "code": "200",
            "type": "glcustcreation",
            "message": f"Customer Name : {ip_name} with Customer Code : {code} created sucessfully."
        }), 201
    except Exception as e:
        return jsonify({
            "code": "500",
            "type": "glcustcreation",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_get_orderstatus', methods=['GET', 'POST'])
def get_order_status():
    """Get Order Status with Transaction Details"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        order_id = data.get('orderId')
        
        print(f"[ORDER STATUS] Request for order: {order_id}")
        
        if not order_id:
            return jsonify({
                "code": "400",
                "message": "orderId is required"
            }), 400
        
        order = ORDERS.get(str(order_id))
        
        if not order:
            return jsonify({
                "code": "404",
                "message": f"Order {order_id} not found"
            }), 404
        
        return jsonify({
            "code": "200",
            "orderId": order["orderId"],
            "custCode": order["custCode"],
            "fromGstNo": order["fromGstNo"],
            "toGstNo": order["toGstNo"],
            "customerType": order["customerType"],
            "doctorName": order["doctorName"],
            "invoices": order["invoices"]
        })
    except Exception as e:
        return jsonify({
            "code": "500",
            "message": str(e)
        }), 500


@app.route('/')
def home():
    """Home page with API documentation"""
    return """
    <html>
    <head>
        <title>ERP Test Server</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { display: inline-block; padding: 3px 8px; border-radius: 3px; color: white; font-weight: bold; }
            .get { background: #61affe; }
            .post { background: #49cc90; }
            code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
            pre { background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🏥 ERP Test Server - Dream Pharma</h1>
        <p>Server is running on port 44000</p>
        
        <h2>Available Endpoints:</h2>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/ws_c2_services_generate_token</code>
            <p>Generate API Token</p>
            <pre>{
  "c2Code": "03C000",
  "storeId": "001",
  "prodCode": "02",
  "securityKey": "TUVVek1EQXhNalE9"
}</pre>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/ws_c2_services_get_master_data</code>
            <p>Get Item Master Data</p>
            <pre>?c2Code=03C000&storeId=001&prodCode=02&apiKey=YOUR_API_KEY</pre>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/ws_c2_services_fetch_stock</code>
            <p>Fetch Stock Data</p>
            <pre>?c2Code=03C000&storeId=001&prodCode=02&apiKey=YOUR_API_KEY</pre>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/ws_c2_services_create_sale_order</code>
            <p>Create Sales Order</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/ws_c2_services_gl_cust_creation</code>
            <p>Create Global Local Customer</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/ws_c2_services_get_orderstatus</code>
            <p>Get Order Status</p>
            <pre>?c2Code=03C000&storeId=001&apiKey=YOUR_API_KEY&orderId=aditya001</pre>
        </div>
        
        <h2>Quick Test:</h2>
        <p>Try <a href="/ws_c2_services_get_master_data?c2Code=03C000&storeId=001&apiKey=test">/ws_c2_services_get_master_data?c2Code=03C000&storeId=001&apiKey=test</a></p>
        <p>Try <a href="/ws_c2_services_fetch_stock?c2Code=03C000&storeId=001&apiKey=test">/ws_c2_services_fetch_stock?c2Code=03C000&storeId=001&apiKey=test</a></p>
        <p>Try <a href="/ws_c2_services_get_orderstatus?c2Code=03C000&storeId=001&apiKey=test&orderId=aditya001">/ws_c2_services_get_orderstatus?orderId=aditya001</a></p>
    </body>
    </html>
    """


import os

if __name__ == '__main__':
    # Render provides the port via an environment variable
    # We default to 44000 for your local testing
    port = int(os.environ.get("PORT", 44000))
    
    print("=" * 60)
    print("ERP Test Server - Dream Pharma")
    print("=" * 60)
    print(f"Starting server on port: {port}")
    print("=" * 60)
    
    # We use 0.0.0.0 so it's accessible externally
    app.run(host='0.0.0.0', port=port, debug=True)
