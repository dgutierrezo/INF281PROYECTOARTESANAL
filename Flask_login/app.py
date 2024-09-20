import os
import random
import re
import string
import psycopg2
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from jinja2 import Template
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

app = Flask(__name__)

# Cargar la clave secreta desde una variable de entorno
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')  # Establecer una clave por defecto solo en desarrollo

# Configuración de Flask-Mail utilizando variables de entorno
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 
app.config['MAIL_PASSWORD'] = 
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

# Función para obtener la conexión a la base de datos
def get_db_connection():
    return psycopg2.connect(
        dbname="ANDES ARTBOL",
        user="postgres",
        password=os.getenv('DB_PASSWORD', '123456'),  # Cargar contraseña de la DB desde una variable de entorno
        host="localhost"
    )

# Decorador para verificar si el usuario está autenticado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor, inicia sesión primero.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ruta principal
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/politicas')
def politicas():
    return render_template('politicas.html')

# Ruta de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']

        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Usuarios WHERE correo = %s", (correo,))
            user = cur.fetchone()

            if user and check_password_hash(user[3], contraseña):  # Asegúrate de que el índice de la contraseña es correcto
                session['usuario_id'] = user[0]
                flash('Inicio de sesión exitoso', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Correo o contraseña incorrectos', 'danger')

        except Exception as e:
            flash(f'Error de conexión a la base de datos: {str(e)}', 'danger')

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('login.html')
# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('login'))

# Ruta del dashboard protegida por el decorador login_required
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Ruta de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        telefono = request.form['telefono']
        rol_id = request.form['rol_id']
        comunidad_id = request.form['comunidad_id']

        # Verificar que los campos no estén vacíos
        if not nombre or not correo or not contraseña or not telefono or not rol_id or not comunidad_id:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('registro.html')

        # Validar correo
        if not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            flash('Correo inválido', 'danger')
            return render_template('registro.html')

        # Validar teléfono
        if not telefono.isdigit():
            flash('El teléfono debe contener solo números', 'danger')
            return render_template('registro.html')

        # Validar la contraseña
        if not validar_contraseña(contraseña):
            flash('La contraseña debe tener al menos 8 caracteres, incluyendo una mayúscula, una minúscula, un número y un símbolo especial.', 'danger')
            return render_template('registro.html')

        # Encriptar la contraseña
        contraseña = generate_password_hash(contraseña)

        # Insertar datos en la base de datos
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO usuarios (nombre, correo, contraseña, telefono, rol_id, comunidad_id) VALUES (%s, %s, %s, %s, %s, %s)", 
                (nombre, correo, contraseña, telefono, rol_id, comunidad_id)
            )
            conn.commit()

            flash('Registro exitoso, ahora puedes iniciar sesión', 'success')
            return redirect(url_for('login'))  # Redirigir a la página de login

        except Exception as e:
            flash(f'Error al registrar el usuario: {str(e)}', 'danger')
            if conn:
                conn.rollback()

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('registro.html')

# Función para validar la contraseña
def validar_contraseña(contraseña):
    if len(contraseña) < 8:
        return False
    if not any(char.isdigit() for char in contraseña):
        return False
    if not any(char.isupper() for char in contraseña):
        return False
    if not any(char.islower() for char in contraseña):
        return False
    if not any(char in "!@#$%^&*()_+" for char in contraseña):
        return False
    return True

# Ruta para recuperación de contraseña
@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        correo = request.form['correo']

        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Usuarios WHERE correo = %s", (correo,))
            user = cur.fetchone()

            if user:
                codigo = generar_codigo()
                session['codigo'] = codigo
                session['usuario_id'] = user[0]

                # Leer el archivo de plantilla HTML
                template_path = os.path.join('templates', 'correo_codigo.html')
                with open(template_path, 'r', encoding='utf-8') as file:
                    template = Template(file.read())
                
                # Renderizar el contenido del HTML con el código
                msg_body = template.render(codigo=codigo)

                msg = Message('Código de recuperación', sender='dgutierrezo@fcpn.edu.bo', recipients=[correo])
                msg.html = msg_body
                msg.charset = 'utf-8'  # Asegúrate de que el charset sea UTF-8
                mail.send(msg)

                flash('Código de recuperación enviado a tu correo', 'success')
                return redirect(url_for('verificar_codigo'))

            else:
                flash('Correo no registrado', 'danger')

        except Exception as e:
            flash(f'Error de conexión a la base de datos: {str(e)}', 'danger')

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('recuperar.html')

# Ruta para verificar el código de recuperación
@app.route('/verificar_codigo', methods=['GET', 'POST'])
def verificar_codigo():
    if request.method == 'POST':
        codigo = request.form['codigo']

        if codigo == session.get('codigo'):
            flash('Código verificado correctamente', 'success')
            return redirect(url_for('cambiar_contraseña'))
        else:
            flash('Código incorrecto', 'danger')

    return render_template('verificar_codigo.html')

# Ruta para cambiar la contraseña
@app.route('/cambiar_contraseña', methods=['GET', 'POST'])
def cambiar_contraseña():
    if request.method == 'POST':
        nueva_contraseña = request.form['nueva_contraseña']
        usuario_id = session.get('usuario_id')

        nueva_contraseña_hash = generate_password_hash(nueva_contraseña)

        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE Usuarios SET contraseña = %s WHERE usuario_id = %s", (nueva_contraseña_hash, usuario_id))
            conn.commit()

            flash('Contraseña cambiada con éxito', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Error al cambiar la contraseña: {str(e)}', 'danger')

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('cambiar_contraseña.html')

# Función para generar código aleatorio
def generar_codigo():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

if __name__ == '__main__':
    app.run(debug=True)
