from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from .models import Product, VariantOption, VariantValue, ProductVariant, VariantCombination, Category
from .forms import BaseProductForm, VariantOptionForm, ProductVariantForm
from . import db
from itertools import product as cartesian_product
import os
import re
from flask import current_app
from werkzeug.utils import secure_filename
from sqlalchemy.sql import func

admin = Blueprint('admin', __name__)


def find_variant_by_combination(product_id, combo):
    # Get all variant IDs for this product
    variant_ids = db.session.query(ProductVariant.id).filter_by(
        product_id=product_id).subquery()

    # Count how many of those variants have exactly the values in combo
    matching_variants = (
        db.session.query(ProductVariant)
        .join(VariantCombination, ProductVariant.id == VariantCombination.variant_id)
        .filter(VariantCombination.value_id.in_([v.id for v in combo]))
        .filter(ProductVariant.product_id == product_id)
        .group_by(ProductVariant.id)
        .having(func.count(VariantCombination.value_id) == len(combo))
        .all()
    )

    return matching_variants[0] if matching_variants else None

# Shorten value for SKU readability


def shorten_value(value):
    mapping = {
        "Left": "L",
        "Right": "R",
        "Medium": "M",
        "Small": "S",
        "Large": "L",
        "Extra Large": "XL",
        "Extra Small": "XS"
    }
    return mapping.get(value.strip().title(), value[:3].upper())

# Slugify product name
def slugify_name(name):
    words = name.strip().upper().split()
    return words[0][:3] if len(words) == 1 else ''.join(word[0] for word in words)


# Map of category names to SKU prefixes
category_prefixes = {
    "Foils": "FOI",
    "Épées": "EPE",
    "Sabres": "SBR",
    "Practice Weapons": "PRC",
    "Weapon Parts": "WPT",
    "Masks & Accessories": "MSK",
    "Gloves": "GLV",
    "Chest Protectors": "CHG",
    "Plastrons": "PLS",
    "Jackets": "JKT",
    "Breeches": "BRH",
    "Lames": "LAM",
    "Socks": "SOC",
    "Shoes": "SHO",
    "Body Cords": "BDC",
    "Electric Blades": "ELB",
    "Electric Weapons": "ELW",
    "Scoring Equipment": "SCR",
    "Weapon Bags": "WBG",
    "Roll Bags": "RBG",
    "Backpacks": "BKP",
    "Tools & Maintenance": "TLS",
    "Tape": "TAP",
    "Testers": "TST",
    "Miscellaneous": "MSC",
}


def generate_auto_sku(product, combo):
    category_code = category_prefixes.get(product.category.name, "GEN")
    product_slug = slugify_name(product.name)
    variant_values = '-'.join(shorten_value(v.value) for v in combo)

    return f"{category_code}-{product_slug}-{variant_values}"


@admin.route('/admin/products/new', methods=['GET', 'POST'])
def new_product():
    form = BaseProductForm()
    form.category.choices = [(c.id, c.name)
                             for c in Category.query.order_by(Category.name).all()]

    if form.validate_on_submit():
        filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename))

        product = Product(
            name=form.name.data,
            description=form.description.data,
            image_filename=filename,
            category_id=form.category.data,
            is_variant_parent=True
        )
        db.session.add(product)
        db.session.commit()
        flash("Product created. Now define variant options.", "success")
        return redirect(url_for('admin.add_variant_options', product_id=product.id))

    return render_template('admin/new_product.html', form=form)


@admin.route('/admin/products/<int:product_id>/options', methods=['GET', 'POST'])
def add_variant_options(product_id):
    product = Product.query.get_or_404(product_id)
    form = VariantOptionForm()

    if form.validate_on_submit():
        print("Form submitted")
        for entry in form.options.entries:
            print("Received:", entry.form.option_name.data)   # Debug line
            name = entry.form.option_name.data.strip()
            if name:
                option = VariantOption(name=name, product_id=product.id)
                db.session.add(option)
        db.session.commit()
        flash("Variant options saved. Now define values for each option.", "success")
        return redirect(url_for('admin.add_variant_values', product_id=product.id))
    else:
        print("Form not submitted or failed validation.")
        print(form.errors)

    return render_template('admin/add_variant_options.html', form=form, product=product)


@admin.route('/admin/products/<int:product_id>/values', methods=['GET', 'POST'])
def add_variant_values(product_id):
    product = Product.query.get_or_404(product_id)
    options = VariantOption.query.filter_by(product_id=product.id).all()

    if not options:
        flash("No variant options found for this product.", "warning")
        return redirect(url_for('admin.add_variant_options', product_id=product.id))

    if request.method == 'POST':
        for option in options:
            values_str = request.form.get(f"option-{option.id}-values", "")
            values = [v.strip() for v in values_str.split(',') if v.strip()]
            for value in values:
                db.session.add(VariantValue(option_id=option.id, value=value))
        db.session.commit()
        flash("Variant values saved! Now proceed to defining combinations.", "success")
        # Redirect to Step 4 (will be rebuilt later)
        return redirect(url_for('admin.products'))

    return render_template("admin/add_variant_values.html", product=product, options=options)


@admin.route('/admin/products', endpoint='products')
def list_products():
    products = Product.query.all()
    return render_template('admin/admin_products.html', products=products)


