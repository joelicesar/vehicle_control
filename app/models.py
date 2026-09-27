# app/models.py
from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Função de callback para Flask-Login para carregar o usuário
from app import login

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='warehouse') # 'warehouse' ou 'manager'

    # Relacionamentos
    trips_started = db.relationship('Trip', foreign_keys='Trip.user_id', backref='starter', lazy='dynamic')
    schedules_created = db.relationship('Schedule', foreign_keys='Schedule.user_id', backref='creator', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(10), unique=True, nullable=False)
    model = db.Column(db.String(64), nullable=False)
    year = db.Column(db.Integer)
    color = db.Column(db.String(32))
    current_km = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='available') # 'available', 'in_use', 'maintenance'
    purchase_date = db.Column(db.Date) # <-- COLUNA ADICIONADA AQUI
    notes = db.Column(db.Text) # <-- COLUNA ADICIONADA AQUI (do formulário)

    # Relacionamentos
    trips = db.relationship('Trip', backref='vehicle', lazy='dynamic')
    schedules = db.relationship('Schedule', backref='vehicle', lazy='dynamic')

    def __repr__(self):
        return f'<Vehicle {self.plate} - {self.model}>'

class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    license_number = db.Column(db.String(32), unique=True, nullable=False)
    license_expiration = db.Column(db.Date)
    phone = db.Column(db.String(32))
    status = db.Column(db.String(20), default='available')  # 'available', 'in_trip', 'unavailable'
    notes = db.Column(db.Text)

    # Relacionamentos
    trips = db.relationship('Trip', backref='driver', lazy='dynamic')
    schedules = db.relationship('Schedule', backref='driver', lazy='dynamic')

    def __repr__(self):
        return f'<Driver {self.name}>'

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text) # <-- COLUNA ADICIONADA AQUI (do formulário)

    # Relacionamentos
    trips = db.relationship('Trip', backref='department', lazy='dynamic')
    schedules = db.relationship('Schedule', backref='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.name}>'

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Usuário que iniciou a viagem

    start_datetime = db.Column(db.DateTime, nullable=False, default=datetime.now)
    end_datetime = db.Column(db.DateTime)

    start_km = db.Column(db.Float, nullable=False)
    end_km = db.Column(db.Float)

    # NOVOS CAMPOS PARA ARMAZENAR VALORES CALCULADOS
    distance_logged = db.Column(db.Float) # Distância calculada e armazenada
    charge_amount_logged = db.Column(db.Float) # Valor da cobrança calculada e armazenada

    purpose = db.Column(db.String(256))
    start_notes = db.Column(db.Text)
    end_notes = db.Column(db.Text)
    vehicle_condition = db.Column(db.Text) # Condição do veículo na saída

    status = db.Column(db.String(20), default='in_progress') # 'in_progress', 'completed', 'cancelled'

    # Propriedade calculada para distância (não armazenada diretamente, mas derivada)
    @property
    def distance(self):
        if self.start_km is not None and self.end_km is not None:
            return self.end_km - self.start_km
        return 0.0

    # Propriedade calculada para valor da cobrança (não armazenada diretamente, mas derivada)
    @property
    def charge_amount(self):
        # Defina seu custo por KM aqui ou em uma configuração (ex: app.config['COST_PER_KM'])
        cost_per_km = 2.00 # Exemplo: R$ 0.50 por KM
        if self.distance > 0:
            return self.distance * cost_per_km
        return 0.0

    def __repr__(self):
        return f'<Trip {self.id} - Vehicle {self.vehicle.plate} - Driver {self.driver.name}>'

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Usuário que agendou

    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    purpose = db.Column(db.String(256))
    status = db.Column(db.String(20), default='scheduled') # 'scheduled', 'confirmed', 'cancelled', 'completed'

    def __repr__(self):
        return f'<Schedule {self.id} - Vehicle {self.vehicle.plate} - Driver {self.driver.name}>'
