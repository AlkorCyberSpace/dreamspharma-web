# Sales Order Creation API - Updated Payloads

## 🔄 Migration Summary

| Aspect | Before | After |
|--------|--------|-------|
| **orderId** | Frontend provides | Backend auto-generates |
| **Responsibility** | Frontend | Backend |
| **Risk** | ID Collisions | 0% - Guaranteed unique |
| **Format** | Any (123, "ABC") | {storeId}{YYYYMMDD}{HHMMSS}{UUID} |

---

## ✅ NEW PAYLOAD (Recommended - No orderId)

```json
POST http://localhost:8000/api/erp/create-sales-order/

Request:
{
    "c2Code": "03C000",
    "storeId": "001",
    "prodCode": "02",
    "ipNo": "8237791693",
    "mobileNo": "8237791693",
    "patientName": "ADITYA",
    "patientAddress": "JP Nagar",
    "patientEmail": "aditya@mail.in",
    "counterSale": 1,
    "ordDate": "2024-07-24",
    "ordTime": "11:52:35",
    "userId": "Rajath",
    "actCode": "GC01",
    "actName": "Lawrence Nadar",
    "drCode": "GD01",
    "drName": "Dr. Prakash",
    "drAddress": "Bangalore",
    "drRegNo": "12345",
    "drOfficeCode": "-",
    "dmanCode": "-",
    "orderTotal": 254.18,
    "orderDiscPer": 0.00,
    "refNo": 987,
    "remark": "Urgent delivery needed",
    "urgentFlag": 0,
    "ordConversionFlag": 0,
    "dcConversionFlag": 0,
    "ordRefNo": 0,
    "sysName": "PL-EG-RIL",
    "sysIp": "172.16.18.11",
    "sysUser": "Gajanan",
    "materialInfo": [
        {
            "item_seq": 1,
            "item_code": "I00049",
            "item_name": "Paracetamol 500mg",
            "batch_no": "BATCH001",
            "expiry_date": "2025-12-31",
            "total_loose_qty": 30,
            "total_loose_sch_qty": 0,
            "service_qty": 0,
            "sale_rate": 6.806,
            "disc_per": 0.00,
            "sch_disc_per": 0.00
        },
        {
            "item_seq": 2,
            "item_code": "I00048",
            "item_name": "Aspirin 500mg",
            "batch_no": "BATCH002",
            "expiry_date": "2025-11-30",
            "total_loose_qty": 10,
            "total_loose_sch_qty": 5,
            "service_qty": 0,
            "sale_rate": 16.806,
            "disc_per": 1.00,
            "sch_disc_per": 0.00
        }
    ]
}

Response (Success):
{
    "code": "200",
    "type": "SaleOrderCreate",
    "message": "Document No. : 24001540035 successfully processed.",
    "documentDetails": [
        {
            "brCode": "001",
            "tranYear": "24",
            "tranPrefix": "6",
            "tranSrno": "1",
            "documentPk": "24001640035",
            "OrderId": "001202604051430AB12CD34",
            "createdDate": "2024-07-24",
            "billTotal": "254.18"
        }
    ]
}
```

---

## OLD PAYLOAD (Deprecated - Still works for backward compatibility)

```json
POST http://localhost:8000/api/erp/create-sales-order/

Request:
{
    "c2Code": "03C000",
    "storeId": "001",
    "orderId": 120,                          ← DEPRECATED: Not needed anymore
    ...rest of fields...
}

Response:
{
    "code": "200",
    "documentDetails": [{
        "OrderId": 120
    }]
}
```

---

## 🆕 Auto-Generated Order ID Format

### Pattern:
```
{storeId}{YYYYMMDD}{HHMMSS}{UUID}
```

### Examples:
```
001202604051430AB12CD34
002202604051541EF56ABCD
003202604052652GHIJ1234
```

### Breakdown - Example: `001202604051430AB12CD34`
```
001      = Store ID (001)
20260405 = Date (April 5, 2026)
145143   = Time (14:51:43 - 2:51:43 PM)
0AB12CD3 = UUID (guarantees uniqueness)
```

---

## 📝 Real-World Examples

### Example 1: Simple Paracetamol Order
```json
{
    "c2Code": "03C000",
    "storeId": "001",
    "ipNo": "9876543210",
    "mobileNo": "9876543210",
    "patientName": "John Doe",
    "patientAddress": "Bangalore, KA",
    "patientEmail": "john@example.com",
    "counterSale": 1,
    "ordDate": "2026-04-05",
    "ordTime": "14:51:43",
    "userId": "pharmacist_001",
    "actCode": "ACC001",
    "actName": "Customer Account",
    "orderTotal": 150.00,
    "orderDiscPer": 5.00,
    "sysName": "PHARMACY_POS",
    "sysIp": "192.168.1.100",
    "sysUser": "admin",
    "materialInfo": [
        {
            "item_seq": 1,
            "item_code": "PARA500",
            "item_name": "Paracetamol 500mg",
            "batch_no": "BATCH202604",
            "expiry_date": "2027-04-05",
            "total_loose_qty": 20,
            "sale_rate": 7.50,
            "disc_per": 0.00,
            "sch_disc_per": 0.00
        }
    ]
}
```

