import os

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

from covid import Covid

app = Flask(__name__)


DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:////tmp/flask_app.db')
DATABASE_URL = 'sqlite:////tmp/flask_app.db'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db_engine =  create_engine(DATABASE_URL)

COVID = Covid(db_engine)
    
@app.route('/', methods=['GET'])
def index():
    
    return render_template('index.html.jinja', countries = COVID.countries)


@app.route('/plot/<country>', methods=['POST', 'GET'])
def plot(country):

  script1, div1 = COVID.plot_absolutes(country)
  script2, div2 = COVID.plot_diffs(country)
  
  df = COVID.get_country(country)
  df = df[df.days_from_first_c > 0]
  df.index = df.date
  df = df[['days_from_first_c', 'C', 'R', 'D', 'I']]
  df.columns = ['Days from first 100 cases', 'Confirmed', 'Recovered', 'Deaths', 'Infected']
  return render_template('layout.html.jinja',
                         bokeh_script = script1+script2,
                         bokeh_figures = div1+div2,
                         datatable = df.to_html(classes = '" id = "dataframe')
  )

@app.route('/update', methods=['GET'])
def update():
  COVID.update()
  return 'Updated OK'


if __name__ == '__main__':
  #db_engine.create_all()
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
