from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, session, current_app
from flask_login import current_user
from .models import Product, VariantOption, VariantValue, ProductVariant, VariantCombination, Category, Order, User
from .forms import BaseProductForm, AdminProductForm, VariantOptionForm, ProductVariantForm, WizardVariantsForm, CategoryForm, RuleWizardForm
from . import db
from werkzeug.utils import secure_filename
from itertools import product as cartesian_product
from functools import wraps
import os
import random
import string


admin = Blueprint('admin', __name__)

category_prefixes = {"Foils": "FOIL", "Épées": "EPEE", "Sabres": "SABR", "Practice Weapons": "PRCWPN", "Weapon Parts": "WPNPRT", "Masks": "MASK", "Gloves": "GLV", "Chest Protectors": "CHSTPROT", "Plastrons": "PLSTRN", "Jackets": "JACKT", "Breeches": "BRCH",
                     "Lames": "LAME", "Socks": "SOCK", "Shoes": "SHOE", "Body Cords": "CORD", "Scoring Equipment": "SCORE", "Weapon Bags": "WPNBAG", "Roll Bags": "ROLLBAG", "Backpacks": "BACKPACK", "Tools": "TOOL", "Tape": "TAPE", "Testers": "TESTER", "Miscellaneous": "MISC"}


def slugify_name(name):
    words = name.strip().upper().split()
    if len(words) == 1:
        return words[0][:3]
    else:
        return ''.join(word[0] for word in words)


def shorten_value(value):
    mapping = {"Left": "L", "Right": "R", "Extra Small": "XS",
               "Small": "S", "Medium": "M", "Large": "L", "Extra Large": "XL"}

    return mapping.get(value.strip().title(), value[:3].upper())


def generate_string_combo_sku(product, combo_list):
    category_code = product.category.slug.upper() if product.category and product.category.slug else "GEN"
    name_part = slugify_name(product.name)
    combo_short = '-'.join(shorten_value(val) for val in combo_list)

    random_suffix = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=4))

    if combo_short:
        return f"{category_code}-{name_part}-{combo_short}-{random_suffix}"
    else:
        return f"{category_code}-{name_part}-{random_suffix}"


def generate_simple_sku(product_name, category):
    prefix = category.slug.upper() if category and category.slug else "GEN"
    name_part = slugify_name(product_name)

    random_suffix = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=4))

    return f"{prefix}-{name_part}-{random_suffix}"


def get_category_tree(parent_id=None, depth=0):
    categories = Category.query.filter_by(
        parent_id=parent_id).order_by(Category.name).all()
    results = []

    for cat in categories:
        results.append((cat, depth))

        results += get_category_tree(parent_id=cat.id, depth=depth+1)

    return results


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin.route('/admin/products', endpoint='products')
@admin_required
def list_products():
    products = Product.query.all()
    return render_template('admin/admin_products.html', products=products)