@admin.route('/admin/products/<int:product_id>/variants', methods=['GET', 'POST'])
def add_product_variants(product_id):
    product = Product.query.get_or_404(product_id)
    options = VariantOption.query.filter_by(product_id=product.id).all()

    value_lists = [
        VariantValue.query.filter_by(option_id=opt.id).all()
        for opt in options
    ]

    combinations = list(cartesian_product(*value_lists))
    variant_forms = []

    # Fetch all existing variants and combinations
    existing_variants = ProductVariant.query.filter_by(
        product_id=product.id).all()
    existing_combos_map = {
        tuple(sorted(vc.value_id for vc in variant.combinations)): variant
        for variant in existing_variants
    }

    current_combo_keys = set(tuple(v.id for v in combo)
                             for combo in combinations)

    if request.method == 'POST':
        # Delete old variants that no longer match
        for combo_key, variant in existing_combos_map.items():
            if combo_key not in current_combo_keys:
                VariantCombination.query.filter_by(
                    variant_id=variant.id).delete()
                db.session.delete(variant)

        db.session.commit()  # Commit deletions first

        # Now handle the new/updated variants
        for i, combo in enumerate(combinations):
            form = ProductVariantForm(request.form, prefix=str(i))
            if form.validate():
                combo_key = tuple(v.id for v in combo)
                existing_variant = existing_combos_map.get(combo_key)

                if existing_variant:
                    existing_variant.price = form.price.data
                    existing_variant.environmental_impact = form.environmental_impact.data
                else:
                    auto_sku = generate_auto_sku(product, combo)
                    new_variant = ProductVariant(
                        product_id=product.id,
                        sku=auto_sku,
                        price=form.price.data,
                        environmental_impact=form.environmental_impact.data,
                        stock = form.stock.data
                    )
                    db.session.add(new_variant)
                    db.session.flush()

                    for value in combo:
                        db.session.add(VariantCombination(
                            variant_id=new_variant.id,
                            value_id=value.id
                        ))
            else:
                print(f"Form {i} failed validation:", form.errors)

        db.session.commit()
        flash("All variants updated!", "success")
        return redirect(url_for('admin.products'))

    # GET: prepare forms
    for i, combo in enumerate(combinations):
        combo_key = tuple(sorted(v.id for v in combo))
        form = ProductVariantForm(prefix=str(i))

        existing_variant = existing_combos_map.get(combo_key)
        if existing_variant:
            form.price.data = existing_variant.price
            form.environmental_impact.data = existing_variant.environmental_impact
            form.sku.data = existing_variant.sku
            form.stock.data = existing_variant.stock if existing_variant else 0
        else:
            form.sku.data = generate_auto_sku(product, combo)

        variant_forms.append((form, combo))

    return render_template("admin/add_product_variants.html", product=product, variant_forms=variant_forms)


@admin.route('/admin/products/<int:product_id>/delete', methods=['POST', 'GET'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    # Delete related VariantCombinations and ProductVariants
    variants = ProductVariant.query.filter_by(product_id=product.id).all()
    for variant in variants:
        VariantCombination.query.filter_by(variant_id=variant.id).delete()
    ProductVariant.query.filter_by(product_id=product.id).delete()

    # Delete variant values and options
    options = VariantOption.query.filter_by(product_id=product.id).all()
    for option in options:
        VariantValue.query.filter_by(option_id=option.id).delete()
    VariantOption.query.filter_by(product_id=product.id).delete()

    # Finally delete the product itself
    db.session.delete(product)
    db.session.commit()
    flash("Product and all associated data deleted.", "success")
    return redirect(url_for('admin.products'))


@admin.route('/admin/seed-categories')
def seed_categories():
    from .models import Category
    existing = Category.query.first()
    if existing:
        flash("Categories already seeded.", "info")
        return redirect(url_for('admin.products'))

    categories = [
        Category(name="Foils", slug="foils"),
        Category(name="Épées", slug="epees"),
        Category(name="Sabres", slug="sabres"),
        Category(name="Practice Weapons", slug="practice-weapons"),
        Category(name="Weapon Parts", slug="weapon-parts"),

        Category(name="Masks & Accessories", slug="masks"),
        Category(name="Gloves", slug="gloves"),
        Category(name="Chest Protectors", slug="chest-protectors"),
        Category(name="Plastrons", slug="plastrons"),

        Category(name="Jackets", slug="jackets"),
        Category(name="Breeches", slug="breeches"),
        Category(name="Lames", slug="lames"),
        Category(name="Socks", slug="socks"),
        Category(name="Shoes", slug="shoes"),

        Category(name="Body Cords", slug="body-cords"),
        Category(name="Electric Blades", slug="electric-blades"),
        Category(name="Electric Weapons", slug="electric-weapons"),
        Category(name="Scoring Equipment", slug="scoring-equipment"),

        Category(name="Weapon Bags", slug="weapon-bags"),
        Category(name="Roll Bags", slug="roll-bags"),
        Category(name="Backpacks", slug="backpacks"),

        Category(name="Tools & Maintenance", slug="tools"),
        Category(name="Tape", slug="tape"),
        Category(name="Testers", slug="testers"),
        Category(name="Miscellaneous", slug="misc"),
    ]

    db.session.add_all(categories)
    db.session.commit()
    flash("Default categories seeded successfully!", "success")
    return redirect(url_for('admin.products'))
