from flask import Blueprint, render_template, request, flash, session, redirect, url_for, abort
from flask_login import login_required, current_user
from .models import Product, Category, ProductVariant, VariantOption, VariantValue, Order, OrderItem
from .forms import AddToCartForm, PaymentForm, ShippingForm, ReviewForm
from . import db

views = Blueprint('views', __name__)


def build_category_tree(parent_id=None):
    categories = Category.query.filter_by(
        parent_id=parent_id).order_by(Category.name).all()

    tree = []
    for cat in categories:
        node = {
            'category': cat,
            'children': build_category_tree(cat.id)
        }

        tree.append(node)

    return tree


def get_all_descendants(cat_id):
    to_visit = [cat_id]
    visited = set()
    while to_visit:
        current_id = to_visit.pop()
        visited.add(current_id)
        children = Category.query.filter_by(parent_id=current_id).all()
        for child in children:
            if child.id not in visited:
                to_visit.append(child.id)

    return visited

def get_variant_label(variant):
    if not variant or not variant.values:
        return ""
    return ",".join(v.value for v in variant.values)

def effective_price(p):
    if p.is_variant_parent and p.variants:
        return min(v.price for v in p.variants)
    return p.price or float('inf')

def effective_impact(p):
    if p.is_variant_parent and p.variants:
        return min(v.environmental_impact for v in p.variants if v.environmental_impact is not None)
    return p.environmental_impact or float('inf')

@views.route('/')
def home():
    sort = request.args.get('sort', 'default')
    products = Product.query.all()

    if sort == 'price':
        products.sort(key=effective_price)
    elif sort == 'impact':
        products.sort(key=effective_impact)
    elif sort == 'name':
        products.sort(key=lambda p: p.name.lower())

    return render_template('home.html', products=products, sort=sort)

@views.route('/product-info/<int:product_id>')
def product_info(product_id):
    product = Product.query.get_or_404(product_id)
    return {
        'name': product.name,
        'description': product.description
    }

@views.route('/products')
def products():
    cat_id = request.args.get('cat_id', type=int)
    search_query = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'default')
    selected_category = None
    query = Product.query

    if cat_id:
        cat_ids = get_all_descendants(cat_id)
        selected_category = Category.query.get(cat_id)
        query = Product.query.filter(Product.category_id.in_(cat_ids))
    elif search_query:
        query = query.filter(Product.name.ilike(f"%{search_query}%"))
    else:
        query = Product.query

    products = query.all()

    if sort == 'price_asc':
        products.sort(key=effective_price)
    elif sort == 'price_desc':
        products.sort(key=lambda p: -effective_price(p))
    elif sort == 'impact_asc':
        products.sort(key=effective_impact)
    elif sort == 'impact_desc':
        products.sort(key=lambda p: -effective_impact(p))
    elif sort == 'name_asc':
        products.sort(key=lambda p: p.name.lower())

    category_tree = build_category_tree(parent_id=None)

    return render_template(
        'products.html',
        products=products,
        category_tree=category_tree,
        cat_id=cat_id,
        sort=sort,
        selected_category=selected_category,
        search_query=search_query
    )


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
    print("Form data:", form.data)
    if not form.validate_on_submit():
        flash("Invalid form submission", "danger")
        return redirect(request.referrer or url_for('views.home'))

    quantity = int(form.quantity.data)
    cart = session.get('cart', [])

    variant_id_raw = form.variant_id.data
    product_id_raw = form.product_id.data

    # Variant product
    if variant_id_raw and str(variant_id_raw).isdigit():
        variant_id = int(variant_id_raw)
        variant = ProductVariant.query.get_or_404(variant_id)

        if quantity > variant.stock:
            flash(f"Only {variant.stock} items left in stock!", "warning")
            return redirect(url_for("views.product_detail", product_id=variant.product_id))

        for item in cart:
            if item.get("variant_id") == variant.id:
                if item['quantity'] + quantity > variant.stock:
                    flash(
                        f"Only {variant.stock} items left in stock!", "warning")
                    return redirect(url_for('views.product_detail', product_id=variant.product_id))
                item['quantity'] += quantity
                break
        else:
            cart.append({'variant_id': variant.id, 'quantity': quantity})

    # Simple product
    elif product_id_raw and str(product_id_raw).isdigit():
        product_id = int(product_id_raw)
        product = Product.query.get_or_404(product_id)

        if product.stock is not None and quantity > product.stock:
            flash(f"Only {product.stock} items left in stock!", "warning")
            return redirect(url_for("views.product_detail", product_id=product.id))

        for item in cart:
            if item.get("product_id") == product.id:
                if product.stock is not None and item['quantity'] + quantity > product.stock:
                    flash(
                        f"Only {product.stock} items left in stock!", "warning")
                    return redirect(url_for("views.product_detail", product_id=product.id))
                item['quantity'] += quantity
                break
        else:
            cart.append({'product_id': product.id, 'quantity': quantity})

    else:
        flash("Missing product or variant ID", "danger")
        return redirect(request.referrer or url_for('views.home'))

    session['cart'] = cart
    flash("Item added to cart!", "success")
    return redirect(url_for("views.view_cart"))


