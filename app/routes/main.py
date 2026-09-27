# app/routes/main.py
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
@login_required # Garante que apenas usuários autenticados acessem esta rota
def index():
    """
    Rota principal que redireciona para o dashboard apropriado
    com base no tipo de usuário.
    """
    # Como @login_required já garante que o usuário está autenticado,
    # podemos remover a verificação 'if current_user.is_authenticated:'.
    # A lógica de redirecionamento por tipo de usuário é executada diretamente.
    if current_user.type == 'warehouse':
        return redirect(url_for('trips.dashboard'))
    elif current_user.type == 'manager':
        return redirect(url_for('reports.dashboard'))
    # Se houver outros tipos de usuário ou um fallback geral, você pode adicionar aqui.
    # Por exemplo, um dashboard padrão para tipos não especificados.
    return redirect(url_for('main.dashboard_default')) # Exemplo de fallback para um dashboard genérico

# Exemplo de um dashboard padrão caso o tipo de usuário não seja 'warehouse' ou 'manager'
# Você precisaria criar a rota e o template correspondentes.
@bp.route('/dashboard_default')
@login_required
def dashboard_default():
    return render_template('main/dashboard_default.html', title='Dashboard')


@bp.route('/about')
def about():
    """
    Rota para a página "Sobre".
    """
    return render_template('main/about.html', title='Sobre')

# Você pode adicionar outras rotas comuns aqui, como contato, etc.
@bp.route('/profile')
@login_required
def profile():
    """
    Rota para exibir o perfil do usuário logado.
    """
    # Você pode passar o objeto current_user diretamente para o template
    return render_template('main/profile.html', title='Perfil do Usuário', user=current_user)