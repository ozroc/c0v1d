import os

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

import pandas

from bokeh.plotting import figure
from bokeh.embed import components


app = Flask(__name__)



DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:////tmp/flask_app.db')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db_engine =  create_engine(DATABASE_URL)


@app.route('/', methods=['GET'])
def index():
  df = pandas.read_sql_table('global', db_engine)
  countries = set(df.location)
  country_string=''
  for i in sorted(countries):
    country_string+='<br><a href="/plot/' + i + '">%s</a>' % i
  return country_string

@app.route('/plot/<country>', methods=['POST', 'GET'])
def plot(country):
  df = pandas.read_sql_table('global', db_engine)
  dataframe = df[df['location'] == country].set_index('days_from_first_c')
  dataframe= dataframe[dataframe.index != 0]
  dataframe['I']=dataframe.C-dataframe.R-dataframe.D
  nt=dataframe.C.max()*2
  dataframe['S']=nt-dataframe['I']
  for i in 'RCDIS':
    dataframe['diff_%s' % i] = dataframe[i].rolling(3).mean().diff()
  dataframe['beta']=(dataframe.C.rolling(3).mean().diff()*nt/(dataframe.S.rolling(3).mean()*dataframe.I.rolling(3).mean()))
  dataframe['gamma_r']=(dataframe.R.rolling(3).mean().diff()/dataframe.I.rolling(3).mean())
  dataframe['gamma_d']=(dataframe.D.rolling(3).mean().diff()/dataframe.I.rolling(3).mean())
  dataframe = dataframe.reset_index()
  p = figure(title='Totals', x_axis_type='datetime', plot_width=900, plot_height=300,tools='hover,pan,wheel_zoom,box_zoom,reset')
  p.line(dataframe.date, dataframe.C, legend_label='Confirmed', color='blue')
  p.line(dataframe.date, dataframe.I, legend_label='Infected', color='orange')
  p.line(dataframe.date, dataframe.D, legend_label='Deaths', color='red')
  p.line(dataframe.date, dataframe.R, legend_label='Recovered', color='green')
  p.legend.location = 'top_left'
  script, div = components(p)

  p = figure(title='Daily increments', x_axis_type='datetime', plot_width=900, plot_height=300,tools='hover,pan,wheel_zoom,box_zoom,reset')
  p.line(dataframe.date, dataframe.diff_C, legend_label='Confirmed', color='blue')
  p.line(dataframe.date, dataframe.diff_I, legend_label='Infected', color='orange')
  p.line(dataframe.date, dataframe.diff_D, legend_label='Deaths', color='red')
  p.line(dataframe.date, dataframe.diff_R, legend_label='Recovered', color='green')
  p.legend.location = 'top_left'
  script2, div2 = components(p)
  script+='<p>'+script2
  div+='<p>'+div2

  # p = figure(title='SIRD parameters', x_axis_type='datetime', plot_width=900, plot_height=300,)
  # p.line(dataframe.date, dataframe.beta, legend_label='Beta', color='blue')
  # p.line(dataframe.date, dataframe.gamma_d, legend_label='Gamma_d', color='red')
  # p.line(dataframe.date, dataframe.gamma_r, legend_label='Gamma_r', color='green')
  # p.legend.location = 'top_left'
  # script2, div2 = components(p)
  # script+='<p>'+script2
  # div+='<p>'+div2
  
  df = df[df.location == country][df.days_from_first_c > 0]
  df.index = df.date
  df = df[['days_from_first_c', 'C', 'R', 'D']]
  
  return render_template('layout.html.jinja',
                         bokeh_script = script,
                         bokeh_figures = div,
                         datatable = df.to_html(classes = '" id = "dataframe')
  )

@app.route('/update', methods=['GET'])
def update():
  Confirmed = pandas.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv')
  Deaths = pandas.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv')
  Recovered = pandas.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv')
  for i in (Confirmed, Recovered, Deaths):
    PROVINCES = i[['Province/State', 'Country/Region', 'Lat', 'Long']].fillna('')
    PROVINCES['Location']= PROVINCES['Country/Region'] + ' ' + PROVINCES['Province/State']
    PROVINCES['Location'] = PROVINCES['Location'].apply(lambda x: x.strip())
    i.index = PROVINCES['Location']
    
  dates = Deaths.columns[4:]
  #  location, long, lat, date, c, d, r
  data={'location':[],'date':[],'long':[],'lat':[],'C':[],'D':[],'R':[], 'days_from_first_c': []}
  days_from_first={}
  for i in Confirmed.index:
    if i not in Recovered.index or i not in Deaths.index:
        continue
    days_from_first[i] = 0
    for d in dates:          
        data['location'].append(i)
        data['lat'].append(Recovered['Lat'][i])
        data['long'].append(Recovered['Long'][i])
        data['date'].append(d)
        data['C'].append(Confirmed[d][i])
        data['R'].append(Recovered[d][i])
        data['D'].append(Deaths[d][i])
        data['days_from_first_c'].append(days_from_first.get(i, 0))
        if Confirmed[d][i] > 100:
            days_from_first[i] += 1
  df = pandas.DataFrame.from_dict(data)
  df['date']=pandas.to_datetime(df['date'])
  df.to_sql('global', db_engine)
  return 'Updated OK'

if __name__ == '__main__':
  #db_engine.create_all()
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
