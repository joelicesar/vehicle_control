# app/forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    TextAreaField, IntegerField, SelectField, DateTimeField, DateField # Adicionado DateField
)
from wtforms.validators import (
    DataRequired, ValidationError, Email, EqualTo, Length, NumberRange
)
from app.models import User, Vehicle, Driver, Department # Importar todos os modelos necessários
from datetime import datetime

# Formulário de Login
class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

# Formulário de Registro
class RegistrationForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    password2 = PasswordField(
        'Repita a Senha', validators=[DataRequired(), EqualTo('password')])
    type = SelectField('Tipo de Usuário', choices=[('warehouse', 'Almoxarifado'), ('manager', 'Gestor')], validators=[DataRequired()])
    submit = SubmitField('Registrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Por favor, use um nome de usuário diferente.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Por favor, use um endereço de email diferente.')

# Formulário para gerenciar Usuários (Adicionar/Editar)
class UserForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Senha (Deixe em branco para manter a atual)')
    password2 = PasswordField(
        'Repita a Senha', validators=[EqualTo('password', message='As senhas devem ser iguais.')])
    type = SelectField('Tipo de Usuário', choices=[('warehouse', 'Almoxarifado'), ('manager', 'Gestor')], validators=[DataRequired()])
    submit = SubmitField('Salvar')

    # Validações personalizadas para garantir unicidade (exceto para o próprio usuário em edição)
    def validate_username(self, username):
        # Esta validação precisa ser mais inteligente para edição
        # e será tratada na rota para permitir que o usuário mantenha seu próprio username
        pass

    def validate_email(self, email):
        # Esta validação precisa ser mais inteligente para edição
        # e será tratada na rota para permitir que o usuário mantenha seu próprio email
        pass

# Formulário para iniciar uma viagem
class StartTripForm(FlaskForm):
    vehicle_id = SelectField('Veículo', coerce=int, validators=[DataRequired()])
    driver_id = SelectField('Motorista', coerce=int, validators=[DataRequired()])
    department_id = SelectField('Departamento', coerce=int, validators=[DataRequired()])
    start_km = IntegerField('Quilometragem de Saída', validators=[DataRequired(), NumberRange(min=0)])
    vehicle_condition = TextAreaField('Estado do Veículo (opcional)', validators=[Length(max=500)])
    start_notes = TextAreaField('Observações (opcional)', validators=[Length(max=500)])
    purpose = StringField('Finalidade da Viagem (opcional)', validators=[Length(max=200)])
    submit = SubmitField('Iniciar Viagem')

    def __init__(self, *args, **kwargs):
        super(StartTripForm, self).__init__(*args, **kwargs)
        # Popula as opções de veículos, motoristas e departamentos
        self.vehicle_id.choices = [(v.id, f"{v.plate} - {v.model}") for v in Vehicle.query.filter_by(status='available').order_by(Vehicle.plate).all()]
        self.driver_id.choices = [(d.id, d.name) for d in Driver.query.filter_by(status='available').order_by(Driver.name).all()]
        self.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]

# Formulário para finalizar uma viagem
class EndTripForm(FlaskForm):
    end_km = IntegerField('Quilometragem de Chegada', validators=[DataRequired(), NumberRange(min=0)])
    vehicle_condition_end = TextAreaField('Estado do Veículo na Chegada (opcional)', validators=[Length(max=500)])
    end_notes = TextAreaField('Observações na Chegada (opcional)', validators=[Length(max=500)])
    submit = SubmitField('Finalizar Viagem')

    def validate_end_km(self, end_km):
        # Esta validação deve ser feita na rota, pois precisa do start_km da viagem
        pass

# Formulário para confirmar cancelamento
class ConfirmCancelForm(FlaskForm):
    submit = SubmitField('Confirmar Cancelamento')

