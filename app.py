from flask import Flask, render_template, jsonify
import csv
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

CSV_FILE = 'data.csv'

def get_latest_data():
    if not os.path.exists(CSV_FILE):
        return "No data available."
    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Пропустить заголовок
        rows = list(reader)
        if rows:
            return rows[-1]  # Последняя запись
        else:
            return "No data available."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    timestamps, avg_values = get_data()
    return jsonify(timestamps=timestamps, avg_values=avg_values)

@app.route('/status')
def status():
    latest_data = get_latest_data()
    return jsonify({"status": "running", "latest_data": latest_data})

if __name__ == '__main__':
    logger.info('Запуск Flask приложения')
    app.run(debug=True)
