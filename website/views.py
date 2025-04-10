from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from .models import Product, Category, ProductVariant, VariantOption, VariantValue, VariantCombination
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

    # Get all variant options and their values
    options = VariantOption.query.filter_by(product_id=product.id).all()
    for option in options:
        option.values = VariantValue.query.filter_by(option_id=option.id).all()

    # Build a list of variant dictionaries (for JS)
    variant_data = []
    variants = ProductVariant.query.filter_by(product_id=product.id).all()
    for variant in variants:
        combo_values = VariantCombination.query.filter_by(
            variant_id=variant.id).all()
        value_ids = [vc.value_id for vc in combo_values]

        variant_data.append({
            'id': variant.id,
            'sku': variant.sku,
            'price': float(variant.price),
            'environmental_impact': float(variant.environmental_impact),
            'value_ids': value_ids  # used in JS to match the variant
        })

    return render_template(
        'product_detail.html',
        product=product,
        options=options,
        variants=variant_data
    )