@admin.route('/admin/products/<int:product_id>/delete', methods=['POST', 'GET'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.image_filename and product.image_filename != 'default-product.webp':
        image_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'], product.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

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


@admin.route('/admin/products/simple/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_simple_product(id):
    product = Product.query.get_or_404(id)
    if product.is_variant_parent:
        abort(404)

    form = AdminProductForm(obj=product)
    form.category.choices = [(c.id, c.name)
                             for c in Category.query.all()]
    form.category.data = product.category_id

    if form.validate_on_submit():
        if form.image.data:
            # Delete old image if it exists and isn't the default
            if product.image_filename and product.image_filename != 'default-product.webp':
                old_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], product.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)

            # Save new image
            filename = secure_filename(form.image.data.filename)
            image_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            form.image.data.save(image_path)
            product.image_filename = filename

        product.name = form.name.data
        product.description = form.description.data
        product.category_id = form.category.data
        product.price = form.price.data
        product.environmental_impact = form.environmental_impact.data
        product.stock = form.stock.data
        db.session.commit()
        flash("Product updated!", "success")
        return redirect(url_for('admin.products'))

    return render_template('admin/edit_simple_product.html', form=form, product=product)


@admin.route('/admin/variant-product/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_variant_product(id):
    product = Product.query.get_or_404(id)
    if not product.is_variant_parent:
        flash("This product does not have variants.", "warning")
        return redirect(url_for("admin.products"))

    form = BaseProductForm(obj=product)
    form.category.choices = [(c.id, c.name)
                             for c in Category.query.order_by(Category.name).all()]

    variants = ProductVariant.query.filter_by(product_id=product.id).all()
    variant_forms = []

    if request.method == 'POST':
        if form.validate_on_submit():
            # Update main product info
            product.name = form.name.data
            product.description = form.description.data
            product.category_id = form.category.data

            if form.image.data:
                # Delete old image if it exists and isn't the default
                if product.image_filename and product.image_filename != 'default-product.webp':
                    old_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'], product.image_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                # Save new image
                filename = secure_filename(form.image.data.filename)
                image_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename)
                form.image.data.save(image_path)
                product.image_filename = filename

            # Update variant info
            for i, variant in enumerate(variants):
                variant_form = ProductVariantForm(request.form, prefix=f"v{i}")
                if variant_form.validate():
                    variant.price = variant_form.price.data
                    variant.environmental_impact = variant_form.environmental_impact.data
                    variant.stock = variant_form.stock.data
                    db.session.add(variant)
                variant_forms.append((variant_form, variant))

            db.session.commit()
            flash("Product and variants updated!", "success")
            return redirect(url_for("admin.products"))
        else:
            flash("Please correct errors before saving", "danger")

    else:
        for i, variant in enumerate(variants):
            variant_form = ProductVariantForm(obj=variant, prefix=f"v{i}")
            variant_forms.append((variant_form, variant))

    return render_template("admin/edit_variant_product.html", form=form, product=product, variant_forms=variant_forms)


@admin.route('/admin/product_wizard/step1', methods=['GET', 'POST'])
@admin_required
def wizard_step1():
    form = AdminProductForm()
    form.category.choices = [(c.id, c.name) for c in Category.query.all()]

    if 'new_product' in session:
        wizard_data = session['new_product']
        form.name.data = wizard_data.get('name', '')
        form.description.data = wizard_data.get('description', '')
        form.category.data = wizard_data.get('category_id', None)
        form.is_variant_parent.data = wizard_data.get(
            'is_variant_parent', True)
        form.price.data = wizard_data.get('price', None)
        form.stock.data = wizard_data.get('stock', 0)
        form.environmental_impact.data = wizard_data.get(
            'environmental_impact', None)

    if form.validate_on_submit():
        image_filename = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            image_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            form.image.data.save(image_path)
            image_filename = filename

        session['new_product'] = {
            "name": form.name.data,
            "description": form.description.data,
            "category_id": form.category.data,
            "is_variant_parent": form.is_variant_parent.data,
            "price": form.price.data,
            "stock": form.stock.data,
            "environmental_impact": form.environmental_impact.data,
            "image_filename": image_filename
        }
        # If it's variant-based, go to step2; else skip straight to final
        if form.is_variant_parent.data:
            return redirect(url_for('admin.wizard_step2'))
        else:
            return redirect(url_for('admin.wizard_finish'))

    return render_template('admin/wizard_step1.html', form=form)


@admin.route('/admin/product_wizard/step2', methods=['GET', 'POST'])
@admin_required
def wizard_step2():
    wizard_data = session.get('new_product')
    if not wizard_data or not wizard_data.get('is_variant_parent'):
        flash("No variant product in progress.", "warning")
        return redirect(url_for('admin.products'))

    form = VariantOptionForm()
    if form.validate_on_submit():
        options_list = []
        for entry in form.options.entries:
            name = entry.form.option_name.data.strip()
            if name:
                options_list.append({"name": name})
        wizard_data['options'] = options_list
        session['new_product'] = wizard_data

        return redirect(url_for('admin.wizard_step3'))

    return render_template('admin/wizard_step2.html', form=form)


@admin.route('/admin/product_wizard/step3', methods=['GET', 'POST'])
@admin_required
def wizard_step3():
    wizard_data = session.get('new_product')
    if not wizard_data or not wizard_data.get('is_variant_parent'):
        flash("No variant product in progress.", "warning")
        return redirect(url_for('admin.products'))

    from .forms import WizardStep3Form
    form = WizardStep3Form()

    # On GET, build subforms for each option
    if request.method == 'GET':
        # Clear any existing entries
        form.options.entries = []
        for opt in wizard_data['options']:
            # Append a new subform
            entry = form.options.append_entry()
            # Store the option's name in the hidden field
            entry.option_name.data = opt['name']
            # We won't set values_str here; the user will type them in
        return render_template('admin/wizard_step3.html', form=form)

    # On POST, validate
    if form.validate_on_submit():
        # Build dictionary { "Size": ["S","M","L"], "Color": ["Red","Blue"] }
        option_values = {}
        for subform in form.options.entries:
            name = subform.option_name.data  # e.g. "Size"
            values_str = subform.values_str.data  # e.g. "S, M, L"
            # split
            values_list = [v.strip()
                           for v in values_str.split(',') if v.strip()]
            option_values[name] = values_list

        # Store in wizard session data
        wizard_data['option_values'] = option_values
        session['new_product'] = wizard_data

        return redirect(url_for('admin.wizard_step3_5'))

    # If form fails validation (bad data, blank, etc.)
    flash("Please correct the errors before proceeding.", "danger")
    return render_template('admin/wizard_step3.html', form=form)


@admin.route('/admin/product_wizard/step3_5', methods=['GET', 'POST'])
@admin_required
def wizard_step3_5():
    wizard_data = session.get('new_product')
    if not wizard_data or not wizard_data.get('is_variant_parent'):
        flash("No variant product in progress.", "warning")
        return redirect(url_for('admin.products'))

    option_names = list(wizard_data['option_values'].keys())
    option_value_map = wizard_data['option_values']

    # For POST: count submitted entries early and apply to the form class
    if request.method == 'POST':
        rule_fields = [k for k in request.form if k.startswith(
            'pricing_rules-') and k.endswith('-match_conditions')]
        mod_fields = [k for k in request.form if k.startswith(
            'modifiers-') and k.endswith('-value_name')]

        RuleWizardForm.pricing_rules.min_entries = len(rule_fields)
        RuleWizardForm.modifiers.min_entries = len(mod_fields)

    form = RuleWizardForm()

    # Dynamically populate dropdown choices for each rule/modifier
    for rule_entry in form.pricing_rules:
        rule_entry.option_name.choices = [(o, o) for o in option_names]
        selected_option = rule_entry.option_name.data or option_names[0]
        rule_entry.option_value.choices = [
            (v, v) for v in option_value_map.get(selected_option, [])]

    for mod_entry in form.modifiers:
        mod_entry.option_name.choices = [(o, o) for o in option_names]
        selected_option = mod_entry.option_name.data or option_names[0]
        mod_entry.option_value.choices = [
            (v, v) for v in option_value_map.get(selected_option, [])]

    if request.method == 'POST':
        if form.validate_on_submit():
            wizard_data['pricing_rules'] = [
                entry.data for entry in form.pricing_rules]
            wizard_data['modifiers'] = [entry.data for entry in form.modifiers]
            session['new_product'] = wizard_data
            return redirect(url_for('admin.wizard_step4'))
        else:
            flash("Please correct errors before continuing.", "danger")
            print("Form Errors:", form.errors)

    return render_template("admin/wizard_step3_5.html", form=form, option_value_map=option_value_map)


@admin.route('/admin/product_wizard/step4', methods=['GET', 'POST'])
@admin_required
def wizard_step4():
    wizard_data = session.get('new_product')
    if not wizard_data or not wizard_data.get('is_variant_parent'):
        flash("No variant product in progress.", "warning")
        return redirect(url_for('admin.products'))

    option_names = [o['name'] for o in wizard_data['options']]
    value_lists = [wizard_data['option_values'][name] for name in option_names]
    combos = list(cartesian_product(*value_lists))

    form = WizardVariantsForm()

    if request.method == "GET":
        def match_combo(combo_dict, condition_string):
            conds = [c.strip() for c in condition_string.split(',')]
            for cond in conds:
                if '=' not in cond:
                    continue
                key, val = cond.split('=')
                if combo_dict.get(key.strip()) != val.strip():
                    return False
            return True

        form.variants.entries = []

        for combo in combos:
            combo_dict = dict(zip(option_names, combo))
            combo_str = ",".join(combo)

            # Defaults
            price = 0.0
            impact = 0.0
            stock = 0

            # Base pricing rules
            for rule in wizard_data.get('pricing_rules', []):
                if match_combo(combo_dict, rule['match_conditions']):
                    price = rule['base_price']
                    impact = rule['base_impact']
                    stock = rule['stock']
                    break

            # Apply modifiers
            for mod in wizard_data.get('modifiers', []):
                if '=' not in mod['value_name']:
                    continue
                key, val = mod['value_name'].split('=')
                if combo_dict.get(key.strip()) == val.strip():
                    price += mod.get('price_modifier', 0) or 0
                    impact += mod.get('impact_modifier', 0) or 0
                    stock += mod.get('stock_modifier', 0) or 0  # ✅ New line

            # Fill form entry
            subform = form.variants.append_entry()
            subform = form.variants[-1]
            subform.combo_str.data = combo_str
            subform.price.data = round(price, 2)
            subform.environmental_impact.data = round(impact, 2)
            subform.stock.data = stock

        return render_template("admin/wizard_step4.html", form=form, combos=combos, option_names=option_names)

    if request.method == "POST":
        if form.validate_on_submit():
            variants_data = []
            for i, entry in enumerate(form.variants.entries):
                combo_str = entry.combo_str.data
                price_val = entry.price.data
                env_val = entry.environmental_impact.data
                stock_val = entry.stock.data

                combo_list = [x.strip() for x in combo_str.split(',')]

                variants_data.append({
                    "combo": combo_list,
                    "price": price_val,
                    "environmental_impact": env_val,
                    "stock": stock_val
                })

            wizard_data['variants'] = variants_data
            session['new_product'] = wizard_data

            return redirect(url_for('admin.wizard_finish'))

        else:
            flash("Please correct the errors before saving.", "danger")
            return render_template("admin/wizard_step4.html", form=form, combos=combos, option_names=option_names)

@admin.route('/admin/product_wizard/finish', methods=['GET', 'POST'])
@admin_required
def wizard_finish():
    from .models import Product, VariantOption, VariantValue, ProductVariant, VariantCombination
    wizard_data = session.get('new_product')
    if not wizard_data:
        flash("No product wizard in progress.", "danger")
        return redirect(url_for('admin.products'))

    product = Product(
        name=wizard_data['name'],
        description=wizard_data['description'],
        category_id=wizard_data['category_id'],
        is_variant_parent=wizard_data['is_variant_parent'],
        price=wizard_data['price'] if not wizard_data['is_variant_parent'] else None,
        stock=wizard_data['stock'] if not wizard_data['is_variant_parent'] else None,
        environmental_impact=wizard_data['environmental_impact'] if not wizard_data['is_variant_parent'] else None,
        image_filename=wizard_data['image_filename']
    )
    db.session.add(product)
    db.session.flush()

    if product.is_variant_parent:
        for opt in wizard_data.get('options', []):
            option_obj = VariantOption(product_id=product.id, name=opt['name'])
            db.session.add(option_obj)
            db.session.flush()

            values_for_opt = wizard_data['option_values'].get(opt['name'], [])
            for val in values_for_opt:
                vval = VariantValue(option_id=option_obj.id, value=val)
                db.session.add(vval)
        db.session.flush()

        from collections import defaultdict
        name_value_to_id = defaultdict(dict)
        for opt in VariantOption.query.filter_by(product_id=product.id).all():
            for val in opt.values:
                name_value_to_id[opt.name][val.value] = val.id

        variants_data = wizard_data.get('variants', [])
        for var_dict in variants_data:
            new_var = ProductVariant(
                product_id=product.id,
                price=var_dict['price'],
                environmental_impact=var_dict['environmental_impact'],
                stock=var_dict['stock'],
                sku=generate_string_combo_sku(product, var_dict['combo'])
            )
            db.session.add(new_var)
            db.session.flush()

            # Link variant with each value in combo
            combo = var_dict['combo']
            for i, val_str in enumerate(combo):
                option_name = wizard_data['options'][i]['name']
                val_id = name_value_to_id[option_name][val_str]
                vc = VariantCombination(variant_id=new_var.id, value_id=val_id)
                db.session.add(vc)
        db.session.flush()

    else:
        product.sku = generate_simple_sku(product.name, product.category)
        db.session.add(product)
        db.session.flush()

    # 4. Commit final
    db.session.commit()

    # 5. Clear wizard data
    session.pop('new_product', None)

    flash("Product successfully created!", "success")
    return redirect(url_for('admin.products'))


@admin.route('/admin/product_wizard/cancel')
@admin_required
def wizard_cancel():
    session.pop('new_product', None)
    flash("Product creation canceled. Nothing was saved.", "info")
    return redirect(url_for('admin.products'))


@admin.route("admin/categories", methods=["GET"])
@admin_required
def admin_list_categories():
    cat_tree = get_category_tree(parent_id=None, depth=0)
    return render_template("admin/admin_categories.html", cat_tree=cat_tree)


@admin.route("admin/categories/new", methods=["GET", "POST"])
@admin_required
def admin_new_category():
    form = CategoryForm()

    top_option = [(0, "No parent")]
    existing_cats = Category.query.all()
    sub_options = []
    for c in existing_cats:
        sub_options.append((c.id, c.name))

    form.parent_id.choices = top_option + sub_options

    if form.validate_on_submit():
        parent_id = form.parent_id.data
        if parent_id == 0:
            parent_id = None

        cat = Category(
            parent_id=parent_id,
            name=form.name.data,
            slug=form.slug.data
        )

        db.session.add(cat)
        db.session.commit()
        flash("Category created!", "success")
        return redirect(url_for("admin.admin_list_categories"))

    return render_template("admin/category_form.html", form=form)


@admin.route("admin/category/<int:cat_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    form = CategoryForm(obj=cat)

    top_option = [(0, "No parent")]
    existing_cats = Category.query.filter(Category.id != cat.id).all()
    sub_options = [(c.id, c.name) for c in existing_cats]
    form.parent_id.choices = top_option + sub_options

    if request.method == "GET":
        form.parent_id.data = cat.parent_id if cat.parent_id else 0

    if form.validate_on_submit():
        chosen_parent = form.parent_id.data
        if chosen_parent == 0:
            chosen_parent = None
        cat.parent_id = chosen_parent
        cat.name = form.name.data
        cat.slug = form.slug.data
        db.session.commit()
        flash("Category Updated!", "success")
        return redirect(url_for("admin.admin_list_categories"))

    return render_template("admin/category_form.html", form=form, category=cat)


@admin.route("admin/category/<int:cat_id>/delete", methods=["POST"])
@admin_required
def admin_delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)

    if cat.children or cat.products:
        flash("Cannot delete a category that has subcategories or products!", "danger")
        return redirect(url_for('admin.admin_list_categories'))

    def delete_subtree(category):
        for child in category.children:
            delete_subtree(child)

        for product in category.products:
            db.session.delete(product)

        db.session.delete(category)

    delete_subtree(cat)
    db.session.commit()
    flash("Category (and any subcategories) deleted! ", "success")

    return redirect(url_for('admin.admin_list_categories'))


@admin.route('admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/admin_orders.html', orders=orders)


@admin.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')


@admin.route('/admin/users')
@admin_required
def admin_users():
    search = request.args.get('search', '').strip()
    users = User.query
    if search:
        users = users.filter(User.email.ilike(f"%{search}"))
    users = users.order_by(User.email).all()
    return render_template('admin/admin_users.html', users=users)


@admin.route('/admin/users/<int:user_id>/promote', methods=['POST'])
@admin_required
def promote_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash(f"{user.email} promoted to admin.", "success")
    return redirect(url_for('admin.admin_users'))


@admin.route('/admin/users/<int:user_id>/demote', methods=['POST'])
@admin_required
def demote_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot demote yourself.", "danger")
        return redirect(url_for('admin.admin_users'))

    user.is_admin = False
    db.session.commit()
    flash(f"{user.email} is no longer an admin.", "warning")
    return redirect(url_for('admin.admin_users'))


@admin.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete yourself.", "danger")
        return redirect(url_for('admin.admin_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.email} deleted.", "danger")
    return redirect(url_for('admin.admin_users'))
