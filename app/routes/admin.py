from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Vehicle, Driver, Department
from app.forms import UserForm, VehicleForm, DriverForm, DepartmentForm
from werkzeug.security import generate_password_hash
from functools import wraps # <-- Adicione esta importação

bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- Funções Auxiliares para Verificação de Gestor ---
def is_manager():
    """Verifica se o usuário logado é um gestor."""
    return current_user.is_authenticated and current_user.type == 'manager'


def manager_required(f):
    """Decorador para exigir que o usuário seja um gestor."""

    @login_required
    @wraps(f)  # <-- Adicione esta linha
    def decorated_function(*args, **kwargs):
        if not is_manager():
            flash('Acesso negado. Esta página é apenas para gestores.')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)

    return decorated_function

# --- Rotas de Gerenciamento de Usuários ---

@bp.route('/users')
@manager_required
def users():
    """
    Rota para listar e gerenciar usuários.
    """
    users = User.query.all()
    return render_template('admin/users.html', title='Gerenciar Usuários', users=users)

@bp.route('/users/add', methods=['GET', 'POST'])
@manager_required
def add_user():
    """
    Rota para adicionar um novo usuário.
    """
    form = UserForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Este nome de usuário já está em uso.')
            return render_template('admin/add_edit_user.html', title='Adicionar Usuário', form=form)

        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('Este e-mail já está em uso.')
            return render_template('admin/add_edit_user.html', title='Adicionar Usuário', form=form)

        user = User(
            username=form.username.data,
            email=form.email.data,
            type=form.type.data
        )
        user.password_hash = generate_password_hash(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Usuário {user.username} adicionado com sucesso!')
        return redirect(url_for('admin.users'))

    return render_template('admin/add_edit_user.html', title='Adicionar Usuário', form=form)

@bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@manager_required
def edit_user(user_id):
    """
    Rota para editar um usuário existente.
    """
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)

    # Se o formulário não foi submetido, preenche a senha com vazio para não exibir hash
    if request.method == 'GET':
        form.password.data = ''
        form.password2.data = ''

    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user and existing_user.id != user.id:
            flash('Este nome de usuário já está em uso.')
            return render_template('admin/add_edit_user.html', title='Editar Usuário', form=form, user=user)

        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email and existing_email.id != user.id:
            flash('Este e-mail já está em uso.')
            return render_template('admin/add_edit_user.html', title='Editar Usuário', form=form, user=user)

        user.username = form.username.data
        user.email = form.email.data
        user.type = form.type.data

        if form.password.data: # Atualiza senha apenas se uma nova for fornecida
            user.password_hash = generate_password_hash(form.password.data)

        db.session.commit()
        flash(f'Usuário {user.username} atualizado com sucesso!')
        return redirect(url_for('admin.users'))

    return render_template('admin/add_edit_user.html', title='Editar Usuário', form=form, user=user)

