import os

from flask import Flask, render_template, render_template_string, request, redirect, url_for
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
    script, div = COVID.plot_map()
    return render_template('index.html.jinja', script = script, div = div, countries = COVID.countries)


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

@app.route('/bokeh', methods=['GET'])
def bokeh():
    import numpy as np

    from bokeh.layouts import column, row
    from bokeh.models import ColumnDataSource, Slider, TextInput
    from bokeh.plotting import figure
    from bokeh.embed import components, server_document


    # Set up data
    N = 200
    x = np.linspace(0, 4*np.pi, N)
    y = np.sin(x)
    source = ColumnDataSource(data=dict(x=x, y=y))


    # Set up plot
    plot = figure(plot_height=400, plot_width=400, title="my sine wave",
                  tools="crosshair,pan,reset,save,wheel_zoom",
                  x_range=[0, 4*np.pi], y_range=[-2.5, 2.5])

    plot.line('x', 'y', source=source, line_width=3, line_alpha=0.6)


    # Set up widgets
    text = TextInput(title="title", value='my sine wave')
    offset = Slider(title="offset", value=0.0, start=-5.0, end=5.0, step=0.1)
    amplitude = Slider(title="amplitude", value=1.0, start=-5.0, end=5.0, step=0.1)
    phase = Slider(title="phase", value=0.0, start=0.0, end=2*np.pi)
    freq = Slider(title="frequency", value=1.0, start=0.1, end=5.1, step=0.1)


    # Set up callbacks
    def update_title(attrname, old, new):
        plot.title.text = text.value

    text.on_change('value', update_title)

    def update_data(attrname, old, new):

        # Get the current slider values
        a = amplitude.value
        b = offset.value
        w = phase.value
        k = freq.value

        # Generate the new curve
        x = np.linspace(0, 4*np.pi, N)
        y = a*np.sin(k*x + w) + b

        source.data = dict(x=x, y=y)

    for w in [offset, amplitude, phase, freq]:
        w.on_change('value', update_data)


    # Set up layouts and add to document
    inputs = column(text, offset, amplitude, phase, freq)
    server = server_document("http://0.0.0.0:5000/bokeh")
    script, div = components(row(inputs, plot, width=800))

    return render_template_string('''{% autoescape false %}<html><head><script src="https://cdn.bokeh.org/bokeh/release/bokeh-2.0.1.min.js"
            crossorigin="anonymous"></script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-2.0.1.min.js"
            crossorigin="anonymous"></script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-2.0.1.min.js"
            crossorigin="anonymous"></script>{{ server }}{{ script }}</head><body>{{ div }}</body></html>{% endautoescape %}''', script = script, div = div, server=server)



if __name__ == '__main__':
  #db_engine.create_all()
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
