from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Trip, Vehicle, Driver, Department, Schedule # Certifique-se que Schedule está aqui
from app.forms import StartTripForm, EndTripForm, ConfirmCancelForm # Importe ConfirmCancelForm
from datetime import datetime, timedelta

bp = Blueprint('trips', __name__, url_prefix='/trips')

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.type != 'warehouse':
        flash('Acesso negado. Esta página é apenas para usuários do almoxarifado.', 'danger')
        return redirect(url_for('main.index'))

    # Estatísticas para os cards
    available_vehicles = Vehicle.query.filter_by(status='available').count()
    completed_trips_today = Trip.query.filter(
        Trip.end_datetime >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        Trip.status == 'completed'
    ).count()
    active_trips = Trip.query.filter_by(status='in_progress').all()
    upcoming_schedules_count = Schedule.query.filter(
        Schedule.start_datetime >= datetime.now(),
        Schedule.status.in_(['scheduled', 'confirmed'])
    ).count()

    # Lista de próximos agendamentos (limitado para o dashboard)
    upcoming_schedules_list = Schedule.query.filter(
        Schedule.start_datetime >= datetime.now(),
        Schedule.status.in_(['scheduled', 'confirmed'])
    ).order_by(Schedule.start_datetime).limit(5).all() # Limitar para não sobrecarregar o dashboard

    return render_template(
        'trips/dashboard.html',
        title='Dashboard Almoxarifado',
        available_vehicles=available_vehicles,
        completed_trips_today=completed_trips_today,
        active_trips=active_trips,
        upcoming_schedules=upcoming_schedules_count,
        upcoming_schedules_list=upcoming_schedules_list,
        now=datetime.now() # Passar a data/hora atual para calcular a duração
    )

@bp.route('/active')
@login_required
def active():
    if current_user.type != 'warehouse':
        flash('Acesso negado. Esta página é apenas para usuários do almoxarifado.', 'danger')
        return redirect(url_for('main.index'))

    trips = Trip.query.filter_by(status='in_progress').order_by(Trip.start_datetime.desc()).all()
    return render_template('trips/active.html', title='Viagens em Andamento', trips=trips, now=datetime.now())

