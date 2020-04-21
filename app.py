import os

from flask import Flask, render_template, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from tornado.ioloop import IOLoop
from threading import Thread

from bokeh.server.server import Server
from bokeh.embed import server_document



from covid import Covid
from covid.model import get_model_bk

app = Flask(__name__)

port = int(os.environ.get('PORT', 5000))
bokeh_port = int(os.environ.get('BOKEH_PORT', 9090))

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:////tmp/flask_app.db')
DATABASE_URL = 'sqlite:////tmp/flask_app.db'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db_engine =  create_engine(DATABASE_URL)

COVID = Covid(db_engine)
    
@app.route('/', methods=['GET'])
def index():
    script, div = COVID.plot_map()
    return render_template('index.html.jinja', script = script, div = div, countries = list(map(lambda x: x['name'], COVID.countries)))


@app.route('/plot/<country>', methods=['POST', 'GET'])
def plot(country):

  script, div = COVID.plot_country(country)
  df = COVID.get_country(country)
  df = df[df.days_from_first_c > 0]
  df.index = df.date
  df = df[['days_from_first_c', 'C', 'R', 'D', 'I']]
  df.columns = ['Days from first 100 cases', 'Confirmed', 'Recovered', 'Deaths', 'Infected']
  return render_template('layout.html.jinja',
                         bokeh_script = script,
                         bokeh_figures = div,
                         datatable = df.to_html(classes = '" id = "dataframe',),
                         countries = COVID.countries
  )

@app.route('/update', methods=['GET'])
def update():
  COVID.update()
  return 'Updated OK'


@app.route('/model', methods=['GET'])
def model():
    script = server_document('http://0.0.0.0:%s/bkapp' % bokeh_port)
    div=''
    return render_template('index.html.jinja', script = div, div = script, countries = COVID.countries)

model_bk = get_model_bk(COVID)

def bk_worker():
    # Can't pass num_procs > 1 in this configuration. If you need to run multiple
    # processes, see e.g. flask_gunicorn_embed.py
    server = Server({'/bkapp': model_bk}, io_loop=IOLoop(), allow_websocket_origin=["0.0.0.0:%s" % port], port=bokeh_port)
    server.start()
    server.io_loop.start()

Thread(target=bk_worker).start()


if __name__ == '__main__':
  app.run(port=port, debug=True)
