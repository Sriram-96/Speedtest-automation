import speedtest
import sqlite3
import time
import datetime
import platform
import smtplib
import socks
import socket
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import schedule
import sys, os
import logging
import configparser
import base64
from twilio.rest import Client
from requests import Request, Session
from twilio.http import HttpClient
from twilio.http.response import Response
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def get_speedtest_results():
    s = speedtest.Speedtest()
    s.get_best_server()
    s.download()
    s.upload()
    results_dict = s.results.dict()
    download_speed=results_dict['download']
    upload_speed=results_dict['upload']
    download_speed=round(download_speed/1000000)
    upload_speed=round(upload_speed/1000000)
    print_log('Speedtest result fetched. Download speed : '+ str(download_speed) + 'Mbps , Upload speed : ' + str(upload_speed) + 'Mbps')
    return download_speed,upload_speed

def create_table():
    conn = sqlite3.connect('speedtest.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS SPEED
         (TIME TIMESTAMP NOT NULL,
         DOWNLOAD INT NOT NULL,
         UPLOAD INT NOT NULL);''')
    conn.execute('''CREATE TABLE IF NOT EXISTS SPEED_HISTORY
         (TIME TIMESTAMP NOT NULL,
         AVERAGE_DOWNLOAD INT NOT NULL,
         AVERAGE_UPLOAD INT NOT NULL,
         RECORDS INT NOT NULL);''')
    conn.execute('''CREATE TABLE IF NOT EXISTS SCHEDULER
         (TIME TIMESTAMP NOT NULL,
         IS_TIME_PASSED INT NOT NULL);''')
    conn.close()
    
def insert_to_db(download_speed,upload_speed):
    conn = sqlite3.connect('speedtest.db')
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("INSERT INTO SPEED (TIME,DOWNLOAD,UPLOAD) \
      VALUES (?,?,?)",(timestamp,download_speed,upload_speed))
    conn.commit()
    conn.close()
    print_log('Inserted to DB')

def send_sms(download_speed,upload_speed,records):
    account_sid = fetch_from_config_file('SMS-CONFIG','TWILIO_ACCOUNT_SID')
    auth_token = fetch_from_config_file('SMS-CONFIG','TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)
    text = 'Your PC ' + platform.node() + ' had an average Download speed of ' + str(download_speed) + ' Mbps and an average Upload speed of ' + str(upload_speed) + ' Mbps, out of ' + str(records) + ' readings'
    message = client.messages.create(body=text,from_=fetch_from_config_file('SMS-CONFIG','TWILIO_FROM_NUMBER'),to=fetch_from_config_file('SMS-CONFIG','TWILIO_TO_NUMBER'))
    print_log('SMS Sent!')

def send_email(download_speed,upload_speed,records):
    fromaddr = fetch_from_config_file('EMAIL-CONFIG','FROM_EMAIL_ID')
    toaddr = fetch_from_config_file('EMAIL-CONFIG','TO_EMAIL_ID')
    attachment = 'graphs/' + datetime.datetime.today().strftime('%Y-%m-%d') + '.png'
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Speedtest Automation Alert!"
    body = 'Your PC ' + platform.node() + ' had an average Download speed of ' + str(download_speed) + ' Mbps and an average Upload speed of ' + str(upload_speed) + ' Mbps, out of ' + str(records) + ' readings'
    msg.attach(MIMEText('<b>%s</b><br><img src="cid:%s"><br>' % (body, attachment), 'html'))
    fp = open(attachment, 'rb')                                              
    img = MIMEImage(fp.read())
    fp.close()
    img.add_header('Content-ID', '<{}>'.format(attachment))
    msg.attach(img)
    server = smtplib.SMTP(fetch_from_config_file('EMAIL-CONFIG','SMTP_SERVER_HOST'),int(fetch_from_config_file('EMAIL-CONFIG','SMTP_SERVER_PORT')))
    server.starttls()
    encoded_password_in_string=fetch_from_config_file('EMAIL-CONFIG','EMAIL_PASSWORD')
    encoded_password_in_bytes=str.encode(encoded_password_in_string)
    decoded_password_in_bytes=base64.b64decode(encoded_password_in_bytes)
    decoded_password_in_string=bytes.decode(decoded_password_in_bytes)
    server.login(fromaddr,decoded_password_in_string)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()
    print_log('Email Sent with attachment!')

def fetch_from_db():
    conn = sqlite3.connect('speedtest.db')
    cursor = conn.execute("SELECT TIME,DOWNLOAD,UPLOAD from SPEED")
    time=[]
    duload=[]
    download=[]
    upload=[]
    for row in cursor:
        time.append(row[0])
        download.append(row[1])
        upload.append(row[2])
        temp=[]
        temp.append(row[1])
        temp.append(row[2])
        duload.append(temp)
    conn.close()
    records = len(time)
    if records>0:
        avg_download_speed = round(np.mean(download))
        avg_upload_speed = round(np.mean(upload))
    else:
        avg_download_speed=0
        avg_upload_speed=0
    p = 'Fetched ' + str(records) + ' records from DB'
    print_log(p)
    return time,duload,avg_download_speed,avg_upload_speed,records

def plot_graph_and_save(time,duload):
    tt=[]
    for i in range(len(time)):
        temp = time[i].split(' ')
        tt.append(temp[1])
    df = pd.DataFrame(duload,tt,columns=['Download','Upload'],dtype=int)
    df.plot()
    img = plt.gcf()
    path = 'graphs/' + datetime.datetime.today().strftime('%Y-%m-%d') + '.png'
    img.savefig(path)
    print_log('Graph plotted and saved')

def insert_to_history_db(avg_download_speed,avg_upload_speed,records):
    conn = sqlite3.connect('speedtest.db')
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("INSERT INTO SPEED_HISTORY (TIME,AVERAGE_DOWNLOAD,AVERAGE_UPLOAD,RECORDS) \
      VALUES (?,?,?,?)",(timestamp,avg_download_speed,avg_upload_speed,records))
    conn.commit()
    conn.close()
    print_log('Inserted to History DB')

def delete_from_db():
    conn = sqlite3.connect('speedtest.db')
    conn.execute("DELETE from SPEED;")
    conn.commit()
    conn.close()
    print_log('Deleted from Speed DB')

def delete_from_scheduler_db():
    conn = sqlite3.connect('speedtest.db')
    conn.execute("DELETE from SCHEDULER;")
    conn.commit()
    conn.close()
    print_log('Deleted from Sheduler DB')

def insert_to_scheduler_db(val):
    delete_from_scheduler_db()
    conn = sqlite3.connect('speedtest.db')
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("INSERT INTO SCHEDULER (TIME,IS_TIME_PASSED) \
      VALUES (?,?)",(timestamp,val))
    conn.commit()
    conn.close()
    print_log('Inserted to Scheduler DB')

def check_to_run_once():
    conn = sqlite3.connect('speedtest.db')
    cursor = conn.execute("SELECT IS_TIME_PASSED from SCHEDULER")
    for row in cursor:
        val=row[0]
    conn.close()
    if val==0:
        insert_to_scheduler_db(1)
        run_once()

def fetch_from_config_file(config_name,key):
    config = configparser.ConfigParser()
    config.read(r'properties.txt')
    return str(config[config_name][key])

def print_log(line):
    logging.basicConfig(filename='main.log',level=logging.INFO)
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    if line=='\n':
        logging.info(line)
    else:
        logging.info(timestamp + ' : ' + line)

def run_everytime():
    try:
        download_speed,upload_speed = get_speedtest_results()
        create_table()
        insert_to_db(download_speed,upload_speed)
        now = datetime.datetime.now()
        time_to_send=fetch_from_config_file('POLLING-CONFIG','TIME_TO_SEND_DAILY_REPORT').split(':')
        time_to_send_hh=int(time_to_send[0])
        time_to_send_mm=int(time_to_send[1])
        if now.hour<=time_to_send_hh and now.minute<time_to_send_mm:
            insert_to_scheduler_db(0)
        else:
            check_to_run_once()
        print_log('\n')
    except Exception as e:
        print_log('Error contacting Speedtest server with exception : ' + str(e))
        print_log('\n')

def run_once():
    try:
        time,duload,avg_download_speed,avg_upload_speed,records = fetch_from_db()
        if records!=0:
            plot_graph_and_save(time,duload)
            if fetch_from_config_file('SMS-CONFIG','SEND_SMS')=='Y':
                send_sms(avg_download_speed,avg_upload_speed,records)
            else:
                print_log('SMS not sent, since SEND_SMS flag is not set to Y')
            if fetch_from_config_file('EMAIL-CONFIG','SEND_EMAIL')=='Y':
                send_email(avg_download_speed,avg_upload_speed,records)
            else:
                print_log('Email not sent, since SEND_EMAIL flag is not set to Y')
            insert_to_history_db(avg_download_speed,avg_upload_speed,records)
            delete_from_db()
            print_log('\n')
        else:
            print_log('SMS/Email not sent, since no records found')
            print_log('\n')
    except Exception as e:
        print_log('Error contacting SMS/Email server with exception : ' + str(e))
        print_log('\n')

##run_everytime()
##run_once()
print('Speedtest Automation running...')
schedule.every(int(fetch_from_config_file('POLLING-CONFIG','NETWORK_POLLING_INTERVAL_IN_MINS'))).minutes.do(run_everytime)

while True:
    schedule.run_pending()
    time.sleep(1)

