from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    """Главная страница - открывает index.html"""
    return render_template('index.html')

@app.route('/<path:path>')
def catch_all(path):
    """Перехватывает все остальные пути и тоже открывает index.html"""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
