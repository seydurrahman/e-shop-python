# utils.py
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, F
from .models import Order, OrderItem, Product


def get_sales_metrics(days=30):
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # ---------------------
    # Daily sales
    # ---------------------
    daily_orders = (
        Order.objects.filter(created_at__range=(start_date, end_date))
        .filter(paid=True)
        .order_by("created_at")
    )

    daily_sales = {}
    for order in daily_orders:
        date_str = order.created_at.date().isoformat()
        daily_sales.setdefault(
            date_str, {"date": date_str, "total_sales": 0, "orders_count": 0}
        )
        daily_sales[date_str]["total_sales"] += order.get_total_cost()
        daily_sales[date_str]["orders_count"] += 1
    daily_sales = list(daily_sales.values())

    # ---------------------
    # Monthly sales (last 12 months)
    # ---------------------
    monthly_orders = Order.objects.filter(paid=True).order_by("created_at")
    monthly_sales = {}
    for order in monthly_orders:
        month_str = order.created_at.strftime("%Y-%m")
        monthly_sales.setdefault(
            month_str, {"month": month_str, "total_sales": 0, "orders_count": 0}
        )
        monthly_sales[month_str]["total_sales"] += order.get_total_cost()
        monthly_sales[month_str]["orders_count"] += 1
    # sort descending and take last 12 months
    monthly_sales = sorted(
        monthly_sales.values(), key=lambda x: x["month"], reverse=True
    )[:12]

    # ---------------------
    # Total metrics
    # ---------------------
    paid_orders = Order.objects.filter(paid=True)
    total_revenue = sum(o.get_total_cost() for o in paid_orders)
    total_orders = paid_orders.count()
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    total_metrics = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_order_value": avg_order_value,
    }

    # ---------------------
    # Order distribution
    # ---------------------
    total_orders_all = Order.objects.count()
    paid_count = Order.objects.filter(paid=True).count()
    pending_count = Order.objects.filter(status="pending").count()
    canceled_count = Order.objects.filter(status="canceled").count()

    order_distribution = {
        "paid": paid_count,
        "pending": pending_count,
        "canceled": canceled_count,
    }

    # ---------------------
    # Top-selling products
    # ---------------------
    top_products_qs = (
        OrderItem.objects.values("product__name")
        .annotate(quantity=Sum("quantity"))
        .order_by("-quantity")[:5]
    )
    top_products = [
        {"product": p["product__name"], "quantity": p["quantity"]}
        for p in top_products_qs
    ]

    return {
        "daily_sales": daily_sales,
        "monthly_sales": monthly_sales,
        "total_metrics": total_metrics,
        "order_distribution": order_distribution,
        "top_products": top_products,
    }
