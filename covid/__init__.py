import pandas

from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.models import HoverTool
from cached_property import cached_property_with_ttl

class Covid(object):
    def __init__(self, db_engine):
        self.db = db_engine
        
    def update(self):
        # invalidate the cache
        if 'df' in self.__dict__.keys():
            del self.__dict__['df']
        # get all data
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

        df.to_sql('global', self.db, if_exists='replace')
        return True
    
    @cached_property_with_ttl(ttl=3600)
    def df(self):
        try:
            return pandas.read_sql_table('global', self.db)
        except:
            self.update()
            return pandas.read_sql_table('global', self.db)
  
    @property
    def countries(self): 
        return sorted(set(self.df.location))


    def get_country(self, countryname):
        dataframe = self.df[self.df.location == countryname]
        dataframe['I'] = dataframe.C-dataframe.R-dataframe.D
        nt=dataframe.C.max()*2
        dataframe['S']=nt-dataframe['I']
        for i in 'RCDIS':
            dataframe['diff_%s' % i] = dataframe[i].rolling(3).mean().diff()
            dataframe['beta']=(dataframe.C.rolling(3).mean().diff()*nt/(dataframe.S.rolling(3).mean()*dataframe.I.rolling(3).mean()))
            dataframe['gamma_r']=(dataframe.R.rolling(3).mean().diff()/dataframe.I.rolling(3).mean())
            dataframe['gamma_d']=(dataframe.D.rolling(3).mean().diff()/dataframe.I.rolling(3).mean())
        dataframe = dataframe.reset_index()
        return dataframe

    
    
    def plot_diffs(self, countryname):
        dataframe = self.get_country(countryname)
        htool = HoverTool(
            tooltips=[
                ("date", "@x{%F}"),
                ("value", "@y")
            ],    
            formatters={
                '@x'        : 'datetime'
            },
        )

        p = figure(title='Daily increments for %s' % countryname,
                   x_axis_type='datetime',
                   plot_width=900, plot_height=300,
                   tools='pan,wheel_zoom,box_zoom,reset',
        )
        p.line(dataframe.date, dataframe.diff_C,
               legend_label='Confirmed', color='blue')
        p.line(dataframe.date, dataframe.diff_I,
               legend_label='Infected', color='orange')
        p.line(dataframe.date, dataframe.diff_D,
               legend_label='Deaths', color='red')
        p.line(dataframe.date, dataframe.diff_R,
               legend_label='Recovered', color='green')
        p.legend.location = 'top_left'
        p.legend.click_policy="hide"
        p.add_tools(htool)
        return components(p)

    def plot_absolutes(self, countryname):
        dataframe = self.get_country(countryname)
        htool = HoverTool(
            tooltips=[
                ("date", "@x{%F}"),
                ("value", "@y")
            ],    
            formatters={
                '@x'        : 'datetime'
            }
        )
        p = figure(title='Absolute values for %s' % countryname,
                   x_axis_type='datetime',
                   plot_width=900, plot_height=300,
                   tools='pan,wheel_zoom,box_zoom,reset'
        )
        p.line(dataframe.date, dataframe.C,
               legend_label='Confirmed', color='blue')
        p.line(dataframe.date, dataframe.I,
               legend_label='Infected', color='orange')
        p.line(dataframe.date, dataframe.D,
               legend_label='Deaths', color='red')
        p.line(dataframe.date, dataframe.R,
               legend_label='Recovered', color='green')
        p.legend.location = 'top_left'
        p.legend.click_policy="hide"
        p.add_tools(htool)
        return components(p)