# Formulário de Agendamento
class ScheduleForm(FlaskForm):
    vehicle_id = SelectField('Veículo', coerce=int, validators=[DataRequired()])
    driver_id = SelectField('Motorista', coerce=int, validators=[DataRequired()])
    department_id = SelectField('Departamento', coerce=int, validators=[DataRequired()])
    start_datetime = DateTimeField('Data e Hora de Início', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_datetime = DateTimeField('Data e Hora de Término', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    purpose = TextAreaField('Finalidade', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Agendar')

    def __init__(self, *args, **kwargs):
        super(ScheduleForm, self).__init__(*args, **kwargs)
        # Agendamento é para o futuro: o status atual ('in_use'/'in_trip', por exemplo) não deve
        # impedir a reserva. Só excluímos quem está permanentemente indisponível
        # (veículo em manutenção/inativo, motorista indisponível). O conflito real de
        # data/hora é checado nas rotas de add/edit via sobreposição de agendamentos.
        self.vehicle_id.choices = [
            (v.id, f"{v.plate} - {v.model}")
            for v in Vehicle.query.filter(~Vehicle.status.in_(['maintenance', 'inactive'])).order_by(Vehicle.plate).all()
        ]
        self.driver_id.choices = [
            (d.id, d.name)
            for d in Driver.query.filter(Driver.status != 'unavailable').order_by(Driver.name).all()
        ]
        self.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]

    def validate_start_datetime(self, field):
        if field.data < datetime.now():
            raise ValidationError('A data e hora de início não podem ser no passado.')

    def validate_end_datetime(self, field):
        if field.data <= self.start_datetime.data:
            raise ValidationError('A data e hora de término devem ser posteriores à data e hora de início.')

# Formulário para Geração de Relatórios
class ReportForm(FlaskForm):
    department_id = SelectField('Departamento', coerce=int, default=0) # 0 para 'Todos'
    start_date = DateField('Data Inicial', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('Data Final', format='%Y-%m-%d', validators=[DataRequired()])
    output_format = SelectField('Formato de Saída', choices=[
        ('html', 'Visualizar no Navegador'),
        ('excel', 'Download Excel'),
        ('pdf', 'Download PDF')
    ], validators=[DataRequired()], default='html')
    submit = SubmitField('Gerar Relatório')

    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        # Adicionar opção 'Todos' e depois os departamentos reais
        self.department_id.choices = [(0, 'Todos')] + [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError('A data final não pode ser anterior à data inicial.')

# --- NOVOS FORMULÁRIOS PARA ADMINISTRAÇÃO ---

# Formulário para Veículos (Adicionar/Editar)
class VehicleForm(FlaskForm):
    plate = StringField('Placa', validators=[DataRequired(), Length(min=7, max=8)])
    model = StringField('Modelo', validators=[DataRequired(), Length(max=100)])
    year = IntegerField('Ano', validators=[DataRequired(), NumberRange(min=1900, max=datetime.now().year + 1)])
    color = StringField('Cor', validators=[DataRequired(), Length(max=50)])
    status = SelectField('Status', choices=[
        ('available', 'Disponível'),
        ('in_use', 'Em Uso'),
        ('maintenance', 'Em Manutenção'),
        ('inactive', 'Inativo')
    ], validators=[DataRequired()])
    current_km = IntegerField('Quilometragem Atual', validators=[DataRequired(), NumberRange(min=0)])
    purchase_date = DateField('Data de Compra', format='%Y-%m-%d', validators=[DataRequired()])
    notes = TextAreaField('Observações (opcional)', validators=[Length(max=500)])
    submit = SubmitField('Salvar Veículo')

    def validate_plate(self, plate):
        # Esta validação será tratada na rota para permitir que o veículo mantenha sua própria placa em edição
        pass

# Formulário para Motoristas (Adicionar/Editar)
class DriverForm(FlaskForm):
    name = StringField('Nome Completo', validators=[DataRequired(), Length(min=3, max=100)])
    license_number = StringField('Número da CNH', validators=[DataRequired(), Length(min=9, max=11)])
    license_expiration = DateField('Validade da CNH', format='%Y-%m-%d', validators=[DataRequired()])
    phone = StringField('Telefone', validators=[DataRequired(), Length(min=10, max=15)])
    status = SelectField('Status', choices=[
        ('available', 'Disponível'),
        ('in_trip', 'Em Viagem'),
        ('unavailable', 'Indisponível')
    ], validators=[DataRequired()])
    notes = TextAreaField('Observações (opcional)', validators=[Length(max=500)])
    submit = SubmitField('Salvar Motorista')

    def __init__(self, *args, **kwargs):
        super(DriverForm, self).__init__(*args, **kwargs)

    def validate_license_number(self, license_number):
        # Esta validação será tratada na rota para permitir que o motorista mantenha sua própria CNH em edição
        pass

    def validate_license_expiration(self, field):
        if field.data < datetime.now().date():
            raise ValidationError('A CNH não pode estar vencida.')

# Formulário para Departamentos (Adicionar/Editar)
class DepartmentForm(FlaskForm):
    name = StringField('Nome do Departamento', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Descrição (opcional)', validators=[Length(max=500)])
    submit = SubmitField('Salvar Departamento')

    def validate_name(self, name):
        # Esta validação será tratada na rota para permitir que o departamento mantenha seu próprio nome em edição
        pass
