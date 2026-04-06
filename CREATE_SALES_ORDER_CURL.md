# Sales Order Creation - cURL Commands

**Endpoint:** `POST /api/erp/ws_c2_services_create_sale_order`

---

## 1️⃣ Minimal Example (Simplest)

```bash
curl -X POST http://localhost:8000/api/erp/ws_c2_services_create_sale_order \
  -H "Content-Type: application/json" \
  -d '{
    "c2Code": "03C000",
    "storeId": "001",
    "ipNo": "8237791693",
    "mobileNo": "8237791693",
    "patientName": "ADITYA",
    "patientAddress": "JP Nagar",
    "patientEmail": "aditya@mail.com",
    "counterSale": 1,
    "ordDate": "2026-04-06",
    "ordTime": "14:51:43",
    "userId": "rajath",
    "actCode": "GC01",
    "actName": "Lawrence Nadar",
    "orderTotal": 254.18,
    "sysName": "PHARMACY_POS",
    "sysIp": "172.16.18.11",
    "sysUser": "gajanan",
    "materialInfo": [
      {
        "item_seq": 1,
        "item_code": "PARA500",
        "item_name": "Paracetamol 500mg",
        "batch_no": "BATCH001",
        "expiry_date": "2027-04-06",
        "total_loose_qty": 20,
        "sale_rate": 10.00,
        "disc_per": 0.00,
        "sch_disc_per": 0.00
      }
    ]
  }'
```

---

## 2️⃣ Full Example (All Optional Fields)

```bash
curl -X POST http://localhost:8000/api/erp/ws_c2_services_create_sale_order \
  -H "Content-Type: application/json" \
  -d '{
    "c2Code": "03C000",
    "storeId": "001",
    "prodCode": "02",
    "ipNo": "8237791693",
    "mobileNo": "8237791693",
    "patientName": "ADITYA KUMAR",
    "patientAddress": "JP Nagar, Bangalore",
    "patientEmail": "aditya.kumar@mail.com",
    "counterSale": 1,
    "ordDate": "2026-04-06",
    "ordTime": "14:51:43",
    "userId": "rajath_001",
    "actCode": "GC01",
    "actName": "Lawrence Nadar Medical Store",
    "drCode": "GD01",
    "drName": "Dr. Prakash Sharma",
    "drAddress": "Medical Centre, Bangalore",
    "drRegNo": "12345",
    "drOfficeCode": "-",
    "dmanCode": "-",
    "orderTotal": 254.18,
    "orderDiscPer": 5.00,
    "refNo": 987,
    "remark": "Urgent delivery needed",
    "urgentFlag": 1,
    "ordConversionFlag": 0,
    "dcConversionFlag": 0,
    "ordRefNo": 0,
    "sysName": "PHARMACY_SYSTEM",
    "sysIp": "172.16.18.11",
    "sysUser": "gajanan",
    "materialInfo": [
      {
        "item_seq": 1,
        "item_code": "PARA500",
        "item_name": "Paracetamol 500mg",
        "batch_no": "BATCH001",
        "expiry_date": "2027-04-06",
        "total_loose_qty": 30,
        "total_loose_sch_qty": 0,
        "service_qty": 0,
        "sale_rate": 6.806,
        "disc_per": 0.00,
        "sch_disc_per": 0.00
      },
      {
        "item_seq": 2,
        "item_code": "ASP500",
        "item_name": "Aspirin 500mg",
        "batch_no": "BATCH002",
        "expiry_date": "2027-03-31",
        "total_loose_qty": 10,
        "total_loose_sch_qty": 5,
        "service_qty": 0,
        "sale_rate": 16.806,
        "disc_per": 1.00,
        "sch_disc_per": 0.00
      }
    ]
  }'
```

---

## 3️⃣ Save Response to File

```bash
curl -X POST http://localhost:8000/api/erp/ws_c2_services_create_sale_order \
  -H "Content-Type: application/json" \
  -d @payload.json \
  -o response.json
```

**payload.json:**
```json
{
  "c2Code": "03C000",
  "storeId": "001",
  "ipNo": "8237791693",
  "mobileNo": "8237791693",
  "patientName": "ADITYA",
  "patientAddress": "JP Nagar",
  "patientEmail": "aditya@mail.com",
  "counterSale": 1,
  "ordDate": "2026-04-06",
  "ordTime": "14:51:43",
  "userId": "rajath",
  "actCode": "GC01",
  "actName": "Lawrence Nadar",
  "orderTotal": 254.18,
  "sysName": "PHARMACY_POS",
  "sysIp": "172.16.18.11",
  "sysUser": "gajanan",
  "materialInfo": [
    {
      "item_seq": 1,
      "item_code": "PARA500",
      "item_name": "Paracetamol 500mg",
      "batch_no": "BATCH001",
      "expiry_date": "2027-04-06",
      "total_loose_qty": 20,
      "sale_rate": 10.00,
      "disc_per": 0.00,
      "sch_disc_per": 0.00
    }
  ]
}
```

---

## 4️⃣ Pretty Print Response

