from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from app import db
from app.models import Trip, Vehicle, Driver, Department
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/dashboard')
@login_required
def dashboard():
    # Verificar permissão
    if current_user.type != 'manager':
        flash('Acesso negado. Esta página é apenas para gestores.', 'danger')
        return redirect(url_for('main.index'))

    # Obter estatísticas para o dashboard
    # Total de veículos
    total_vehicles = Vehicle.query.count()
    available_vehicles = Vehicle.query.filter_by(status='available').count()

    # Total de motoristas
    total_drivers = Driver.query.count()
    available_drivers = Driver.query.filter_by(status='available').count()

    # Viagens do mês atual
    today = datetime.now().date()
    start_of_month = datetime(today.year, today.month, 1).date()
    end_of_month = (datetime(today.year, today.month + 1, 1) - timedelta(days=1)).date() if today.month < 12 else datetime(today.year, 12, 31).date()

    trips_this_month = Trip.query.filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time())
    ).count()

    # Viagens completadas este mês
    completed_trips_this_month = Trip.query.filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time()),
        Trip.status == 'completed'
    ).count()

    # Quilometragem total do mês
    total_km_this_month = db.session.query(db.func.sum(Trip.distance_logged)).filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time()),
        Trip.status == 'completed'
    ).scalar() or 0

    # Valor total cobrado este mês (R$ 2,00 por km)
    total_amount_this_month = total_km_this_month * 2.00

    # Departamentos mais ativos (top 5)
    top_departments = db.session.query(
        Department.name,
        db.func.count(Trip.id).label('trip_count')
    ).join(Trip, Department.id == Trip.department_id).filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time())
    ).group_by(Department.name).order_by(db.desc('trip_count')).limit(5).all()

    # Veículos mais utilizados (top 5)
    top_vehicles = db.session.query(
        Vehicle.plate,
        db.func.count(Trip.id).label('trip_count')
    ).join(Trip, Vehicle.id == Trip.vehicle_id).filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time())
    ).group_by(Vehicle.plate).order_by(db.desc('trip_count')).limit(5).all()

    # Motoristas mais ativos (top 5)
    top_drivers = db.session.query(
        Driver.name,
        db.func.count(Trip.id).label('trip_count')
    ).join(Trip, Driver.id == Trip.driver_id).filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time())
    ).group_by(Driver.name).order_by(db.desc('trip_count')).limit(5).all()

    return render_template(
        'reports/dashboard.html',
        title='Dashboard de Gestão',
        total_vehicles=total_vehicles,
        available_vehicles=available_vehicles,
        total_drivers=total_drivers,
        available_drivers=available_drivers,
        trips_this_month=trips_this_month,
        completed_trips_this_month=completed_trips_this_month,
        total_km=total_km_this_month,  # Usar esta variável para total_km
        total_km_this_month=total_km_this_month,
        total_amount_this_month=total_amount_this_month,
        top_departments=top_departments,
        top_vehicles=top_vehicles,
        top_drivers=top_drivers,
        current_month=datetime.now().strftime('%B %Y')
    )

