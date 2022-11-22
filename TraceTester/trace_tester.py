import requests

import pandas as pd
import plotly.express as px

old = 'Previous duration'
new = 'Current duration'

labels = {'Type': ''}
color_map = {old: "blue", new: "orange"}

zipkin_url = 'localhost:30002'
url = 'http://{}/zipkin/api/v2/traces'.format(zipkin_url)


def to_df(trace, is_new):
    result = []
    trace = list(sorted(trace, key=lambda x: x['timestamp'], reverse=True))
    start_timestamp = trace[-1]['timestamp']
    for span in trace:
        if 'shared' in span and span['shared'] is True:
            continue
        server_shared = [s for s in trace if s['kind'] == 'SERVER' and s['id'] == span['id']][0]
        name = server_shared['name']
        duration = int(span['duration']) * 1e6
        version = server_shared['tags']['application.version']
        print(duration)
        data = name + ' [' + str(span['duration']) + ' μs]'
        start = int(span['timestamp']) - int(start_timestamp)
        finish = start + duration
        service_name = server_shared['localEndpoint']['serviceName'].upper()
        type = new if is_new else old

        result.append(dict(Data=data, Start=start, Finish=finish, Service=service_name, Type=type, Duration=duration, Info='', Version=version))
    return result


if __name__ == '__main__':
    old_trace = requests.get(url=url, params={'annotationQuery': 'deployment.version=1.0.0'}).json()
    new_trace = requests.get(url=url, params={'annotationQuery': 'deployment.version=1.0.1'}).json()

    result1 = to_df(new_trace, True)
    result2 = to_df(old_trace, False)

    df = pd.DataFrame(result1 + result2)

    size = int(df['Service'].size / 2)
    current_duration = list(filter(lambda x: 'parentId' not in x, new_trace))[0]['duration']
    previous_duration = list(filter(lambda x: 'parentId' not in x, old_trace))[0]['duration']
    for i in range(size):
        duration_difference = (df['Duration'].values[i] - df['Duration'].values[i + size]) * 1e-6
        start_difference = (df['Duration'].values[i] - df['Duration'].values[i + size])
        df.at[i, 'Data'] = df['Data'].values[i] + '<br>Duration: ' + '%+d' % duration_difference + ' μs'

        new_version = df['Version'].values[i]
        old_version = df['Version'].values[i + size]
        if old_version != new_version:
            df.at[i, 'Service'] = df['Service'].values[i] + '<br>' + old_version + '->' + new_version
            df.at[i + size, 'Service'] = df['Service'].values[i + size] + '<br>' + old_version + '->' + new_version
        else:
            df.at[i, 'Service'] = df['Service'].values[i] + '<br>' + df['Version'].values[i]
            df.at[i + size, 'Service'] = df['Service'].values[i + size] + '<br>' + df['Version'].values[i + size]


    fig = px.timeline(df,
                      x_start="Start",
                      x_end="Finish",
                      y="Service",
                      color="Type",
                      color_discrete_map=color_map,
                      text="Data",
                      labels=labels)

    fig.update_traces(textposition='inside')
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=0.95,
        xanchor="right",
        x=1,
    ),
        xaxis_title="Time [μs]",
        barmode='group',
        title_text='Trace Tester, deployment version: 1->2'
                   '<br><sup>Previous duration: ' + str(previous_duration) + ' μs, Current duration: ' + str(current_duration) + ' μs </sup>',
        title_x=0.5,
        margin=dict(b=20))
    fig.update_xaxes(type='linear', tickformat='digits')

    fig.write_image("fig1.png")
    fig.show()
