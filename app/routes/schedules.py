from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify # Adicionado jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Schedule, Vehicle, Driver, Department
from app.forms import ScheduleForm
from datetime import datetime, timedelta

# Criar um blueprint chamado 'schedules' com prefixo de URL '/schedules'
bp = Blueprint('schedules', __name__, url_prefix='/schedules')

@bp.route('/')
@login_required
def index():
    """
    Rota principal para listar agendamentos futuros.
    """
    # Obter agendamentos futuros
    future_schedules = Schedule.query.filter(
        Schedule.start_datetime >= datetime.now(),
        Schedule.status.in_(['scheduled', 'confirmed'])
    ).order_by(Schedule.start_datetime).all()

    return render_template(
        'schedules/index.html',
        title='Agendamentos',
        future_schedules=future_schedules
    )

@bp.route('/calendar')
@login_required
def calendar():
    """
    Rota para exibir o calendário de agendamentos.
    """
    # Verificar se o usuário é do almoxarifado ou gestor
    if current_user.type not in ['warehouse', 'manager']:
        flash('Acesso negado. Esta página é apenas para usuários do almoxarifado e gestores.')
        return redirect(url_for('main.index'))

    # Obter todos os agendamentos
    schedules = Schedule.query.order_by(Schedule.start_datetime.asc()).all()

    # Preparar dados para o calendário (ex: FullCalendar)
    # Para simplificar, vamos apenas passar a lista de agendamentos

    return render_template('schedules/calendar.html', title='Calendário de Agendamentos', schedules=schedules)

# Rota consolidada para adicionar/criar agendamentos
@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_schedule(): # Renomeado de 'create' para 'add_schedule' para consistência
    """
    Rota para adicionar um novo agendamento.
    GET: Exibe o formulário de agendamento
    POST: Processa o formulário enviado e cria o agendamento
    """
    if current_user.type != 'warehouse':
        flash('Acesso negado. Apenas usuários do almoxarifado podem agendar veículos.')
        return redirect(url_for('main.index'))

    form = ScheduleForm()
    if form.validate_on_submit():
        # Verificar conflitos de agendamento: mesmo veículo OU mesmo motorista no mesmo período
        conflicts = Schedule.query.filter(
            db.or_(
                Schedule.vehicle_id == form.vehicle_id.data,
                Schedule.driver_id == form.driver_id.data
            ),
            Schedule.status.in_(['scheduled', 'confirmed']),
            Schedule.start_datetime < form.end_datetime.data,
            Schedule.end_datetime > form.start_datetime.data
        ).all()

        if conflicts:
            flash('Há conflitos de horário para este veículo ou motorista. Por favor, escolha outro horário, veículo ou motorista.', 'danger')
            return render_template('schedules/add_schedule.html', title='Adicionar Agendamento', form=form, conflicts=conflicts) # Usar add_schedule.html

        # Criar novo agendamento
        schedule = Schedule(
            vehicle_id=form.vehicle_id.data,
            driver_id=form.driver_id.data,
            department_id=form.department_id.data,
            user_id=current_user.id,
            start_datetime=form.start_datetime.data,
            end_datetime=form.end_datetime.data,
            purpose=form.purpose.data,
            status='scheduled'
        )
        db.session.add(schedule)
        db.session.commit()
        flash('Agendamento criado com sucesso!', 'success')
        return redirect(url_for('schedules.calendar')) # Redirecionar para o calendário

    return render_template('schedules/add_schedule.html', title='Adicionar Agendamento', form=form) # Usar add_schedule.html

