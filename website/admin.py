from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from .models import Weapon, Apparel, Footwear, Glove
from .forms import WeaponForm, ApparelForm, FootwearForm, GloveForm
from . import db
import os
from flask import current_app
from werkzeug.utils import secure_filename

admin = Blueprint('admin', __name__)

product_models = {
    'weapon': Weapon,
    'apparel': Apparel,
    'footwear': Footwear,
    'glove': Glove
}

product_forms = {
    'weapon': WeaponForm,
    'apparel': ApparelForm,
    'footwear': FootwearForm,
    'glove': GloveForm
}


def get_model_and_form(product_type):
    model = product_models.get(product_type)
    form_class = product_forms.get(product_type)

    if not model or not form_class:
        abort(404)

    return model, form_class


@admin.route('/admin/products')
def manage_products():
    products = {
        'weapon': Weapon.query.all(),
        'apparel': Apparel.query.all(),
        'glove': Glove.query.all(),
        'footwear': Footwear.query.all()
    }

    return render_template('admin/products.html', products=products)


@admin.route('/admin/products/add/<product_type>', methods=['GET', 'POST'])
def add_product(product_type):
    model, FormClass = get_model_and_form(product_type)
    form = FormClass()

    if form.validate_on_submit():
        image_file = form.image.data
        filename = None

        if image_file:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        product = model(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            environmental_impact=form.environmental_impact.data,
            image_filename=filename
        )

        if product_type == 'weapon':
            product.blade_type = form.blade_type.data
            product.certification = form.certification.data

        if product_type == 'footwear':
            product.size = form.size.data

        if product_type == 'glove':
            product.size = form.size.data
            product.hand_orientation = form.hand_orientation.data
            product.certification = form.certification.data

        if product_type == 'apparel':
            product.size = form.size.data
            product.material = form.material

        db.session.add(product)
        db.session.commit()
        flash(f"{product_type.title()} added successfully!", "success")
        return redirect(url_for('admin.manage_products'))

    return render_template('admin/add_product.html', form=form, product_type=product_type)


@admin.route('/admin/products/edit/<product_type>/<int:id>')
def edit_weapon(id):
    weapon = Weapon.query.get_or_404(id)
    form = WeaponForm(obj=weapon)  # Pre-fill form

    if form.validate_on_submit():
        weapon.name = form.name.data
        weapon.description = form.description.data
        weapon.price = form.price.data
        weapon.environmental_impact = form.environmental_impact.data
        weapon.blade_type = form.blade_type.data
        weapon.certification = form.certification.data

        # handle image upload
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            image_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], filename)
            form.image.data.save(image_path)
            weapon.image_filename = filename

        db.session.commit()
        flash("Weapon updated successfully!", "success")
        return redirect(url_for('admin.manage_products'))

    return render_template('admin/edit_weapon.html', form=form, weaxpon=weapon)


@admin.route('/admin/products/delete/<product_type>/<int:id>')
def delete_weapon(id):
    weapon = Weapon.query.get_or_404(id)

    # Optional: also remove image file from disk
    if weapon.image_filename:
        try:
            os.remove(os.path.join(
                current_app.config['UPLOAD_FOLDER'], weapon.image_filename))
        except FileNotFoundError:
            pass

    db.session.delete(weapon)
    db.session.commit()
    flash("Weapon deleted.", "info")
    return redirect(url_for('admin.manage_products'))