@bp.route('/billing')
@login_required
def billing():
    # Verificar permissão
    if current_user.type != 'manager':
        flash('Acesso negado. Esta página é apenas para gestores.', 'danger')
        return redirect(url_for('main.index'))

    # Obter todos os departamentos para o filtro
    departments = Department.query.order_by(Department.name).all()

    # Parâmetros de filtro
    department_id = request.args.get('department_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Definir o custo por km (R$ 2,00)
    cost_per_km = 2.00

    # Datas padrão (mês atual)
    today = datetime.now().date()
    start_of_month = datetime(today.year, today.month, 1).date()
    end_of_month = (datetime(today.year, today.month + 1, 1) - timedelta(days=1)).date() if today.month < 12 else datetime(today.year, 12, 31).date()

    # Processar datas do filtro
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = start_of_month
        start_date_str = start_date.strftime('%Y-%m-%d')

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        end_date = end_of_month
        end_date_str = end_date.strftime('%Y-%m-%d')

    # Construir a query base
    query = Trip.query.filter(
        Trip.status == 'completed',
        Trip.end_datetime.isnot(None),
        Trip.start_datetime >= datetime.combine(start_date, datetime.min.time()),
        Trip.end_datetime <= datetime.combine(end_date, datetime.max.time())
    )

    # Filtrar por departamento se especificado
    if department_id:
        query = query.filter_by(department_id=department_id)

    # Executar a query
    trips = query.order_by(Trip.department_id, Trip.end_datetime).all()

    # Agrupar por departamento para o relatório
    departments_data = {}
    total_distance = 0
    total_amount = 0

    for trip in trips:
        dept_id = trip.department_id
        if dept_id not in departments_data:
            departments_data[dept_id] = {
                'name': trip.department.name,
                'trips': [],
                'total_distance': 0,
                'total_amount': 0
            }

        # Usar distance_logged se disponível, senão calcular
        distance = trip.distance_logged if trip.distance_logged is not None else (trip.end_km - trip.start_km)

        # Usar charge_amount_logged se disponível, senão calcular com o valor correto de R$ 2,00 por km
        amount = trip.charge_amount_logged if trip.charge_amount_logged is not None else (distance * cost_per_km)

        departments_data[dept_id]['trips'].append({
            'id': trip.id,
            'vehicle': trip.vehicle.plate,
            'driver': trip.driver.name,
            'start_date': trip.start_datetime,
            'end_date': trip.end_datetime,
            'distance': distance,
            'amount': amount
        })

        departments_data[dept_id]['total_distance'] += distance
        departments_data[dept_id]['total_amount'] += amount
        total_distance += distance
        total_amount += amount

    return render_template(
        'reports/billing.html',
        title='Relatório de Cobrança',
        departments=departments,
        department_id=department_id,
        start_date=start_date_str,
        end_date=end_date_str,
        departments_data=departments_data,
        total_distance=total_distance,
        total_amount=total_amount,
        cost_per_km=cost_per_km
    )

@bp.route('/billing/export-pdf')
@login_required
def export_billing_pdf():
    # Verificar permissão
    if current_user.type != 'manager':
        flash('Acesso negado. Esta página é apenas para gestores.', 'danger')
        return redirect(url_for('main.index'))

    # Obter os mesmos parâmetros de filtro da página de relatório
    department_id = request.args.get('department_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Definir o custo por km (R$ 2,00)
    cost_per_km = 2.00

    # Processar datas do filtro (mesmo código da função billing)
    today = datetime.now().date()
    start_of_month = datetime(today.year, today.month, 1).date()
    end_of_month = (datetime(today.year, today.month + 1, 1) - timedelta(days=1)).date() if today.month < 12 else datetime(today.year, 12, 31).date()

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = start_of_month

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        end_date = end_of_month

    # Construir a query base (mesmo código da função billing)
    query = Trip.query.filter(
        Trip.status == 'completed',
        Trip.end_datetime.isnot(None),
        Trip.start_datetime >= datetime.combine(start_date, datetime.min.time()),
        Trip.end_datetime <= datetime.combine(end_date, datetime.max.time())
    )

    # Filtrar por departamento se especificado
    if department_id:
        query = query.filter_by(department_id=department_id)
        department_name = Department.query.get(department_id).name
    else:
        department_name = "Todos os Departamentos"

    # Executar a query
    trips = query.order_by(Trip.department_id, Trip.end_datetime).all()

    # Preparar o buffer para o PDF
    buffer = BytesIO()

    # Criar o documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    # Definir estilos
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']

    # Criar elementos do PDF
    elements = []

    # Título do relatório
    title = Paragraph(f"Relatório de Cobrança", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.25*inch))

    # Subtítulo com informações do filtro
    subtitle = Paragraph(
        f"Departamento: {department_name} | Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}",
        subtitle_style
    )
    elements.append(subtitle)
    elements.append(Spacer(1, 0.25*inch))

    # Agrupar por departamento
    departments_data = {}
    total_distance = 0
    total_amount = 0

    for trip in trips:
        dept_id = trip.department_id
        if dept_id not in departments_data:
            departments_data[dept_id] = {
                'name': trip.department.name,
                'trips': [],
                'total_distance': 0,
                'total_amount': 0
            }

        # Usar distance_logged se disponível, senão calcular
        distance = trip.distance_logged if trip.distance_logged is not None else (trip.end_km - trip.start_km)

        # Calcular o valor usando o custo por km correto
        amount = distance * cost_per_km

        departments_data[dept_id]['trips'].append({
            'id': trip.id,
            'vehicle': trip.vehicle.plate,
            'driver': trip.driver.name,
            'start_date': trip.start_datetime.strftime('%d/%m/%Y %H:%M'),
            'end_date': trip.end_datetime.strftime('%d/%m/%Y %H:%M'),
            'distance': distance,
            'amount': amount
        })

        departments_data[dept_id]['total_distance'] += distance
        departments_data[dept_id]['total_amount'] += amount
        total_distance += distance
        total_amount += amount

    # Criar tabelas para cada departamento
    for dept_id, dept_data in departments_data.items():
        # Título do departamento
        dept_title = Paragraph(f"Departamento: {dept_data['name']}", subtitle_style)
        elements.append(dept_title)
        elements.append(Spacer(1, 0.1*inch))

        # Cabeçalho da tabela
        table_data = [
            ['ID', 'Veículo', 'Motorista', 'Data Início', 'Data Fim', 'Distância (km)', 'Valor (R$)']
        ]

        # Dados da tabela
        for trip in dept_data['trips']:
            table_data.append([
                str(trip['id']),
                trip['vehicle'],
                trip['driver'],
                trip['start_date'],
                trip['end_date'],
                f"{trip['distance']:.1f}",
                f"R$ {trip['amount']:.2f}"
            ])

        # Linha de total do departamento
        table_data.append([
            '', '', '', '', 'Total do Departamento:',
            f"{dept_data['total_distance']:.1f}",
            f"R$ {dept_data['total_amount']:.2f}"
        ])

        # Criar a tabela
        table = Table(table_data, repeatRows=1)

        # Estilo da tabela
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (5, 1), (6, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        table.setStyle(table_style)

        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))

    # Adicionar total geral se houver mais de um departamento
    if len(departments_data) > 1:
        total_title = Paragraph("Total Geral", subtitle_style)
        elements.append(total_title)
        elements.append(Spacer(1, 0.1*inch))

        total_table = Table([
            ['Total de Quilômetros', 'Valor Total'],
            [f"{total_distance:.1f} km", f"R$ {total_amount:.2f}"]
        ])

        total_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 1), (-1, 1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        total_table.setStyle(total_style)

        elements.append(total_table)

    # Adicionar data de geração do relatório
    generation_date = Paragraph(
        f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        normal_style
    )
    elements.append(Spacer(1, 0.5*inch))
    elements.append(generation_date)

    # Construir o PDF
    doc.build(elements)

    # Preparar a resposta
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_cobranca_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf'

    return response

# Adicione as novas rotas aqui, garantindo que os nomes sejam únicos
@bp.route('/vehicle-usage')
@login_required
def vehicle_usage():
    # Verificar permissão
    if current_user.type != 'manager':
        flash('Acesso negado. Esta página é apenas para gestores.', 'danger')
        return redirect(url_for('main.index'))

    # Implementação temporária - redirecionar para dashboard
    flash('Relatório de Uso de Veículos em desenvolvimento.', 'info')
    return redirect(url_for('reports.dashboard'))

@bp.route('/department-summary')
@login_required
def department_summary():
    # Verificar permissão
    if current_user.type != 'manager':
        flash('Acesso negado. Esta página é apenas para gestores.', 'danger')
        return redirect(url_for('main.index'))

    # Implementação temporária - redirecionar para dashboard
    flash('Resumo por Departamento em desenvolvimento.', 'info')
    return redirect(url_for('reports.dashboard'))

@bp.route('/dashboard-view')
@login_required
def dashboard_view():
    # Verificar permissão
    if current_user.type != 'manager':
        flash('Acesso negado. Esta página é apenas para gestores.', 'danger')
        return redirect(url_for('main.index'))

    # Obter estatísticas para o dashboard
    # Total de veículos
    total_vehicles = Vehicle.query.count()
    available_vehicles = Vehicle.query.filter_by(status='available').count()

    # Total de motoristas
    total_drivers = Driver.query.count()
    available_drivers = Driver.query.filter_by(status='available').count()

    # Viagens do mês atual
    today = datetime.now().date()
    start_of_month = datetime(today.year, today.month, 1).date()
    end_of_month = (datetime(today.year, today.month + 1, 1) - timedelta(days=1)).date() if today.month < 12 else datetime(today.year, 12, 31).date()

    trips_this_month = Trip.query.filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time())
    ).count()

    # Viagens completadas este mês
    completed_trips_this_month = Trip.query.filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time()),
        Trip.status == 'completed'
    ).count()

    # Quilometragem total do mês
    total_km_this_month = db.session.query(db.func.sum(Trip.distance_logged)).filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time()),
        Trip.status == 'completed'
    ).scalar() or 0

    # Valor total cobrado este mês (R$ 2,00 por km)
    total_amount_this_month = total_km_this_month * 2.00

    # Departamentos mais ativos (top 5)
    top_departments = db.session.query(
        Department.name,
        db.func.count(Trip.id).label('trip_count')
    ).join(Trip, Department.id == Trip.department_id).filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time())
    ).group_by(Department.name).order_by(db.desc('trip_count')).limit(5).all()

    # Veículos mais utilizados (top 5)
    top_vehicles = db.session.query(
        Vehicle.plate,
        db.func.count(Trip.id).label('trip_count')
    ).join(Trip, Vehicle.id == Trip.vehicle_id).filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time())
    ).group_by(Vehicle.plate).order_by(db.desc('trip_count')).limit(5).all()

    # Motoristas mais ativos (top 5)
    top_drivers = db.session.query(
        Driver.name,
        db.func.count(Trip.id).label('trip_count')
    ).join(Trip, Driver.id == Trip.driver_id).filter(
        Trip.start_datetime >= datetime.combine(start_of_month, datetime.min.time()),
        Trip.start_datetime <= datetime.combine(end_of_month, datetime.max.time())
    ).group_by(Driver.name).order_by(db.desc('trip_count')).limit(5).all()

    return render_template(
        'reports/dashboard.html',
        title='Dashboard de Gestão',
        total_vehicles=total_vehicles,
        available_vehicles=available_vehicles,
        total_drivers=total_drivers,
        available_drivers=available_drivers,
        trips_this_month=trips_this_month,
        completed_trips_this_month=completed_trips_this_month,
        total_km=total_km_this_month,
        total_km_this_month=total_km_this_month,
        total_amount=total_amount_this_month,  # Adicionar esta linha
        total_amount_this_month=total_amount_this_month,
        top_departments=top_departments,
        top_vehicles=top_vehicles,
        top_drivers=top_drivers,
        current_month=datetime.now().strftime('%B %Y')
    )
