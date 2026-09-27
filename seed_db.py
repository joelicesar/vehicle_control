# seed_db.py
from app import create_app, db
from app.models import User, Vehicle, Department, Driver, Trip, Schedule
from datetime import datetime, timedelta
import random

def seed_database():
    """
    Popula o banco de dados com dados de exemplo.
    """
    print("Iniciando população do banco de dados...")

    # Criar a aplicação e contexto
    app = create_app()
    with app.app_context():
        # Limpar dados existentes
        print("Limpando dados existentes...")
        Trip.query.delete()
        Schedule.query.delete()
        Driver.query.delete()
        Vehicle.query.delete()
        Department.query.delete()
        User.query.delete()

        # Criar usuários
        print("Criando usuários...")
        warehouse_user = User(username='almoxarifado', email='almoxarifado@empresa.com', type='warehouse')
        warehouse_user.set_password('senha123')

        manager_user = User(username='gestor', email='gestor@empresa.com', type='manager')
        manager_user.set_password('senha123')

        db.session.add(warehouse_user)
        db.session.add(manager_user)

        # Criar departamentos
        print("Criando departamentos...")
        departments = [
            Department(name='Administrativo', cost_center='CC001'),
            Department(name='Comercial', cost_center='CC002'),
            Department(name='Operacional', cost_center='CC003'),
            Department(name='TI', cost_center='CC004'),
            Department(name='RH', cost_center='CC005')
        ]

        for dept in departments:
            db.session.add(dept)

        # Commit para obter IDs
        db.session.commit()

        # Criar veículos
        print("Criando veículos...")
        vehicles = [
            Vehicle(plate='ABC1234', model='Fiat Uno', year=2020, current_km=15000, status='available'),
            Vehicle(plate='DEF5678', model='VW Gol', year=2021, current_km=8000, status='available'),
            Vehicle(plate='GHI9012', model='Chevrolet Onix', year=2022, current_km=5000, status='available'),
            Vehicle(plate='JKL3456', model='Renault Sandero', year=2019, current_km=25000, status='in_use'),
            Vehicle(plate='MNO7890', model='Toyota Corolla', year=2021, current_km=12000, status='available')
        ]

        for vehicle in vehicles:
            db.session.add(vehicle)

        # Commit para obter IDs
        db.session.commit()

        # Criar motoristas
        print("Criando motoristas...")
        drivers = [
            Driver(name='João Silva', department=departments[0], license_number='123456789', license_expiry=datetime(2025, 12, 31)),
            Driver(name='Maria Oliveira', department=departments[1], license_number='987654321', license_expiry=datetime(2024, 10, 15)),
            Driver(name='Pedro Santos', department=departments[2], license_number='456789123', license_expiry=datetime(2023, 8, 20)),
            Driver(name='Ana Souza', department=departments[3], license_number='789123456', license_expiry=datetime(2024, 5, 10)),
            Driver(name='Carlos Ferreira', department=departments[4], license_number='321654987', license_expiry=datetime(2025, 3, 25))
        ]

        for driver in drivers:
            db.session.add(driver)

        # Commit para obter IDs
        db.session.commit()

        # Criar viagens concluídas (histórico)
        print("Criando histórico de viagens...")

        # Data base para viagens (30 dias atrás)
        base_date = datetime.now() - timedelta(days=30)

        # Criar algumas viagens concluídas nos últimos 30 dias
        for i in range(20):
            # Data aleatória nos últimos 30 dias
            days_ago = random.randint(0, 29)
            start_date = base_date + timedelta(days=days_ago)

            # Duração aleatória entre 1 e 8 horas
            duration_hours = random.randint(1, 8)
            end_date = start_date + timedelta(hours=duration_hours)

            # Selecionar veículo, motorista e departamento aleatórios
            vehicle = random.choice(vehicles)
            driver = random.choice(drivers)
            department = random.choice(departments)

            # Quilometragem aleatória
            start_km = vehicle.current_km - random.randint(100, 500)
            distance = random.randint(20, 200)
            end_km = start_km + distance

            # Criar viagem
            trip = Trip(
                vehicle=vehicle,
                driver=driver,
                department=department,
                start_datetime=start_date,
                end_datetime=end_date,
                start_km=start_km,
                end_km=end_km,
                vehicle_condition="Veículo em bom estado",
                start_notes="Saída para visita a cliente",
                end_notes="Retorno sem problemas",
                status='completed'
            )

            db.session.add(trip)

            # Atualizar quilometragem do veículo
            vehicle.current_km = end_km

        # Criar uma viagem em andamento
        in_progress_vehicle = vehicles[3]  # Veículo com status 'in_use'
        in_progress_trip = Trip(
            vehicle=in_progress_vehicle,
            driver=drivers[2],
            department=departments[2],
            start_datetime=datetime.now() - timedelta(hours=2),
            start_km=in_progress_vehicle.current_km,
            vehicle_condition="Veículo em bom estado",
            start_notes="Saída para entrega de mercadoria",
            status='in_progress'
        )

        db.session.add(in_progress_trip)

        # Criar agendamentos futuros
        print("Criando agendamentos futuros...")

        # Data base para agendamentos (hoje)
        base_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        # Criar alguns agendamentos para os próximos 7 dias
        for i in range(10):
            # Data aleatória nos próximos 7 dias
            days_ahead = random.randint(0, 7)
            start_date = base_date + timedelta(days=days_ahead, hours=random.randint(0, 8))

            # Duração aleatória entre 2 e 6 horas
            duration_hours = random.randint(2, 6)
            end_date = start_date + timedelta(hours=duration_hours)

            # Selecionar veículo, motorista e departamento aleatórios
            vehicle = random.choice([v for v in vehicles if v.status == 'available'])
            driver = random.choice(drivers)
            department = random.choice(departments)

            # Status aleatório (agendado ou confirmado)
            status = random.choice(['scheduled', 'confirmed'])

            # Finalidades possíveis
            purposes = [
                "Visita a cliente",
                "Entrega de mercadoria",
                "Reunião externa",
                "Manutenção preventiva",
                "Transporte de funcionários"
            ]

            # Criar agendamento
            schedule = Schedule(
                vehicle=vehicle,
                driver=driver,
                department=department,
                start_datetime=start_date,
                end_datetime=end_date,
                purpose=random.choice(purposes),
                status=status
            )

            db.session.add(schedule)

        # Commit final
        db.session.commit()
        print("População do banco de dados concluída com sucesso!")

if __name__ == '__main__':
    seed_database()
