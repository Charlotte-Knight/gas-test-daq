from flask import Flask, render_template, redirect, request
import plotly.graph_objs as go
from database import *
import daq_service

app = Flask(__name__)

init_db()
daq_service.start()

@app.route("/")
def index():
    runs = get_runs()
    return render_template("index.html", runs=runs)

@app.route("/start_run", methods=["POST"])
def start_run():
    name = request.form["name"]
    desc = request.form["desc"]
    run_id = create_run(name, desc)
    daq_service.set_run(run_id)
    return redirect("/")

@app.route("/stop_run/<int:run_id>")
def stop_run(run_id):
    end_run(run_id)
    daq_service.set_run(None)
    return redirect("/")

@app.route("/run/<int:run_id>")
def view_run(run_id):
    data = get_measurements(run_id)

    times = [d[0] for d in data]
    p1 = [d[1] for d in data]
    p2 = [d[2] for d in data]
    p3 = [d[3] for d in data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=p1, name="P1"))
    fig.add_trace(go.Scatter(x=times, y=p2, name="P2"))
    fig.add_trace(go.Scatter(x=times, y=p3, name="P3"))

    return render_template(
        "run.html",
        plot=fig.to_html(full_html=False)
    )

@app.route("/pump/<state>")
def pump_control(state):
    daq_service.set_pump(1 if state == "on" else 0)
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