@bp.route('/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(schedule_id): # Renomeado para consistência
    """
    Rota para editar um agendamento existente.
    GET: Exibe o formulário preenchido com os dados do agendamento
    POST: Processa o formulário enviado e atualiza o agendamento
    """
    schedule = Schedule.query.get_or_404(schedule_id)

    # Verificar se o usuário tem permissão para editar (ex: apenas almoxarifado)
    if current_user.type != 'warehouse':
        flash('Acesso negado. Apenas usuários do almoxarifado podem editar agendamentos.', 'danger')
        return redirect(url_for('schedules.calendar'))

    # Verificar se o agendamento já foi concluído ou cancelado
    if schedule.status in ['completed', 'cancelled']:
        flash('Este agendamento não pode ser editado.', 'warning')
        return redirect(url_for('schedules.calendar'))

    form = ScheduleForm(obj=schedule)
    if form.validate_on_submit():
        # Verificar conflitos de agendamento: mesmo veículo OU mesmo motorista no mesmo período
        conflicts = Schedule.query.filter(
            db.or_(
                Schedule.vehicle_id == form.vehicle_id.data,
                Schedule.driver_id == form.driver_id.data
            ),
            Schedule.id != schedule_id,  # Excluir o próprio agendamento da verificação
            Schedule.status.in_(['scheduled', 'confirmed']),
            Schedule.start_datetime < form.end_datetime.data,
            Schedule.end_datetime > form.start_datetime.data
        ).all()

        if conflicts:
            flash('Há conflitos de horário para este veículo ou motorista. Por favor, escolha outro horário, veículo ou motorista.', 'danger')
            return render_template('schedules/edit_schedule.html', title='Editar Agendamento', form=form, schedule=schedule, conflicts=conflicts) # Usar edit_schedule.html

        # Atualizar agendamento
        schedule.vehicle_id = form.vehicle_id.data
        schedule.driver_id = form.driver_id.data
        schedule.department_id = form.department_id.data
        schedule.start_datetime = form.start_datetime.data
        schedule.end_datetime = form.end_datetime.data
        schedule.purpose = form.purpose.data
        db.session.commit()
        flash('Agendamento atualizado com sucesso!', 'success')
        return redirect(url_for('schedules.calendar')) # Redirecionar para o calendário

    return render_template('schedules/edit_schedule.html', title='Editar Agendamento', form=form, schedule=schedule) # Usar edit_schedule.html

@bp.route('/confirm/<int:schedule_id>', methods=['POST']) # Alterado para POST
@login_required
def confirm_schedule(schedule_id): # Renomeado para consistência
    """
    Rota para confirmar um agendamento.
    """
    schedule = Schedule.query.get_or_404(schedule_id)

    # Verificar permissão
    if current_user.type != 'warehouse':
        flash('Acesso negado. Apenas usuários do almoxarifado podem confirmar agendamentos.', 'danger')
        return redirect(url_for('schedules.calendar'))

    # Verificar se o agendamento já foi concluído ou cancelado
    if schedule.status in ['completed', 'cancelled']:
        flash('Este agendamento não pode ser confirmado.', 'warning')
        return redirect(url_for('schedules.calendar'))

    schedule.status = 'confirmed'
    db.session.commit()
    flash('Agendamento confirmado com sucesso!', 'success')
    return redirect(url_for('schedules.calendar')) # Redirecionar para o calendário

@bp.route('/cancel/<int:schedule_id>', methods=['POST']) # Alterado para POST
@login_required
def cancel_schedule(schedule_id): # Renomeado para consistência
    """
    Rota para cancelar um agendamento.
    """
    schedule = Schedule.query.get_or_404(schedule_id)

    # Verificar permissão
    if current_user.type != 'warehouse':
        flash('Acesso negado. Apenas usuários do almoxarifado podem cancelar agendamentos.', 'danger')
        return redirect(url_for('schedules.calendar'))

    # Verificar se o agendamento já foi concluído
    if schedule.status == 'completed':
        flash('Este agendamento não pode ser cancelado.', 'warning')
        return redirect(url_for('schedules.calendar'))

    schedule.status = 'cancelled'
    db.session.commit()
    flash('Agendamento cancelado com sucesso!', 'success')
    return redirect(url_for('schedules.calendar')) # Redirecionar para o calendário

@bp.route('/detail/<int:schedule_id>')
@login_required
def detail_schedule(schedule_id): # Renomeado para consistência
    """
    Rota para visualizar detalhes de um agendamento específico.
    """
    schedule = Schedule.query.get_or_404(schedule_id)
    return render_template('schedules/detail_schedule.html', title='Detalhes do Agendamento', schedule=schedule) # Usar detail_schedule.html

@bp.route('/week')
@login_required
def week_view():
    """
    Rota para visualizar agendamentos da semana atual.
    """
    # Calcular início e fim da semana atual
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start_datetime = datetime.combine(start_of_week, datetime.min.time())
    end_datetime = datetime.combine(end_of_week, datetime.max.time())

    # Obter agendamentos da semana
    schedules = Schedule.query.filter(
        Schedule.start_datetime >= start_datetime,
        Schedule.start_datetime <= end_datetime,
        Schedule.status.in_(['scheduled', 'confirmed'])
    ).order_by(Schedule.start_datetime).all()

    # Agrupar por dia da semana
    days = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_schedules = [s for s in schedules if s.start_datetime.date() == day]
        days.append({
            'date': day,
            'schedules': day_schedules
        })

    return render_template(
        'schedules/week_view.html', # Usar week_view.html
        title='Agendamentos da Semana',
        days=days,
        start_of_week=start_of_week,
        end_of_week=end_of_week
    )

@bp.route('/check-availability')
@login_required
def check_availability():
    """
    API para verificar disponibilidade de veículos em um determinado período.
    """
    vehicle_id = request.args.get('vehicle_id', type=int)
    start_date_str = request.args.get('start_date') # Renomeado para evitar conflito com datetime obj
    end_date_str = request.args.get('end_date') # Renomeado para evitar conflito com datetime obj

    if not all([vehicle_id, start_date_str, end_date_str]):
        return jsonify({'error': 'Parâmetros incompletos'}), 400

    try:
        start_datetime = datetime.fromisoformat(start_date_str)
        end_datetime = datetime.fromisoformat(end_date_str)
    except ValueError:
        return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DDTHH:MM:SS ou YYYY-MM-DDTHH:MM'}), 400

    # Verificar conflitos
    conflicts = Schedule.query.filter(
        Schedule.vehicle_id == vehicle_id,
        Schedule.status.in_(['scheduled', 'confirmed']),
        Schedule.start_datetime < end_datetime,
        Schedule.end_datetime > start_datetime
    ).all()

    if conflicts:
        conflict_data = [{
            'id': c.id,
            'start': c.start_datetime.isoformat(),
            'end': c.end_datetime.isoformat(),
            'driver': c.driver.name,
            'department': c.department.name
        } for c in conflicts]
        return jsonify({'available': False, 'conflicts': conflict_data})

    return jsonify({'available': True})

