import random
import re
import string
import psycopg2
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message


app = Flask(__name__)

app.secret_key = '123456'

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] =
app.config['MAIL_PASSWORD'] =
app.config['MAIL_USE_TLS'] = True
mail = Mail(app)

# Función para obtener la conexión a la base de datos
def get_db_connection():
    return psycopg2.connect(
        dbname="ANDES ARTBOL",
        user="postgres",
        password='123456',  
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

            if user and check_password_hash(user[3], contraseña):
                if user[7]:  # Si el usuario está verificado
                    session['usuario_id'] = user[0]
                    flash('Inicio de sesión exitoso', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Debes verificar tu correo antes de iniciar sesión.', 'warning')
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

# Ruta para verificar el código de verificación 
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        telefono = request.form['telefono']
        rol_id = request.form['rol_id']
        comunidad_id = request.form['comunidad_id']
        
        # Validaciones
        if not nombre or not correo or not contraseña or not telefono or not rol_id or not comunidad_id:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('registro.html', roles=roles, comunidades=comunidades)

        if not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            flash('Correo inválido', 'danger')
            return render_template('registro.html', roles=roles, comunidades=comunidades)

        if not telefono.isdigit():
            flash('El teléfono debe contener solo números', 'danger')
            return render_template('registro.html', roles=roles, comunidades=comunidades)

        if not validar_contraseña(contraseña):
            flash('La contraseña debe tener al menos 8 caracteres, incluyendo una mayúscula, una minúscula, un número y un símbolo especial.', 'danger')
            return render_template('registro.html', roles=roles, comunidades=comunidades)

        contraseña = generate_password_hash(contraseña)

        # Generar código de verificación
        codigo_verificacion = generar_codigo()

        # Insertar datos en la base de datos
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO usuarios (nombre, correo, contraseña, telefono, rol_id, comunidad_id, codigo_verificacion, verificado) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                (nombre, correo, contraseña, telefono, rol_id, comunidad_id, codigo_verificacion, False)
            )
            conn.commit()

            # Enviar el correo de verificación
            msg = Message('Verificación de cuenta', sender=app.config['MAIL_USERNAME'], recipients=[correo])
            msg.body = f'Tu código de verificación es: {codigo_verificacion}'
            mail.send(msg)

            flash('Se ha enviado un código de verificación a tu correo.', 'success')
            session['correo_verificacion'] = correo  # Guardar correo en la sesión
            return redirect(url_for('verificar_codigo_registro'))

        except Exception as e:
            flash(f'Error al registrar el usuario: {str(e)}', 'danger')
            if conn:
                conn.rollback()

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    # Cargar roles y comunidades
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT rol_id, nombre FROM roles")  # Asumiendo que tienes una tabla 'roles'
    roles = cur.fetchall()

    cur.execute("SELECT comunidad_id, nombre FROM comunidades")  # Asumiendo que tienes una tabla 'comunidades'
    comunidades = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('registro.html', roles=roles, comunidades=comunidades)


@app.route('/verificar_codigo_recuperacion', methods=['GET', 'POST'])
def verificar_codigo_recuperacion():
    if request.method == 'POST':
        codigo = request.form['codigo']

        if codigo == session.get('codigo'):
            flash('Código verificado correctamente', 'success')
            return redirect(url_for('cambiar_contraseña'))
        else:
            flash('Código incorrecto', 'danger')

    return render_template('verificar_codigo_recuperacion.html')

@app.route('/verificar_codigo_registro', methods=['GET', 'POST'])
def verificar_codigo_registro():
    
        correo = session.get('correo_verificacion')
        
        if request.method == 'POST':
            codigo_ingresado = request.form['codigo']

        # Verificar el código en la base de datos
            conn = None
            cur = None
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT codigo_verificacion FROM usuarios WHERE correo = %s", (correo,))
                codigo_correcto = cur.fetchone()[0]

                if codigo_correcto == codigo_ingresado:
                # Código verificado, actualizar usuario como verificado
                    cur.execute("UPDATE usuarios SET verificado = TRUE WHERE correo = %s", (correo,))
                    conn.commit()
                    flash('Cuenta verificada correctamente.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash('El código ingresado es incorrecto.', 'danger')

            except Exception as e:
                flash(f'Error al verificar el código: {str(e)}', 'danger')

            finally:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
        return render_template('verificar_codigo_registro.html')

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
            cur.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
            user = cur.fetchone()

            if user:
                codigo = generar_codigo()
                session['codigo'] = codigo
                session['usuario_id'] = user[0]

                msg = Message('Código de recuperación', sender=app.config['MAIL_USERNAME'], recipients=[correo])
                msg.html = render_template('correo_codigo.html', codigo=codigo)
                mail.send(msg)
                
                flash('Código de recuperación enviado a tu correo.', 'success')
                print('Se envio el correo pero no se redirige')
                return redirect(url_for('verificar_codigo_recuperacion'))

            else:
                flash('El correo no está registrado.', 'danger')

        except Exception as e:
            flash(f'Error al enviar el código de recuperación: {str(e)}', 'danger')

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    
    return render_template('recuperar.html')

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


@app.route('/nueva_contraseña', methods=['GET', 'POST'])
def nueva_contraseña():
    if request.method == 'POST':
        nueva_contraseña = request.form['nueva_contraseña']
        confirmacion_contraseña = request.form['confirmacion_contraseña']

        if nueva_contraseña != confirmacion_contraseña:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('nueva_contraseña.html')

        if not validar_contraseña(nueva_contraseña):
            flash('La nueva contraseña no cumple con los requisitos de seguridad', 'danger')
            return render_template('nueva_contraseña.html')

        # Encriptar y actualizar la contraseña
        nueva_contraseña_hash = generate_password_hash(nueva_contraseña)

        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("UPDATE Usuarios SET contraseña = %s WHERE id = %s", (nueva_contraseña_hash, session['usuario_id']))
            conn.commit()

            flash('Contraseña actualizada correctamente', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Error al actualizar la contraseña: {str(e)}', 'danger')

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('nueva_contraseña.html')

# Función para generar códigos de verificación aleatorios
def generar_codigo(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

if __name__ == '__main__':
    app.run(debug=True)