@bp.route('/users/delete/<int:user_id>', methods=['POST'])
@manager_required
def delete_user(user_id):
    """
    Rota para excluir um usuário.
    """
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Você não pode excluir seu próprio usuário.')
        return redirect(url_for('admin.users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário {user.username} excluído com sucesso!')
    return redirect(url_for('admin.users'))

# --- Rotas de Gerenciamento de Veículos ---

@bp.route('/vehicles')
@manager_required
def vehicles():
    """
    Rota para listar e gerenciar veículos.
    """
    vehicles = Vehicle.query.all()
    return render_template('admin/vehicles.html', title='Gerenciar Veículos', vehicles=vehicles)

@bp.route('/vehicles/add', methods=['GET', 'POST'])
@manager_required
def add_vehicle():
    """
    Rota para adicionar um novo veículo.
    """
    form = VehicleForm()
    if form.validate_on_submit():
        existing_vehicle = Vehicle.query.filter_by(plate=form.plate.data).first()
        if existing_vehicle:
            flash('Esta placa já está cadastrada.')
            return render_template('admin/add_edit_vehicle.html', title='Adicionar Veículo', form=form)

        vehicle = Vehicle(
            plate=form.plate.data,
            model=form.model.data,
            year=form.year.data,
            color=form.color.data,
            status=form.status.data,
            current_km=form.current_km.data,
            purchase_date=form.purchase_date.data,
            notes=form.notes.data
        )
        db.session.add(vehicle)
        db.session.commit()
        flash(f'Veículo {vehicle.plate} adicionado com sucesso!')
        return redirect(url_for('admin.vehicles'))

    return render_template('admin/add_edit_vehicle.html', title='Adicionar Veículo', form=form)

@bp.route('/vehicles/edit/<int:vehicle_id>', methods=['GET', 'POST'])
@manager_required
def edit_vehicle(vehicle_id):
    """
    Rota para editar um veículo existente.
    """
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = VehicleForm(obj=vehicle)

    if form.validate_on_submit():
        existing_vehicle = Vehicle.query.filter_by(plate=form.plate.data).first()
        if existing_vehicle and existing_vehicle.id != vehicle.id:
            flash('Esta placa já está cadastrada.')
            return render_template('admin/add_edit_vehicle.html', title='Editar Veículo', form=form, vehicle=vehicle)

        vehicle.plate = form.plate.data
        vehicle.model = form.model.data
        vehicle.year = form.year.data
        vehicle.color = form.color.data
        vehicle.status = form.status.data
        vehicle.current_km = form.current_km.data
        vehicle.purchase_date = form.purchase_date.data
        vehicle.notes = form.notes.data

        db.session.commit()
        flash(f'Veículo {vehicle.plate} atualizado com sucesso!')
        return redirect(url_for('admin.vehicles'))

    return render_template('admin/add_edit_vehicle.html', title='Editar Veículo', form=form, vehicle=vehicle)

@bp.route('/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@manager_required
def delete_vehicle(vehicle_id):
    """
    Rota para excluir um veículo.
    """
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    # TODO: Adicionar lógica para verificar se o veículo está em uso antes de excluir
    db.session.delete(vehicle)
    db.session.commit()
    flash(f'Veículo {vehicle.plate} excluído com sucesso!')
    return redirect(url_for('admin.vehicles'))

# --- Rotas de Gerenciamento de Motoristas ---

@bp.route('/drivers')
@manager_required
def drivers():
    """
    Rota para listar e gerenciar motoristas.
    """
    drivers = Driver.query.all()
    return render_template('admin/drivers.html', title='Gerenciar Motoristas', drivers=drivers)

@bp.route('/drivers/add', methods=['GET', 'POST'])
@manager_required
def add_driver():
    form = DriverForm()
    if form.validate_on_submit():
        # Verificar se já existe um motorista com a mesma CNH
        existing_driver = Driver.query.filter_by(license_number=form.license_number.data).first()
        if existing_driver:
            flash('Já existe um motorista com este número de CNH.', 'danger')
            return render_template('admin/add_edit_driver.html', title='Adicionar Motorista', form=form)

        driver = Driver(
            name=form.name.data,
            license_number=form.license_number.data,
            license_expiration=form.license_expiration.data,
            phone=form.phone.data,
            status=form.status.data,
            notes=form.notes.data
        )
        db.session.add(driver)
        db.session.commit()
        flash('Motorista adicionado com sucesso!', 'success')
        return redirect(url_for('admin.drivers'))
    return render_template('admin/add_edit_driver.html', title='Adicionar Motorista', form=form)


@bp.route('/drivers/edit/<int:driver_id>', methods=['GET', 'POST'])
@manager_required
def edit_driver(driver_id):
    """
    Rota para editar um motorista existente.
    """
    driver = Driver.query.get_or_404(driver_id)
    form = DriverForm(obj=driver)

    if form.validate_on_submit():
        existing_driver = Driver.query.filter_by(license_number=form.license_number.data).first()
        if existing_driver and existing_driver.id != driver.id:
            flash('Este número de CNH já está cadastrado.')
            return render_template('admin/add_edit_driver.html', title='Editar Motorista', form=form, driver=driver)

        driver.name = form.name.data
        driver.license_number = form.license_number.data
        driver.license_expiration = form.license_expiration.data
        driver.phone = form.phone.data
        driver.status = form.status.data
        driver.notes = form.notes.data

        db.session.commit()
        flash(f'Motorista {driver.name} atualizado com sucesso!')
        return redirect(url_for('admin.drivers'))

    return render_template('admin/add_edit_driver.html', title='Editar Motorista', form=form, driver=driver)

@bp.route('/drivers/delete/<int:driver_id>', methods=['POST'])
@manager_required
def delete_driver(driver_id):
    """
    Rota para excluir um motorista.
    """
    driver = Driver.query.get_or_404(driver_id)
    # TODO: Adicionar lógica para verificar se o motorista está em uso antes de excluir
    db.session.delete(driver)
    db.session.commit()
    flash(f'Motorista {driver.name} excluído com sucesso!')
    return redirect(url_for('admin.drivers'))

# --- Rotas de Gerenciamento de Departamentos ---

@bp.route('/departments')
@manager_required
def departments():
    """
    Rota para listar e gerenciar departamentos.
    """
    departments = Department.query.all()
    return render_template('admin/departments.html', title='Gerenciar Departamentos', departments=departments)

@bp.route('/departments/add', methods=['GET', 'POST'])
@manager_required
def add_department():
    """
    Rota para adicionar um novo departamento.
    """
    form = DepartmentForm()
    if form.validate_on_submit():
        existing_department = Department.query.filter_by(name=form.name.data).first()
        if existing_department:
            flash('Este nome de departamento já está em uso.')
            return render_template('admin/add_edit_department.html', title='Adicionar Departamento', form=form)

        department = Department(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(department)
        db.session.commit()
        flash(f'Departamento {department.name} adicionado com sucesso!')
        return redirect(url_for('admin.departments'))

    return render_template('admin/add_edit_department.html', title='Adicionar Departamento', form=form)

@bp.route('/departments/edit/<int:department_id>', methods=['GET', 'POST'])
@manager_required
def edit_department(department_id):
    """
    Rota para editar um departamento existente.
    """
    department = Department.query.get_or_404(department_id)
    form = DepartmentForm(obj=department)

    if form.validate_on_submit():
        existing_department = Department.query.filter_by(name=form.name.data).first()
        if existing_department and existing_department.id != department.id:
            flash('Este nome de departamento já está em uso.')
            return render_template('admin/add_edit_department.html', title='Editar Departamento', form=form, department=department)

        department.name = form.name.data
        department.description = form.description.data

        db.session.commit()
        flash(f'Departamento {department.name} atualizado com sucesso!')
        return redirect(url_for('admin.departments'))

    return render_template('admin/add_edit_department.html', title='Editar Departamento', form=form, department=department)

@bp.route('/departments/delete/<int:department_id>', methods=['POST'])
@manager_required
def delete_department(department_id):
    """
    Rota para excluir um departamento.
    """
    department = Department.query.get_or_404(department_id)
    # TODO: Adicionar lógica para verificar se há motoristas/veículos associados antes de excluir
    db.session.delete(department)
    db.session.commit()
    flash(f'Departamento {department.name} excluído com sucesso!')
    return redirect(url_for('admin.departments'))
