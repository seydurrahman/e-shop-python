from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import RegistrationForm, RatingForm, CheckoutForm
from .models import Category, Product, Cart, CartItem, Rating, Order, OrderItem
from django.db.models import Q, Min, Max, Avg
from django.contrib.auth.decorators import login_required
from .sslcommerz import (
    generate_sslcommerz_payment,
    send_order_confirmation_email,
    verify_sslcommerz_payment,
)
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

# Create your views here.


# Manual User Authentication
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Logged In Successful!")
            return redirect("profile")
        else:
            messages.error(request, "Invalid username or password")
    return render(request, "shop/login.html")


def register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(
                request, user, backend="django.contrib.auth.backends.ModelBackend"
            )  # ✅ fixed
            messages.success(request, "Registration Successful!")
            return redirect("profile")
    else:
        form = RegistrationForm()

    return render(request, "shop/register.html", {"form": form})


# def register_view(request):
#     if request.method == 'POST':
#         form = RegistrationForm(request.POST)

#         if form.is_valid():
#             user = form.save()
#             login(request, user)
#             messages.success(request, "Registration Successful!")
#             return redirect('profile')
#     else:
#         form = RegistrationForm()

#     return render(request, 'shop/register.html', {'form' : form})


def logout_view(request):
    logout(request)
    return redirect("login")


# homepage
def home(request):
    featured_products = Product.objects.filter(available=True).order_by("-created_at")[
        :8
    ]  # descending order
    categories = Category.objects.all()

    return render(
        request,
        "shop/home.html",
        {"featured_products": featured_products, "categories": categories},
    )


# product list page
def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        print("category .......", category)
        products = products.filter(category=category)

    min_price = products.aggregate(Min("price"))["price__min"]
    max_price = products.aggregate(Max("price"))["price__max"]

    if request.GET.get("min_price"):
        products = products.filter(price__gte=request.GET.get("min_price"))

    if request.GET.get("max_price"):
        products = products.filter(price__lte=request.GET.get("max_price"))

    if request.GET.get("rating"):
        min_rating = request.GET.get("rating")
        products = products.annotate(avg_rating=Avg("ratings__rating")).filter(
            avg_rating__gte=min_rating
        )
        # temp variable --> avg_rating
        # Avg
        # ratings related_name ke use kore rating model er rating value ke access korlam
        # avg_rating == user er filter kora rating er sathe

    if request.GET.get("search"):
        query = request.GET.get("search")
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )

    return render(
        request,
        "shop/product_list.html",
        {
            "category": category,
            "categories": categories,
            "products": products,
            "min_price": min_price,
            "max_price": max_price,
        },
    )


# product detail page
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    related_products = Product.objects.filter(category=product.category).exclude(
        id=product.id
    )

    user_rating = None

    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(product=product, user=request.user)
        except Rating.DoesNotExist:
            pass

    rating_form = RatingForm(instance=user_rating)

    return render(
        request,
        "shop/product_detail.html",
        {
            "product": product,
            "related_products": related_products,
            "user_rating": user_rating,
            "rating_form": rating_form,
        },
    )


# Rate Product
# logged in user, Purchase koreche kina
@login_required
def rate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    ordered_items = OrderItem.objects.filter(
        order__user=request.user, product=product, order__paid=True
    )

    if not ordered_items.exists():  # order kore nai
        messages.warning(request, "You can only rate products you have purchased!")
        return redirect("product_detail", slug=product.slug)

    try:
        rating = Rating.objects.get(product=product, user=request.user)
    except Rating.DoesNotExist:
        rating = None

    # jodi rating age diye thake tail rating form ager rating data diye fill up kora thakbe sekhtre instance = user rating hoye jbe
    # jodi rating na kora thake taile instance = None thakbe and se new rating create korte parbe
    if request.method == "POST":
        form = RatingForm(request.POST, instance=rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.product = product
            rating.user = request.user
            rating.save()
            return redirect("product_detail", slug=product.slug)
    else:
        form = RatingForm(instance=rating)

    return render(request, "shop/rate_product.html", {"form": form, "product": product})


# Everything about cart - feature
# cart detail --> temporary order - ok
# cart e item add - ok
# cart e item remove - ok
# cart e item update - ok
# checkout - ok


@login_required
def cart_detail(request):
    # user er kono cart nai
    # user er cart ache
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)

    return render(request, "shop/cart.html", {"cart": cart})


# cart add
@login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # User er cart ache kina

    # Exception handling
    # jodi thake taile oi cart ta check korbo
    try:  # ekahne error aste pare
        cart = Cart.objects.get(user=request.user)

    # jodi na thake, taile cart ekta banabo
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)

    # Cart e item add korbo
    # item already cart e ache
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        cart_item.quantity += 1
        cart_item.save()

    # item cart e nai
    except CartItem.DoesNotExist:
        CartItem.objects.create(cart=cart, product=product, quantity=1)

    messages.success(request, f"{product.name} has been added to your cart!")
    return redirect("product_detail", slug=product.slug)


# cart Update
# cart item quantity increase/decrease korte parbo
@login_required
def cart_update(request, product_id):
    # cart konta
    # cart er item konta
    # main product jeta cart item hisebe cart e ache

    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)

    quantity = int(request.POST.get("quantity", 1))

    # Keya saban -> stock e ache 20 ta product
    # user Keya saban -> 40 ta add to cart korche..
    # user Keya saban -> 5, 4, 3, 2, 1, 0 --> cartitem delete kore deoya lagbe

    if quantity <= 0:
        cart_item.delete()
        messages.success(request, f"{product.name} has been removed from your cart!")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f"Cart updated successfully!!")
    return redirect("cart_detail")