### Example 2: Multi-Item Prescription Order
```json
{
    "c2Code": "03C000",
    "storeId": "002",
    "ipNo": "8765432109",
    "mobileNo": "8765432109",
    "patientName": "Rajesh Kumar",
    "patientAddress": "Delhi",
    "patientEmail": "rajesh@example.com",
    "counterSale": 0,
    "ordDate": "2026-04-05",
    "ordTime": "10:30:00",
    "userId": "doc_recommended_123",
    "actCode": "ACC002",
    "actName": "Rajesh Kumar",
    "drCode": "DR001",
    "drName": "Dr. Sharma",
    "drAddress": "Medical Center, Delhi",
    "drRegNo": "DL12345",
    "orderTotal": 850.50,
    "orderDiscPer": 10.00,
    "urgentFlag": 1,
    "sysName": "PHARMACY_SYSTEM",
    "sysIp": "192.168.1.105",
    "sysUser": "pharmacist_02",
    "materialInfo": [
        {
            "item_seq": 1,
            "item_code": "AMX250",
            "item_name": "Amoxicillin 250mg",
            "batch_no": "AMX2026001",
            "expiry_date": "2027-06-30",
            "total_loose_qty": 30,
            "sale_rate": 15.00,
            "disc_per": 0.00,
            "sch_disc_per": 0.00
        },
        {
            "item_seq": 2,
            "item_code": "OFL500",
            "item_name": "Ofloxacin 500mg",
            "batch_no": "OFL2026002",
            "expiry_date": "2027-05-15",
            "total_loose_qty": 10,
            "sale_rate": 25.50,
            "disc_per": 5.00,
            "sch_disc_per": 2.00
        },
        {
            "item_seq": 3,
            "item_code": "PARAC1000",
            "item_name": "Paracetamol 1000mg",
            "batch_no": "PARA2026003",
            "expiry_date": "2027-04-05",
            "total_loose_qty": 15,
            "sale_rate": 8.50,
            "disc_per": 0.00,
            "sch_disc_per": 0.00
        }
    ]
}
```

---

## cURL Examples for Testing

### Test 1: Create Order (Auto-Generated ID)
```bash
curl -X POST http://localhost:8000/api/erp/create-sales-order/ \
  -H "Content-Type: application/json" \
  -d '{
    "c2Code": "03C000",
    "storeId": "001",
    "ipNo": "8237791693",
    "mobileNo": "8237791693",
    "patientName": "TEST PATIENT",
    "patientAddress": "Test Address",
    "patientEmail": "test@mail.com",
    "counterSale": 1,
    "ordDate": "2026-04-05",
    "ordTime": "14:51:43",
    "userId": "test_user",
    "actCode": "ACC001",
    "actName": "Test Account",
    "orderTotal": 100.00,
    "sysName": "TEST_SYSTEM",
    "sysIp": "127.0.0.1",
    "sysUser": "tester",
    "materialInfo": [
      {
        "item_seq": 1,
        "item_code": "TEST001",
        "item_name": "Test Item",
        "batch_no": "BATCH001",
        "expiry_date": "2027-04-05",
        "total_loose_qty": 5,
        "sale_rate": 20.00,
        "disc_per": 0.00,
        "sch_disc_per": 0.00
      }
    ]
  }'
```

### Test 2: Multiple Concurrent Orders
```bash
# Run 5 concurrent orders - all get unique IDs
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/erp/create-sales-order/ \
    -H "Content-Type: application/json" \
    -d '{
      "c2Code": "03C000",
      "storeId": "001",
      "ipNo": "8237791693",
      "mobileNo": "823779169'$i'",
      "patientName": "PATIENT_'$i'",
      "patientAddress": "Address",
      "patientEmail": "test'$i'@mail.com",
      "counterSale": 1,
      "ordDate": "2026-04-05",
      "ordTime": "14:51:43",
      "userId": "user_'$i'",
      "actCode": "ACC001",
      "actName": "Account",
      "orderTotal": 100.00,
      "sysName": "TEST",
      "sysIp": "127.0.0.1",
      "sysUser": "tester",
      "materialInfo": [{"item_seq": 1, "item_code": "TEST001", "item_name": "Test", "batch_no": "B001", "expiry_date": "2027-04-05", "total_loose_qty": 5, "sale_rate": 20.00, "disc_per": 0.00, "sch_disc_per": 0.00}]
    }' &
done
wait

# Output: All 5 orders created with unique OrderIds
```