@views.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    detailed_cart = []

    for item in cart:
        if 'variant_id' in item:
            variant = ProductVariant.query.get(item['variant_id'])
            if variant:
                detailed_cart.append({
                    'variant': variant,
                    'quantity': item['quantity'],
                    'subtotal': variant.price * item['quantity'],
                    'impact': variant.environmental_impact * item['quantity'],
                    'options': get_variant_label(variant)
                })
        elif 'product_id' in item:
            product = Product.query.get(item['product_id'])
            if product:
                detailed_cart.append({
                    'product': product,
                    'quantity': item['quantity'],
                    'subtotal': product.price * item['quantity'],
                    'impact': (product.environmental_impact or 0) * item['quantity']
                })

    total = sum(item['subtotal'] for item in detailed_cart)
    total_impact = sum(item['impact'] for item in detailed_cart)

    return render_template('cart.html', cart=detailed_cart, total=total, total_impact=total_impact)


@views.route('/update-cart', methods=['POST'])
def update_cart():
    variant_id_raw = request.form.get('variant_id')
    product_id_raw = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    action = request.form.get('action')
    cart = session.get('cart', [])
    updated_cart = []

    for item in cart:
        # --- Variant-based product ---
        if variant_id_raw and 'variant_id' in item and str(item['variant_id']) == str(variant_id_raw):
            if action == 'remove':
                continue
            elif action == 'update':
                variant = ProductVariant.query.get(int(variant_id_raw))
                if not variant or quantity > variant.stock:
                    flash(
                        f"Only {variant.stock} in stock for {variant.product.name} ({variant.sku})", "warning")
                else:
                    item['quantity'] = quantity
            updated_cart.append(item)

        # --- Simple product ---
        elif product_id_raw and 'product_id' in item and str(item['product_id']) == str(product_id_raw):
            if action == 'remove':
                continue
            elif action == 'update':
                product = Product.query.get(int(product_id_raw))
                if not product or quantity > product.stock:
                    flash(
                        f"Only {product.stock} in stock for {product.name}", "warning")
                else:
                    item['quantity'] = quantity
            updated_cart.append(item)

        # --- Keep unrelated items ---
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
        if 'variant_id' in item:
            variant = ProductVariant.query.get(item['variant_id'])
            if variant:
                detailed_cart.append({
                    'variant': variant,
                    'quantity': item['quantity'],
                    'subtotal': variant.price * item['quantity'],
                    'impact': variant.environmental_impact * item['quantity'],
                    'options': get_variant_label(variant)
                })
        elif 'product_id' in item:
            product = Product.query.get(item['product_id'])
            if product:
                detailed_cart.append({
                    'product': product,
                    'quantity': item['quantity'],
                    'subtotal': product.price * item['quantity'],
                    'impact': (product.environmental_impact or 0) * item['quantity']
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
                total_impact=round(total_impact, 2)
            )
            db.session.add(order)
            db.session.flush()

            for item in cart:
                if 'variant_id' in item:
                    variant = ProductVariant.query.get(item['variant_id'])
                    if not variant or item['quantity'] > variant.stock:
                        flash("Stock error. Please review your cart.", "danger")
                        return redirect(url_for('views.view_cart'))
                    variant.stock -= item['quantity']
                    db.session.add(OrderItem(
                        order_id=order.id,
                        product_id=variant.product.id,
                        variant_id=variant.id,
                        quantity=item['quantity'],
                        price=variant.price,
                        impact=round(variant.environmental_impact *
                                     item['quantity'], 2)
                    ))
                elif 'product_id' in item:
                    product = Product.query.get(item['product_id'])
                    if not product or item['quantity'] > product.stock:
                        flash("Stock error. Please review your cart.", "danger")
                        return redirect(url_for('views.view_cart'))
                    product.stock -= item['quantity']
                    db.session.add(OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        variant_id=None,
                        quantity=item['quantity'],
                        price=product.price,
                        impact=round((product.environmental_impact or 0)
                                     * item['quantity'], 2)
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


@views.route('/orders')
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(
        Order.created_at.desc()).all()
    return render_template('order_history.html', orders=orders)


@views.route('orders/<int:order_id>/invoice')
@login_required
def download_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)

    return render_template("invoice.html", order=order)