@login_required
def cart_remove(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)

    cart_item.delete()
    messages.success(request, f"{product.name} has been removed from your cart!")
    return redirect("cart_detail")


# 80% --> thinking
# 20% time --> coding


# checkout
# cart er data gula niye asbo
# ['first_name', 'last_name', 'email', 'address', 'postal_code', 'city','note']
# TOTAL TAKA --> 8000 TAKA
# Payment option --> Payment gateway te niye jabo


# Product --> Cart Item --> Order Item
@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            messages.warning(request, "Your cart is empty!")
            return redirect("cart_detail")
    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty!")
        return redirect("cart_detail")

    # Checkout form ta fill up korbe
    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(
                commit=False
            )  # form object create hobe kintu data database e jabe na
            order.user = request.user
            order.save()  # order kora hoye geche

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,  # cartitem e ekhn order item
                    price=item.product.price,  # product er main price e order item er main price
                    quantity=item.quantity,  # cart item er quantity e hocche order item er quantity
                )
            #  order kora done finally
            # cart er ar kono value e nai
            cart.items.all().delete()  # cart er item gula delete kore dilam
            request.session["order_id"] = order.id
            return redirect("payment_process")
    else:
        form = CheckoutForm()
    return render(request, "shop/checkout.html", {"cart": cart, "form": form})


# Payment Related Khela
# 0. Payment Process --> SSL Commerz er Window dekhabe, email confirmation pathano
# 1. Payment Success
# 2. Payment Fail
# 3. Payment Cancel


# 0. Payment Process
@login_required
def payment_process(request):
    # session
    order_id = request.session.get("order_id")
    if not order_id:
        return redirect("home")

    order = get_object_or_404(Order, id=order_id)
    payment_data = generate_sslcommerz_payment(request, order)

    if payment_data["status"] == "SUCCESS":
        return redirect(payment_data["GatewayPageURL"])
    else:
        messages.error(request, "Payment gateway error. Please Try again.")
        return redirect("checkout")


# 1. Payment Success
@csrf_exempt
def payment_success(request, order_id):
    """
    Handle payment success redirect/callback from SSLCommerz.
    This endpoint may be hit by the gateway (server-to-server) or by the user's browser.
    We do not require login here because gateway callbacks won't have the user's session.
    Instead we verify the transaction using SSLCommerz validation API before marking the order paid.
    """
    order = get_object_or_404(Order, id=order_id)

    # SSLCommerz typically returns a `val_id` which we can use to validate the transaction
    val_id = request.GET.get("val_id") or request.POST.get("val_id")

    verified = False
    if val_id:
        try:
            verified = verify_sslcommerz_payment(val_id, order.get_total_cost())
        except Exception as e:
            # In production log the exception
            print("Error verifying SSLCommerz payment:", e)

    # Only mark paid when verification succeeds
    if verified and not order.paid:
        order.paid = True
        order.status = "processing"
        order.transaction_id = order.id
        order.save()

        # decrement stock
        for item in order.order_items.all():
            product = item.product
            product.stock -= item.quantity
            if product.stock < 0:
                product.stock = 0
            product.save()

        # send confirmation email
        send_order_confirmation_email(order)

    # Render the success page for both browser redirects and gateway callbacks
    # If user is authenticated and owns the order they'll see the same page
    return render(request, "shop/payment_success.html", {"order": order})


@csrf_exempt
def payment_notify(request, order_id):
    """
    IPN / server-to-server notification endpoint for SSLCommerz.
    The gateway will POST `val_id` (and other params). We verify using the val_id
    and mark the order paid if verification succeeds.
    Returns plain 'OK' to acknowledge receipt.
    """
    order = get_object_or_404(Order, id=order_id)

    # prefer POST for IPN
    val_id = request.POST.get("val_id") or request.GET.get("val_id")
    if not val_id:
        # nothing to verify
        return HttpResponse("NO_VAL_ID", status=400)

    try:
        ok = verify_sslcommerz_payment(val_id, order.get_total_cost())
    except Exception as e:
        print("IPN verification failed:", e)
        return HttpResponse("ERROR", status=500)

    if ok and not order.paid:
        order.paid = True
        order.status = "processing"
        # transaction id may be provided as val_id or gateway tran_id; store val_id for trace
        order.transaction_id = val_id
        order.save()

        # decrement stock
        for item in order.order_items.all():
            product = item.product
            product.stock -= item.quantity
            if product.stock < 0:
                product.stock = 0
            product.save()

        # send confirmation email
        send_order_confirmation_email(order)

    # Acknowledge to gateway
    return HttpResponse("OK")


@csrf_exempt
def payment_fail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "canceled"
    order.save()
    return redirect("checkout")


@csrf_exempt
def payment_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "canceled"
    order.save()
    return redirect("cart_detail")


# profile page


@login_required
def profile(request):
    tab = request.GET.get("tab")
    orders = Order.objects.filter(user=request.user)
    completed_orders = orders.filter(status="delivered")
    total_spent = sum(order.get_total_cost() for order in orders)
    order_history_active = tab == "orders"  # true or false return korbe

    return render(
        request,
        "shop/profile.html",
        {
            "user": request.user,
            "orders": orders,
            "completed_orders": completed_orders,
            "total_spent": total_spent,
            "order_history_active": order_history_active,
        },
    )
