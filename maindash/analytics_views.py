"""
Store-wise Financial Analytics API
Income / Expense / Revenue breakdown per store
Uses: SalesOrder, SalesOrderItem, Invoice, InvoiceDetail,
      WalletTransaction, CreditNote, Store models
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class StoreFinancialAnalyticsView(APIView):
    """
    GET /api/admin/analytics/stores/
    
    Returns income / expense / revenue / order stats per store.
    
    Query params:
      period   : today | week | month | quarter | year | custom  (default: month)
      date_from: YYYY-MM-DD  (required when period=custom)
      date_to  : YYYY-MM-DD  (required when period=custom)
      store_id : int          (optional — filter to one store)
      group_by : day | week | month  (default: month)
    
    Data sources:
      Revenue  → Invoice.doc_total  (confirmed billed amount)
      Income   → SalesOrder.order_total (gross order value placed)
      Discount → InvoiceDetail discount amounts (expense side)
      Wallet   → WalletTransaction DEBIT = expense (credits given out)
      Returns  → CreditNote APPROVED amounts (expense)
      Tax      → cgst+sgst+igst amounts from InvoiceDetail
    """
    permission_classes = [IsAuthenticated]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _date_range(self, period, date_from=None, date_to=None):
        today = timezone.now().date()
        if period == "today":
            return today, today
        if period == "week":
            return today - timedelta(days=6), today
        if period == "month":
            return today.replace(day=1), today
        if period == "quarter":
            q_start_month = ((today.month - 1) // 3) * 3 + 1
            return today.replace(month=q_start_month, day=1), today
        if period == "year":
            return today.replace(month=1, day=1), today
        if period == "custom" and date_from and date_to:
            from datetime import datetime
            try:
                return (
                    datetime.strptime(date_from, "%Y-%m-%d").date(),
                    datetime.strptime(date_to, "%Y-%m-%d").date(),
                )
            except ValueError:
                pass
        # default: current month
        return today.replace(day=1), today

    def _zero(self):
        return Decimal("0.00")

    # ------------------------------------------------------------------
    # main GET
    # ------------------------------------------------------------------
    def get(self, request):
        if request.user.role != "SUPERADMIN":
            return Response(
                {"success": False, "message": "SuperAdmin only"},
                status=status.HTTP_403_FORBIDDEN,
            )

        period   = request.query_params.get("period", "month")
        date_from = request.query_params.get("date_from")
        date_to   = request.query_params.get("date_to")
        store_filter = request.query_params.get("store_id")
        group_by  = request.query_params.get("group_by", "month")

        start_date, end_date = self._date_range(period, date_from, date_to)

        # ── Import models from dreamspharmaapp ──────────────
        from dreamspharmaapp.models import (
            Store, SalesOrder, SalesOrderItem,
            Invoice, InvoiceDetail,
            WalletTransaction, CreditNote,
        )

        # ── Active stores ─────────────────────────────────────────────
        stores_qs = Store.objects.filter(is_active=True)
        if store_filter:
            stores_qs = stores_qs.filter(id=store_filter)

        all_stores = list(stores_qs)

        # ── Date filter for orders ────────────────────────────────────
        order_date_filter = Q(
            ord_date__gte=start_date,
            ord_date__lte=end_date,
        )

        invoice_date_filter = Q(
            doc_date__gte=start_date,
            doc_date__lte=end_date,
        )

        # ── Build per-store breakdown ─────────────────────────────────
        stores_data = []
        total_revenue     = self._zero()
        total_income      = self._zero()
        total_discounts   = self._zero()
        total_wallet_out  = self._zero()
        total_returns     = self._zero()
        total_tax         = self._zero()
        total_orders      = 0
        total_confirmed   = 0

        for store in all_stores:
            # Orders for this store
            orders = SalesOrder.objects.filter(
                order_date_filter,
                fulfilling_store=store,
            )

            order_count      = orders.count()
            confirmed_count  = orders.filter(ord_conversion_flag=True).count()
            delivered_count  = orders.filter(dc_conversion_flag=True).count()
            pending_count    = orders.filter(
                ord_conversion_flag=False,
                dc_conversion_flag=False
            ).count()

            # Gross income = sum of all order totals placed
            income_agg = orders.aggregate(
                gross=Sum("order_total"),
                billed=Sum("bill_total"),
            )
            gross_income  = income_agg["gross"]  or self._zero()
            billed_income = income_agg["billed"] or self._zero()

            # Revenue = sum of invoiced doc_total (confirmed revenue)
            invoices = Invoice.objects.filter(
                invoice_date_filter,
                sales_order__fulfilling_store=store,
            )
            revenue_agg = invoices.aggregate(total=Sum("doc_total"))
            revenue = revenue_agg["total"] or self._zero()

            # Discounts + Tax from invoice line items
            details = InvoiceDetail.objects.filter(
                invoice__in=invoices
            )
            detail_agg = details.aggregate(
                disc_amt    = Sum("disc_amt"),
                cgst_amt    = Sum("cgst_amt"),
                sgst_amt    = Sum("sgst_amt"),
                igst_amt    = Sum("igst_amt"),
                cess_amt    = Sum("cess_amt"),
            )
            discounts = detail_agg["disc_amt"]  or self._zero()
            tax = (
                (detail_agg["cgst_amt"] or self._zero()) +
                (detail_agg["sgst_amt"] or self._zero()) +
                (detail_agg["igst_amt"] or self._zero()) +
                (detail_agg["cess_amt"] or self._zero())
            )

            # Wallet debits = credits given to retailers (expense for business)
            wallet_out_agg = WalletTransaction.objects.filter(
                wallet__retailer__preferred_store=store,
                transaction_type="CREDIT",
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            ).aggregate(total=Sum("amount"))
            wallet_out = wallet_out_agg["total"] or self._zero()

            # Credit note returns (approved = confirmed expense)
            returns_agg = CreditNote.objects.filter(
                store=store,
                status="APPROVED",
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            ).aggregate(total=Sum("amount"))
            returns = returns_agg["total"] or self._zero()

            # Net profit = Revenue − Discounts − Wallet credits − Returns
            net_profit = revenue - discounts - wallet_out - returns

            # Average order value
            avg_order = (
                gross_income / order_count
                if order_count > 0
                else self._zero()
            )

            # Top selling items for this store (by qty)
            top_items = (
                SalesOrderItem.objects
                .filter(sales_order__in=orders)
                .values("item_code", "item_name")
                .annotate(total_qty=Sum("total_loose_qty"), total_value=Sum("item_total"))
                .order_by("-total_qty")[:5]
            )

            # Trend data (orders grouped by period)
            trunc_fn = {
                "day":   TruncDay,
                "week":  TruncWeek,
                "month": TruncMonth,
            }.get(group_by, TruncMonth)

            trend = (
                orders
                .annotate(period_label=trunc_fn("ord_date"))
                .values("period_label")
                .annotate(
                    order_count=Count("id"),
                    revenue=Sum("order_total"),
                )
                .order_by("period_label")
            )

            store_row = {
                "store_id":        store.id,
                "store_name":      store.name,
                "erp_store_id":    store.store_id,
                "erp_c2_code":     store.c2_code,
                "city":            store.city,
                "state":           store.state,
                # ── Order stats ──
                "total_orders":    order_count,
                "confirmed_orders": confirmed_count,
                "delivered_orders": delivered_count,
                "pending_orders":  pending_count,
                "avg_order_value": str(round(avg_order, 2)),
                # ── Financial ──
                "gross_income":    str(round(gross_income, 2)),
                "billed_income":   str(round(billed_income, 2)),
                "revenue":         str(round(revenue, 2)),
                "discounts_given": str(round(discounts, 2)),
                "wallet_credits_given": str(round(wallet_out, 2)),
                "returns_amount":  str(round(returns, 2)),
                "tax_collected":   str(round(tax, 2)),
                "net_profit":      str(round(net_profit, 2)),
                # ── Top items ──
                "top_items": [
                    {
                        "item_code":   t["item_code"],
                        "item_name":   t["item_name"] or t["item_code"],
                        "total_qty":   t["total_qty"],
                        "total_value": str(round(t["total_value"] or 0, 2)),
                    }
                    for t in top_items
                ],
                # ── Trend ──
                "trend": [
                    {
                        "period":      str(t["period_label"].date()) if hasattr(t["period_label"], "date") else str(t["period_label"]),
                        "orders":      t["order_count"],
                        "revenue":     str(round(t["revenue"] or 0, 2)),
                    }
                    for t in trend
                ],
            }

            stores_data.append(store_row)

            # Accumulate totals
            total_revenue    += revenue
            total_income     += gross_income
            total_discounts  += discounts
            total_wallet_out += wallet_out
            total_returns    += returns
            total_tax        += tax
            total_orders     += order_count
            total_confirmed  += confirmed_count

        # ── ERP store identification summary ─────────────────────────
        # Answers: "when GetItemMaster is called, which store's data is it?"
        erp_store_map = [
            {
                "store_id":     s.id,
                "store_name":   s.name,
                "erp_c2_code":  s.c2_code,
                "erp_store_id": s.store_id,
                "erp_prod_code":s.prod_code,
                "is_primary":   s.is_primary,
                "note": (
                    "Default fallback store — used when no GPS is sent"
                    if s.is_primary else
                    f"Selected when customer is near {s.city}"
                ),
            }
            for s in stores_qs
        ]

        return Response({
            "success": True,
            "period": {
                "label":      period,
                "start_date": str(start_date),
                "end_date":   str(end_date),
            },
            "summary": {
                "total_stores":       len(all_stores),
                "total_orders":       total_orders,
                "confirmed_orders":   total_confirmed,
                "total_gross_income": str(round(total_income, 2)),
                "total_revenue":      str(round(total_revenue, 2)),
                "total_discounts":    str(round(total_discounts, 2)),
                "total_wallet_credits": str(round(total_wallet_out, 2)),
                "total_returns":      str(round(total_returns, 2)),
                "total_tax":          str(round(total_tax, 2)),
                "total_net_profit":   str(round(
                    total_revenue - total_discounts - total_wallet_out - total_returns,
                    2
                )),
            },
            "stores": stores_data,
            # Answers the admin's question:
            # "When GetItemMaster is called without GPS, which store is it?"
            "erp_store_routing": erp_store_map,
        }, status=status.HTTP_200_OK)


class StoreItemMasterRoutingView(APIView):
    """
    GET /api/admin/analytics/store-routing/
    
    Shows admin exactly which ERP store is selected for a given
    GPS location — answers "which store's products am I seeing?"
    
    Query params:
      latitude  : float
      longitude : float
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "SUPERADMIN":
            return Response({"success": False, "message": "SuperAdmin only"}, status=403)

        from dreamspharmaapp.models import Store
        from dreamspharmaapp.store_manager import StoreLocationManager
        from dreamspharmaapp.erp_service import ERPService

        lat = request.query_params.get("latitude")
        lon = request.query_params.get("longitude")

        all_stores = Store.objects.filter(is_active=True).values(
            "id", "name", "city", "state", "c2_code", "store_id",
            "prod_code", "is_primary", "latitude", "longitude"
        )

        result = {
            "all_stores": list(all_stores),
            "selected_store": None,
            "selection_method": None,
        }

        if lat and lon:
            try:
                store_info = ERPService.get_nearest_store_config(float(lat), float(lon))
                result["selected_store"] = {
                    "store_db_id":  store_info["store_db_id"],
                    "store_name":   store_info["store_name"],
                    "distance_km":  store_info.get("distance_km"),
                    "erp_c2_code":  store_info["erp_config"]["c2_code"],
                    "erp_store_id": store_info["erp_config"]["store_id"],
                    "erp_prod_code":store_info["erp_config"]["prod_code"],
                }
                result["selection_method"] = "GPS nearest-store algorithm"
            except Exception as e:
                result["error"] = str(e)
        else:
            # Show which store is the fallback default
            primary = Store.objects.filter(is_active=True, is_primary=True).first()
            if primary:
                result["selected_store"] = {
                    "store_db_id":  primary.id,
                    "store_name":   primary.name,
                    "erp_c2_code":  primary.c2_code,
                    "erp_store_id": primary.store_id,
                    "erp_prod_code":primary.prod_code,
                }
                result["selection_method"] = "Default primary store (no GPS provided)"

        return Response({"success": True, "data": result})