```bash
curl -X POST http://localhost:8000/api/erp/ws_c2_services_create_sale_order \
  -H "Content-Type: application/json" \
  -d '{"c2Code": "03C000", ...}' | python -m json.tool
```

---

## 5️⃣ Verbose Mode (Debug)

```bash
curl -v -X POST http://localhost:8000/api/erp/ws_c2_services_create_sale_order \
  -H "Content-Type: application/json" \
  -d '{"c2Code": "03C000", ...}'
```

---

## 6️⃣ With Headers & Timing

```bash
curl -w "\n\nTime: %{time_total}s\nStatus: %{http_code}\n" \
  -X POST http://localhost:8000/api/erp/ws_c2_services_create_sale_order \
  -H "Content-Type: application/json" \
  -H "User-Agent: Postman" \
  -d '{"c2Code": "03C000", ...}'
```

---

## 7️⃣ Test Multiple Orders (Concurrency Test)

```bash
#!/bin/bash

# Test 5 concurrent orders
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/erp/ws_c2_services_create_sale_order \
    -H "Content-Type: application/json" \
    -d "{
      \"c2Code\": \"03C000\",
      \"storeId\": \"001\",
      \"ipNo\": \"8237791693\",
      \"mobileNo\": \"8237791693\",
      \"patientName\": \"PATIENT_$i\",
      \"patientAddress\": \"JP Nagar\",
      \"patientEmail\": \"patient$i@mail.com\",
      \"counterSale\": 1,
      \"ordDate\": \"2026-04-06\",
      \"ordTime\": \"14:51:43\",
      \"userId\": \"rajath\",
      \"actCode\": \"GC01\",
      \"actName\": \"Lawrence Nadar\",
      \"orderTotal\": 254.18,
      \"sysName\": \"PHARMACY_POS\",
      \"sysIp\": \"172.16.18.11\",
      \"sysUser\": \"gajanan\",
      \"materialInfo\": [{
        \"item_seq\": 1,
        \"item_code\": \"PARA500\",
        \"item_name\": \"Paracetamol 500mg\",
        \"batch_no\": \"BATCH001\",
        \"expiry_date\": \"2027-04-06\",
        \"total_loose_qty\": 20,
        \"sale_rate\": 10.00,
        \"disc_per\": 0.00,
        \"sch_disc_per\": 0.00
      }]
    }" &
done
wait
echo "All orders completed"
```

Save as `create_concurrent_orders.sh` and run:
```bash
bash create_concurrent_orders.sh
```

---

## ✅ Expected Success Response

```json
{
  "code": "200",
  "type": "SaleOrderCreate",
  "message": "Document No. : 24001540035 successfully processed.",
  "documentDetails": [
    {
      "brCode": "001",
      "tranYear": "26",
      "tranPrefix": "6",
      "tranSrno": "1",
      "documentPk": "26001640035",
      "OrderId": "001202604061430AB12CD34",
      "createdDate": "2026-04-06",
      "billTotal": "254.18"
    }
  ]
}
```

**Important:** 
- ✅ **OrderId is auto-generated** (format: `{storeId}{YYYYMMDD}{HHMMSS}{UUID}`)
- ✅ **No need to send orderId** in request - remove it!
- ✅ **Use the returned OrderId** for tracking/queries

---

## ❌ Error Responses

### Missing Required Field
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

### ERP Service Down
```json
{
  "code": "503",
  "type": "SaleOrderCreate",
  "message": "ERP service temporarily unavailable"
}
```

### Server Error
```json
{
  "code": "500",
  "type": "SaleOrderCreate",
  "message": "Error creating order"
}
```

---

## 🐚 PowerShell Alternative

```powershell
$body = @{
    c2Code = "03C000"
    storeId = "001"
    ipNo = "8237791693"
    mobileNo = "8237791693"
    patientName = "ADITYA"
    patientAddress = "JP Nagar"
    patientEmail = "aditya@mail.com"
    counterSale = 1
    ordDate = "2026-04-06"
    ordTime = "14:51:43"
    userId = "rajath"
    actCode = "GC01"
    actName = "Lawrence Nadar"
    orderTotal = 254.18
    sysName = "PHARMACY_POS"
    sysIp = "172.16.18.11"
    sysUser = "gajanan"
    materialInfo = @(
        @{
            item_seq = 1
            item_code = "PARA500"
            item_name = "Paracetamol 500mg"
            batch_no = "BATCH001"
            expiry_date = "2027-04-06"
            total_loose_qty = 20
            sale_rate = 10.00
            disc_per = 0.00
            sch_disc_per = 0.00
        }
    )
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/erp/ws_c2_services_create_sale_order" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body
```

---

## 📝 Notes

- **Local testing**: Use `http://localhost:8000`
- **Production**: Replace with `https://your-domain.com`
- **Date format**: Always use `YYYY-MM-DD`
- **Time format**: Always use `HH:MM:SS` (24-hour)
- **OrderId**: Auto-generated - do NOT provide in request
- **Bearer token**: Not required (AllowAny permission)
