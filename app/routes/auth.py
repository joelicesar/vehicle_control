# app/routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from urllib.parse import urlparse
from app import db
from app.models import User
from app.forms import LoginForm, RegistrationForm

# Criar um blueprint chamado 'auth' com prefixo de URL '/auth'
bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Rota para login de usuários.
    GET: Exibe o formulário de login
    POST: Processa o formulário enviado e autentica o usuário
    """
    # Se o usuário já estiver autenticado, redireciona para o dashboard
    if current_user.is_authenticated:
        current_app.logger.info(f"Usuário {current_user.username} já autenticado, redirecionando para dashboard.")
        # Redirecionamento inteligente para o dashboard correto
        if current_user.type == 'manager':
            return redirect(url_for('reports.dashboard'))
        elif current_user.type == 'warehouse':
            return redirect(url_for('trips.dashboard'))
        else:
            return redirect(url_for('main.dashboard')) # Fallback

    # Cria uma instância do formulário de login
    form = LoginForm()
    # Se o formulário for enviado e for válido
    if form.validate_on_submit():
        current_app.logger.info(f"Tentativa de login: username={form.username.data}")
        # Busca o usuário pelo nome de usuário
        user = User.query.filter_by(username=form.username.data).first()
        # Verifica se o usuário existe e se a senha está correta
        if user is None:
            current_app.logger.warning(f"Tentativa de login falhou: Usuário '{form.username.data}' não encontrado.")
            flash('Nome de usuário ou senha inválidos')
            return redirect(url_for('auth.login'))
        if not user.check_password(form.password.data):
            current_app.logger.warning(f"Tentativa de login falhou para '{form.username.data}': Senha incorreta.")
            flash('Nome de usuário ou senha inválidos')
            return redirect(url_for('auth.login'))

        # Autentica o usuário
        current_app.logger.info(f"Login bem-sucedido para o usuário: {user.username} (Tipo: {user.type})")
        login_user(user, remember=form.remember_me.data)

        # Redireciona para a próxima página (se houver) ou para o dashboard específico
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            # Se não houver 'next' ou for um URL externo, redireciona para o dashboard padrão do tipo de usuário
            if user.type == 'manager':
                next_page = url_for('reports.dashboard')
            elif user.type == 'warehouse':
                next_page = url_for('trips.dashboard')
            else:
                next_page = url_for('main.dashboard') # Fallback

        current_app.logger.info(f"Redirecionando para: {next_page}")
        return redirect(next_page)

    # Renderiza o template de login com o formulário
    return render_template('auth/login.html', title='Login', form=form)

@bp.route('/logout')
def logout():
    """
    Rota para logout de usuários.
    Encerra a sessão do usuário atual e redireciona para a página de login.
    """
    if current_user.is_authenticated:
        current_app.logger.info(f"Usuário {current_user.username} fez logout.")
    logout_user()
    flash('Você foi desconectado com sucesso.')
    return redirect(url_for('auth.login')) # Redirecionar para a página de login após logout

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Rota para registro de novos usuários.
    GET: Exibe o formulário de registro
    POST: Processa o formulário enviado e cria um novo usuário
    """
    # Se o usuário já estiver autenticado, redireciona para o dashboard
    if current_user.is_authenticated:
        current_app.logger.info(f"Usuário {current_user.username} já autenticado, tentando acessar registro.")
        # Redirecionamento inteligente para o dashboard correto
        if current_user.type == 'manager':
            return redirect(url_for('reports.dashboard'))
        elif current_user.type == 'warehouse':
            return redirect(url_for('trips.dashboard'))
        else:
            return redirect(url_for('main.dashboard')) # Fallback

    # Cria uma instância do formulário de registro
    form = RegistrationForm()
    # Se o formulário for enviado e for válido
    if form.validate_on_submit():
        # Cria um novo usuário com os dados do formulário, incluindo o email
        user = User(username=form.username.data, email=form.email.data, type=form.type.data)
        user.set_password(form.password.data)
        # Adiciona o usuário ao banco de dados
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"Novo usuário registrado: {user.username} (Tipo: {user.type})")
        flash('Parabéns, você está registrado! Por favor, faça login.')
        return redirect(url_for('auth.login'))

    # Renderiza o template de registro com o formulário
    return render_template('auth/register.html', title='Registro', form=form)