---

## Response Codes

### ✅ Success (200)
```json
{
    "code": "200",
    "type": "SaleOrderCreate",
    "message": "Document No. : 24001540035 successfully processed.",
    "documentDetails": [{
        "OrderId": "001202604051430AB12CD34",    ← Use this for tracking
        "documentPk": "24001540035"
    }]
}
```

### ⚠️ Validation Error (400)
```json
{
    "code": "400",
    "type": "SaleOrderCreate",
    "message": "Invalid parameters",
    "errors": {
        "patientEmail": ["Enter a valid email address"]
    }
}
```

### 🔴 ERP Service Unavailable (503)
```json
{
    "code": "503",
    "type": "SaleOrderCreate",
    "message": "ERP service temporarily unavailable"
}
```

### 🔴 Internal Server Error (500)
```json
{
    "code": "500",
    "type": "SaleOrderCreate",
    "message": "Error details"
}
```

---

## 🔑 Key Changes for Frontend Developers

### Before (Old Way - ❌)
```javascript
// Frontend generates ID
const orderId = Math.random() * 1000000;

fetch('/api/erp/create-sales-order/', {
    method: 'POST',
    body: JSON.stringify({
        orderId: orderId,      // ❌ Remove this
        c2Code: '03C000',
        ...
    })
});
```

### After (New Way - ✅)
```javascript
// Frontend sends order data WITHOUT orderId
fetch('/api/erp/create-sales-order/', {
    method: 'POST',
    body: JSON.stringify({
        // orderId: REMOVED - Backend generates it
        c2Code: '03C000',
        storeId: '001',
        patientName: 'ADITYA',
        ...
    })
})
.then(res => res.json())
.then(data => {
    const generatedOrderId = data.documentDetails[0].OrderId;
    console.log('Order created:', generatedOrderId);  // 001202604051430AB12CD34
});
```

---

## 📋 Validation Rules

### Required Fields
- ✅ c2Code (string, max 20)
- ✅ storeId (string, max 20)
- ✅ ipNo (string, max 100)
- ✅ mobileNo (string, max 15)
- ✅ patientName (string, max 255)
- ✅ patientAddress (string)
- ✅ patientEmail (valid email)
- ✅ counterSale (int: 0 or 1)
- ✅ ordDate (date format: YYYY-MM-DD)
- ✅ ordTime (time format: HH:MM:SS)
- ✅ userId (string, max 100)
- ✅ actCode (string, max 50)
- ✅ actName (string, max 255)
- ✅ orderTotal (decimal, max 12 digits)
- ✅ sysName (string, max 100)
- ✅ sysIp (valid IP address)
- ✅ sysUser (string, max 100)
- ✅ materialInfo (array with at least 1 item)

### Optional Fields
- orderDiscPer (decimal, default: 0)
- refNo (integer)
- remark (string)
- urgentFlag (0 or 1, default: 0)
- ordConversionFlag (0 or 1, default: 0)
- dcConversionFlag (0 or 1, default: 0)
- ordRefNo (integer, default: 0)
- drCode (string, max 50)
- drName (string, max 255)
- drAddress (string)
- drRegNo (string, max 50)
- drOfficeCode (string, max 50, default: "-")
- dmanCode (string, max 50, default: "-")

### Material Info Fields (per item)
- ✅ item_seq (integer)
- ✅ item_code (string)
- ✅ item_name (string)
- ✅ total_loose_qty (integer)
- ✅ sale_rate (decimal)
- batch_no (string, optional)
- expiry_date (date, optional)
- total_loose_sch_qty (integer, default: 0)
- service_qty (integer, default: 0)
- disc_per (decimal, default: 0)
- sch_disc_per (decimal, default: 0)

---

## 🧪 Testing Checklist

- [ ] Single order creation (backend generates ID)
- [ ] Multiple concurrent orders (all get unique IDs)
- [ ] Verify ID format: {storeId}{YYYYMMDD}{HHMMSS}{UUID}
- [ ] Check response includes generated OrderId
- [ ] Verify OrderId in response matches database
- [ ] Test with missing required fields (should get 400)
- [ ] Test with invalid email (should get 400)
- [ ] Verify transaction rollback on partial failure

---

## 📞 Support

For issues:
1. Check logs for `[ORDER_ID]`, `[ORDER_CREATED]`, `[ORDER_RETRY]` entries
2. Verify all required fields are present
3. Ensure dates/times are valid
4. Check storeId exists in ERP
