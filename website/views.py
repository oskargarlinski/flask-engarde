from flask import Blueprint, render_template, request, flash, session, redirect, url_for
from flask_login import login_required, current_user
from .models import Product, Category, ProductVariant, VariantOption, VariantValue, Order, OrderItem
from .forms import AddToCartForm, PaymentForm, ShippingForm, ReviewForm
from . import db

views = Blueprint('views', __name__)


@views.route('/')
def home():
    return render_template("home.html", active_page='home')


@views.route('/products', methods=['GET'])
def products(category_id=None):
    if category_id:
        # If category_id is provided, filter products by category
        products = Product.query.filter_by(category_id=category_id).all()
    else:
        # Otherwise, show all products
        products = Product.query.all()

    categories = Category.query.all()  # To display categories for filtering
    return render_template('products.html', products=products, categories=categories)


@views.route('/products/<int:product_id>', methods=['GET'])
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)

    variants = ProductVariant.query.filter_by(product_id=product.id).all()
    options = VariantOption.query.filter_by(product_id=product.id).all()

    option_values = {
        option.name: VariantValue.query.filter_by(option_id=option.id).all()
        for option in options
    }

    variant_data = []
    for variant in variants:
        variant_data.append({
            "id": variant.id,
            "sku": variant.sku,
            "price": variant.price,
            "environmental_impact": variant.environmental_impact,
            "stock": variant.stock,
            "values": [v.value for v in variant.values]
        })

    form = AddToCartForm()

    return render_template(
        'product_detail.html',
        product=product,
        variants=variants,
        option_values=option_values,
        form=form,
        variants_json=variant_data
    )


@views.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    form = AddToCartForm()
    if form.validate_on_submit():
        variant_id = int(form.variant_id.data)
        quantity = int(form.quantity.data)

        variant = ProductVariant.query.get_or_404(variant_id)
        if quantity > variant.stock:
            flash(f"Only {variant.stock} items left in stock!", "warning")
            return redirect(url_for('views.product_detail', product_id=variant.product_id))

        cart = session.get('cart', [])
        for item in cart:
            if item['variant_id'] == variant_id:
                if item['quantity'] + quantity > variant.stock:
                    flash(
                        f"Only {variant.stock} items left in stock!", "warning")
                    return redirect(url_for('views.product_detail', product_id=variant.product_id))
                item['quantity'] += quantity
                break
        else:
            cart.append({'variant_id': variant_id, 'quantity': quantity})

        session['cart'] = cart
        flash("Item added to cart!", "success")
        return redirect(url_for('views.view_cart'))

    flash("Invalid form submission", "danger")
    return redirect(request.referrer or url_for('views.home'))


@views.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    detailed_cart = []

    for item in cart:
        variant = ProductVariant.query.get(item['variant_id'])
        if variant:
            detailed_cart.append({
                'variant': variant,
                'quantity': item['quantity'],
                'subtotal': variant.price * item['quantity'],
                'impact': variant.environmental_impact * item['quantity']
            })

    total = sum(item['subtotal'] for item in detailed_cart)
    total_impact = sum(item['impact'] for item in detailed_cart)

    return render_template('cart.html', cart=detailed_cart, total=total, total_impact=total_impact)


@views.route('/update-cart', methods=['POST'])
def update_cart():
    variant_id = int(request.form.get('variant_id'))
    quantity = int(request.form.get('quantity', 1))
    action = request.form.get('action')
    cart = session.get('cart', [])

    updated_cart = []
    for item in cart:
        if item['variant_id'] == variant_id:
            if action == 'remove':
                continue
            elif action == 'update':
                variant = ProductVariant.query.get(variant_id)
                if not variant or quantity > variant.stock:
                    flash(
                        f"Only {variant.stock} in stock for {variant.product.name} ({variant.sku})", "warning")
                else:
                    item['quantity'] = quantity
        else:
            updated_cart.append(item)

    session['cart'] = updated_cart
    return redirect(url_for('views.view_cart'))


@views.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', [])
    step = request.values.get('step', 'shipping')

    # 1. Build detailed cart
    detailed_cart = []
    for item in cart:
        variant = ProductVariant.query.get(item['variant_id'])
        if variant:
            detailed_cart.append({
                'variant': variant,
                'quantity': item['quantity'],
                'subtotal': variant.price * item['quantity'],
                'impact': variant.environmental_impact * item['quantity']
            })
    total = sum(item['subtotal'] for item in detailed_cart)
    total_impact = sum(item['impact'] for item in detailed_cart)

    # 2. Step logic
    if step == 'shipping':
        form = ShippingForm()
        if form.validate_on_submit():
            session['checkout_shipping'] = form.data
            return redirect(url_for('views.checkout', step='payment'))
        return render_template("checkout.html", form=form, step='shipping', cart=detailed_cart, total=total, total_impact=total_impact)

    elif step == 'payment':
        form = PaymentForm()
        if form.validate_on_submit():
            session['checkout_payment'] = form.data
            return redirect(url_for('views.checkout', step='review'))
        return render_template("checkout.html", form=form, step='payment', cart=detailed_cart, total=total, total_impact=total_impact)

    elif step == 'review':
        form = ReviewForm()
        shipping = session.get('checkout_shipping', {})
        payment = session.get('checkout_payment', {})

        if form.validate_on_submit():
            # Create order
            order = Order(
                user_id=current_user.id,
                first_name=shipping['first_name'],
                last_name=shipping['last_name'],
                email=current_user.email,
                address=shipping['shipping_address'],
                city=shipping['city'],
                country=shipping['country'],
                postal_code=shipping['postal_code'],
                total_price=total,
                total_impact=total_impact
            )
            db.session.add(order)
            db.session.flush()

            for item in cart:
                variant = ProductVariant.query.get(item['variant_id'])
                print("Variant ID:", item['variant_id'])
                print("Requested:", item.get('quantity'))
                print("In Stock:", variant.stock if variant else "Not Found")
                if not variant or item['quantity'] > variant.stock:
                    flash("Stock error. Please review your cart.", "danger")
                    return redirect(url_for('views.view_cart'))
                variant.stock -= item['quantity']
                db.session.add(OrderItem(
                    order_id=order.id,
                    variant_id=variant.id,
                    quantity=item['quantity'],
                    price=variant.price,
                    impact=variant.environmental_impact
                ))

            db.session.commit()
            session.pop('cart', None)
            session.pop('checkout_shipping', None)
            session.pop('checkout_payment', None)
            flash("Order placed successfully!", "success")
            return redirect(url_for('views.home'))

        return render_template("checkout.html", form=form, step='review', cart=detailed_cart, total=total, total_impact=total_impact)

@views.route('/clear-session')
def clear_session():
    session.clear()
    return redirect(url_for('views.home'))