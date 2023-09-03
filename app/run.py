from app import create_app
# import app.config as config

app = create_app()

# Set app configurations from config.py
# app.secret_key = config.SECRET_KEY
# app.config['SESSION_TYPE'] = config.SESSION_TYPE

if __name__ == '__main__':
    app.run(debug=True)
