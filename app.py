from flask import Flask, render_template, jsonify
import plotly.graph_objs as go
import csv

app = Flask(__name__)

# Путь к файлу с данными
CSV_FILE = 'data.csv'

def get_data():
    timestamps = []
    avg_values = []
    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Пропустить заголовок
        for row in reader:
            timestamps.append(row[0])
            avg_values.append(float(row[1]))
    return timestamps, avg_values

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    timestamps, avg_values = get_data()
    return jsonify(timestamps=timestamps, avg_values=avg_values)

if __name__ == '__main__':
    app.run(debug=True)
