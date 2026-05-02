# Admin COD Delivery API

The Admin COD Delivery API is an endpoint for superadmins to mark Cash on Delivery (COD) orders as delivered and payment collected.

## Endpoint Details

- **Path:** `/api/superadmin/orders/cod-delivered/`
- **Method:** `POST`
- **Authentication:** Required (User must be authenticated and have the role `SUPERADMIN`)

## Request Payload

The API expects a JSON payload containing the following fields:

- `order_id` (string, **required**): The unique identifier of the sales order to be updated.
- `status` (string, **optional**, default: `"delivered"`): The new status for the COD order. Accepted values are:
    - `"paid"`
    - `"confirmed"`
    - `"delivered"`

### Example Request

```json
{
  "order_id": "ORD12345",
  "status": "delivered"
}
```

## Behavior and Actions

1.  **Authorization:** Verifies if the requesting user is a `SUPERADMIN`. If not, returns a `403 Forbidden` error.
2.  **Validation:**
    - Checks if `order_id` is present in the payload. If missing, returns a `400 Bad Request`.
    - Looks up the `SalesOrder` using the provided `order_id`. If not found, returns a `404 Not Found`.
    - Verifies that the order has an associated `Payment` record with `payment_method='COD'`. If not found, returns a `400 Bad Request`.
3.  **Status Updates:** Based on the requested `status` action:
    - **`paid`:**
        - Checks if payment is already collected. If so, returns a `400 Bad Request`.
        - Marks the payment as collected (`cod_collected = True`, sets `cod_collected_at`, `cod_collected_by`, and updates `payment.status` to `'SUCCESS'`).
        - Does *not* change the main order conversion flags.
    - **`confirmed`:**
        - Checks and collects payment if not already marked as collected.
        - Updates the order flag: `ord_conversion_flag = True`.
    - **`delivered` (Default):**
        - Checks and collects payment if not already marked as collected.
        - Updates order flags: both `dc_conversion_flag = True` and `ord_conversion_flag = True`.
4.  **Audit Logging:** Generates an audit log entry detailing the action performed, the user who performed it, the target `order_id`, and a descriptive message. The category is recorded as `'Order'`.

## Responses

### Success (200 OK)

```json
{
  "success": true,
  "message": "Marked COD Order \"ORD12345\" as delivered and payment collected successfully"
}
```

### Error Responses

- **403 Forbidden:** Only Super Admin can access this endpoint.
- **400 Bad Request:** `order_id` is required in the payload, no COD payment found, or COD payment already marked as collected (for 'paid' status).
- **404 Not Found:** Order not found.