@bp.route('/history')
@login_required
def history():
    # Permite acesso a almoxarifado e gestor
    if current_user.type not in ['warehouse', 'manager']:
        flash('Acesso negado. Esta página é apenas para usuários do almoxarifado e gestores.', 'danger')
        return redirect(url_for('main.index'))

    # Obter todos os veículos, motoristas e departamentos para os filtros
    all_vehicles = Vehicle.query.order_by(Vehicle.plate).all()
    all_drivers = Driver.query.order_by(Driver.name).all()
    all_departments = Department.query.order_by(Department.name).all()

    # Parâmetros de filtro da URL
    vehicle_id = request.args.get('vehicle_id', type=int)
    driver_id = request.args.get('driver_id', type=int)
    department_id = request.args.get('department_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    query = Trip.query.filter(Trip.status.in_(['completed', 'cancelled'])) # Incluir canceladas no histórico

    if vehicle_id:
        query = query.filter_by(vehicle_id=vehicle_id)
    if driver_id:
        query = query.filter_by(driver_id=driver_id)
    if department_id:
        query = query.filter_by(department_id=department_id)
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        query = query.filter(Trip.start_datetime >= start_date)
    else:
        start_date_str = '' # Para manter o campo vazio se não houver filtro
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(microseconds=1) # Inclui o dia inteiro
        query = query.filter(Trip.end_datetime <= end_date)
    else:
        end_date_str = '' # Para manter o campo vazio se não houver filtro

    trips = query.order_by(Trip.start_datetime.desc()).all()

    return render_template(
        'trips/history.html',
        title='Histórico de Viagens',
        trips=trips,
        vehicles=all_vehicles,
        drivers=all_drivers,
        departments=all_departments,
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        department_id=department_id,
        start_date=start_date_str,
        end_date=end_date_str
    )

@bp.route('/detail/<int:trip_id>')
@login_required
def trip_detail(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    # Permite acesso a almoxarifado e gestor
    if current_user.type not in ['warehouse', 'manager']:
        flash('Acesso negado. Esta página é apenas para usuários do almoxarifado e gestores.', 'danger')
        return redirect(url_for('main.index'))

    return render_template('trips/detail.html', title=f'Detalhes da Viagem #{trip.id}', trip=trip)

@bp.route('/start', methods=['GET', 'POST'])
@login_required
def start_trip():
    if current_user.type != 'warehouse':
        flash('Acesso negado. Apenas usuários do almoxarifado podem registrar saídas.', 'danger')
        return redirect(url_for('main.index'))

    form = StartTripForm()
    if form.validate_on_submit():
        # Verificar se o veículo está realmente disponível
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        if not vehicle or vehicle.status != 'available':
            flash('Veículo selecionado não está disponível.', 'danger')
            return render_template('trips/start_trip.html', title='Registrar Saída de Veículo', form=form)

        # Verificar se o motorista está disponível
        driver = Driver.query.get(form.driver_id.data)
        if not driver or driver.status != 'available':
            flash('Motorista selecionado não está disponível.', 'danger')
            return render_template('trips/start_trip.html', title='Registrar Saída de Veículo', form=form)

        # Avisar (sem bloquear) se este veículo ou motorista tem agendamento
        # confirmado/marcado para as próximas horas, para o almoxarifado não
        # entregar o veículo sem saber que alguém já reservou.
        upcoming_window = datetime.now() + timedelta(hours=24)
        upcoming_schedules = Schedule.query.filter(
            db.or_(Schedule.vehicle_id == vehicle.id, Schedule.driver_id == driver.id),
            Schedule.status.in_(['scheduled', 'confirmed']),
            Schedule.start_datetime >= datetime.now(),
            Schedule.start_datetime <= upcoming_window
        ).order_by(Schedule.start_datetime).all()

        for s in upcoming_schedules:
            flash(
                f'Atenção: {s.vehicle.plate} / {s.driver.name} tem agendamento '
                f'em {s.start_datetime.strftime("%d/%m/%Y %H:%M")} ({s.department.name}). '
                'Combine o horário de devolução para não atrasar essa reserva.',
                'warning'
            )

        trip = Trip(
            vehicle_id=form.vehicle_id.data,
            driver_id=form.driver_id.data,
            department_id=form.department_id.data,
            user_id=current_user.id,
            start_datetime=datetime.now(),
            start_km=form.start_km.data,
            vehicle_condition=form.vehicle_condition.data,
            start_notes=form.start_notes.data,
            purpose=form.purpose.data,
            status='in_progress'
        )
        db.session.add(trip)

        # Atualizar status do veículo e motorista
        vehicle.status = 'in_use'
        driver.status = 'in_trip'

        db.session.commit()
        flash('Saída de veículo registrada com sucesso!', 'success')
        return redirect(url_for('trips.dashboard'))

    return render_template('trips/start_trip.html', title='Registrar Saída de Veículo', form=form)

@bp.route('/end/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def end_trip(trip_id):
    if current_user.type != 'warehouse':
        flash('Acesso negado. Apenas usuários do almoxarifado podem registrar chegadas.', 'danger')
        return redirect(url_for('main.index'))

    trip = Trip.query.get_or_404(trip_id)

    if trip.status != 'in_progress':
        flash('Esta viagem não está em andamento e não pode ser finalizada.', 'warning')
        return redirect(url_for('trips.trip_detail', trip_id=trip.id))

    form = EndTripForm()
    if form.validate_on_submit():
        if form.end_km.data < trip.start_km:
            flash('A quilometragem final não pode ser menor que a quilometragem inicial.', 'danger')
            return render_template('trips/end_trip.html', title='Registrar Chegada de Veículo', form=form, trip=trip)

        trip.end_datetime = datetime.now()
        trip.end_km = form.end_km.data
        trip.distance_logged = trip.end_km - trip.start_km
        trip.vehicle_condition_end = form.vehicle_condition_end.data
        trip.end_notes = form.end_notes.data
        trip.status = 'completed'

        # Calcular valor da cobrança (exemplo: R$ 0.50 por km)
        trip.charge_amount_logged = trip.distance_logged * 2.00

        # Atualizar status do veículo e motorista
        trip.vehicle.status = 'available'
        trip.driver.status = 'available'

        db.session.commit()
        flash('Chegada de veículo registrada e viagem finalizada com sucesso!', 'success')
        return redirect(url_for('trips.history'))

    # Preencher o campo de KM final com o KM inicial como sugestão
    if request.method == 'GET':
        form.end_km.data = trip.start_km

    return render_template('trips/end_trip.html', title='Registrar Chegada de Veículo', form=form, trip=trip)

# NOVA ROTA PARA CANCELAR VIAGEM
@bp.route('/cancel/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def cancel_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    if current_user.type != 'warehouse':
        flash('Acesso negado. Apenas usuários do almoxarifado podem cancelar viagens.', 'danger')
        return redirect(url_for('main.index'))

    if trip.status == 'completed':
        flash('Viagens concluídas não podem ser canceladas.', 'warning')
        return redirect(url_for('trips.trip_detail', trip_id=trip.id))

    # Se a viagem já está cancelada, apenas redireciona
    if trip.status == 'cancelled':
        flash('Esta viagem já foi cancelada.', 'info')
        return redirect(url_for('trips.trip_detail', trip_id=trip.id))

    form = ConfirmCancelForm() # Instancia o formulário de confirmação

    if form.validate_on_submit():
        trip.status = 'cancelled'
        # Se a viagem estava em andamento, liberar veículo e motorista
        if trip.vehicle and trip.vehicle.status == 'in_use':
            trip.vehicle.status = 'available'
        if trip.driver and trip.driver.status == 'in_trip':
            trip.driver.status = 'available'

        db.session.commit()
        flash(f'Viagem #{trip.id} cancelada com sucesso!', 'success')
        return redirect(url_for('trips.history'))

    return render_template('trips/cancel_trip.html', title='Confirmar Cancelamento', trip=trip, form=form)

