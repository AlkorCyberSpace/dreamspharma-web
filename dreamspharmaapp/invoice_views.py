import io
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

import logging
logger = logging.getLogger(__name__)

def _safe(val, default="-"):
    if val is None or str(val).strip() == "":
        return default
    return str(val)

def build_invoice_pdf(sales_order, invoice) -> bytes:
    """
    Build a simple Dreams Pharma invoice PDF.
    Returns raw bytes of the PDF.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
        title=f"Invoice {invoice.doc_no}",
    )

    story = []
    styles = getSampleStyleSheet()
    
    # Title
    story.append(Paragraph(f"<b>Dreams Pharma - Invoice</b>", styles['Title']))
    story.append(Spacer(1, 5 * mm))
    
    # Meta Info
    story.append(Paragraph(f"<b>Order ID:</b> {_safe(sales_order.order_id)}", styles['Normal']))
    story.append(Paragraph(f"<b>Invoice No:</b> {_safe(invoice.doc_no)}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {_safe(invoice.doc_date)}", styles['Normal']))
    story.append(Spacer(1, 5 * mm))
    
    # Billing Info
    story.append(Paragraph(f"<b>Billed To:</b> {_safe(sales_order.patient_name)}", styles['Normal']))
    story.append(Paragraph(f"<b>Phone:</b> {_safe(sales_order.mobile_no)}", styles['Normal']))
    story.append(Spacer(1, 10 * mm))

    # Items Table
    col_labels = ["#", "Product", "Batch", "Qty", "Rate", "Total"]
    tbl_data = [col_labels]
    
    details = list(invoice.details.all())
    subtotal = 0.0

    for idx, d in enumerate(details):
        item_total = float(d.item_total or 0)
        subtotal += item_total
        tbl_data.append([
            str(idx + 1),
            _safe(d.product_name),
            _safe(d.batch),
            _safe(d.qty),
            f"{float(d.sale_rate or 0):.2f}",
            f"{item_total:.2f}"
        ])

    table = Table(tbl_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A3C6E")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F4F6F9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 10 * mm))

    # Totals
    grand_total = float(invoice.doc_total or 0)
    story.append(Paragraph(f"<b>Subtotal:</b> {subtotal:.2f}", styles['Normal']))
    story.append(Paragraph(f"<b>Grand Total:</b> {grand_total:.2f}", styles['Heading3']))
    
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Thank you for your business!", styles['Normal']))

    doc.build(story)
    return buf.getvalue()

class InvoiceDownloadView(APIView):
    """
    Download invoice PDF for a completed order.

    GET /api/orders/<order_id>/invoice/
    GET /api/orders/<order_id>/invoice/?doc_no=001/25/S/105   (specific invoice)

    Returns: application/pdf  (inline or attachment based on ?download=1)
    """
    permission_classes = [AllowAny]

    def get(self, request, order_id):
        from .models import SalesOrder, Invoice

        # ── fetch sales order ────────────────────────────────────────────────
        try:
            sales_order = SalesOrder.objects.get(order_id=order_id)
        except SalesOrder.DoesNotExist:
            return Response(
                {"success": False, "message": f"Order '{order_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── fetch invoice ────────────────────────────────────────────────────
        doc_no = request.query_params.get("doc_no")
        try:
            if doc_no:
                invoice = Invoice.objects.get(sales_order=sales_order, doc_no=doc_no)
            else:
                invoice = Invoice.objects.filter(sales_order=sales_order).latest("created_at")
        except Invoice.DoesNotExist:
            # Try syncing from ERP if not stored locally
            logger.info(f"[INVOICE_DOWNLOAD] No local invoice for {order_id}, attempting ERP sync")
            try:
                from .services import sync_invoice_from_erp
                sync_invoice_from_erp(
                    order_id=order_id,
                    c2_code=sales_order.c2_code,
                    store_id=sales_order.store_id,
                    max_retries=3,
                )
                if doc_no:
                    invoice = Invoice.objects.get(sales_order=sales_order, doc_no=doc_no)
                else:
                    invoice = Invoice.objects.filter(sales_order=sales_order).latest("created_at")
            except Exception:
                return Response(
                    {
                        "success": False,
                        "message": "Invoice not available yet. Please try again in a moment.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        # ── generate PDF ─────────────────────────────────────────────────────
        try:
            pdf_bytes = build_invoice_pdf(sales_order, invoice)
        except Exception as e:
            logger.error(f"[INVOICE_PDF_ERROR] order={order_id} err={e}", exc_info=True)
            return Response(
                {"success": False, "message": "Failed to generate invoice PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── return as PDF response ────────────────────────────────────────────
        safe_doc_no = invoice.doc_no.replace("/", "-").replace(" ", "_")
        filename = f"invoice_{safe_doc_no}.pdf"

        disposition = "attachment" if request.query_params.get("download") else "inline"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Content-Length"] = len(pdf_bytes)
        return response
