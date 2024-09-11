from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from flask_mail import Mail, Message
import random
import string

app = Flask(__name__)
app.secret_key = '123456'

# Configuración de conexión a PostgreSQL
conn = psycopg2.connect(
    dbname="ANDES ARTBOL",
    user="postgres",
    password="123456",
    host="localhost"
)

@app.route('/')
def home():
    return redirect(url_for('login'))

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587 
app.config['MAIL_USERNAME'] = 'dgutierrezo@fcpn.edu.bo'
app.config['MAIL_PASSWORD'] = 'mtaq gtkd qeqs zbxd'
app.config['MAIL_USE_TLS'] = True 
app.config['MAIL_USE_SSL'] = False  

mail = Mail(app)

# Ruta de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        
        cur = conn.cursor()
        cur.execute("SELECT * FROM Usuarios WHERE correo = %s AND contraseña = %s", (correo, contraseña))
        user = cur.fetchone()
        
        if user:
            session['usuario_id'] = user[0]
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('dashboard'))
        
        else:
            flash('Correo o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    # Limpiar la sesión
    session.clear()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('login'))

# Ruta del dashboard
@app.route('/dashboard')
def dashboard():
    # Verifica si el usuario está logueado
    if 'usuario_id' not in session:
        flash('Por favor, inicia sesión primero.', 'warning')
        return redirect(url_for('login'))
    
    # Aquí puedes pasar información al template del dashboard
    return render_template('dashboard.html')

@app.route('/politicas')
def politicas():
    return render_template('politicas.html')


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
        
        cur = conn.cursor()
        cur.execute("INSERT INTO Usuarios (nombre, correo, contraseña, telefono, rol_id, comunidad_id) VALUES (%s, %s, %s, %s, %s, %s)", (nombre, correo, contraseña, telefono, rol_id, comunidad_id))
        conn.commit()
        
        flash('Registro exitoso, ahora puedes iniciar sesión', 'success')
        return redirect(url_for('login'))
        
    return render_template('registro.html')

# Ruta para recuperación de contraseña
def generar_codigo():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        correo = request.form['correo']
        
        cur = conn.cursor()
        cur.execute("SELECT * FROM Usuarios WHERE correo = %s", (correo,))
        user = cur.fetchone()
        
        if user:
            codigo = generar_codigo()
            session['codigo'] = codigo
            session['usuario_id'] = user[0]
            
            msg = Message('Código de recuperación', sender='dgutierrezo@fcpn.edu.bo', recipients=[correo])
            msg.body = f'Tu código de recuperación es: {codigo}'
            mail.send(msg)
            
            flash('Código de recuperación enviado a tu correo', 'success')
            return redirect(url_for('verificar_codigo'))
        else:
            flash('Correo no registrado', 'danger')
    
    return render_template('recuperar.html')

#Verificación de código

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


# Cambio de contraseña
@app.route('/cambiar_contraseña', methods=['GET', 'POST'])
def cambiar_contraseña():
    if request.method == 'POST':
        nueva_contraseña = request.form['nueva_contraseña']
        usuario_id = session.get('usuario_id')
        
        cur = conn.cursor()
        cur.execute("UPDATE Usuarios SET contraseña = %s WHERE usuario_id = %s", (nueva_contraseña, usuario_id))
        conn.commit()
        
        flash('Contraseña cambiada con éxito', 'success')
        return redirect(url_for('login'))
    
    return render_template('cambiar_contraseña.html')

if __name__ == '__main__':
    app.run(debug=True)
