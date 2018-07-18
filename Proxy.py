import speedtest
import sqlite3
import time
import datetime
import platform
import smtplib
import socks
import socket
from twilio.rest import Client
from requests import Request, Session
from twilio.http import HttpClient
from twilio.http.response import Response
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class ProxiedTwilioHttpClient(HttpClient):
    def request(self, method, url, params=None, data=None, headers=None, auth=None, timeout=None,allow_redirects=False):
        session = Session()
        session.verify = 'C:/Users/212601214/Desktop/Twilio_certificate_updated.crt'
        session.proxies = {"https" : "http://cis-india-pitc-bangalorez.proxy.corporate.ge.com:80"}
        request = Request(method.upper(), url, params=params, data=data, headers=headers, auth=auth)
        prepped_request = session.prepare_request(request)
        response = session.send(prepped_request,allow_redirects=allow_redirects,timeout=timeout,)
        return Response(int(response.status_code), response.content.decode('utf-8'))

def recvline(sock):
    stop = 0
    line = ''
    while True:
        i = sock.recv(1)
        if i == '\n': stop = 1
        line += i
        if stop == 1:
            break
    return line

class ProxySMTP( smtplib.SMTP ):
    def __init__(self, host='smtp.gmail.com', port=587, p_address='cis-india-pitc-bangalorez.proxy.corporate.ge.com',p_port=80, local_hostname=None,timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        self.p_address = p_address
        self.p_port = p_port
        self.timeout = timeout
        self.esmtp_features = {}
        self.default_port = smtplib.SMTP_PORT
        if host:
            (code, msg) = self.connect(host, port)
            if code != 220:
                raise SMTPConnectError(code, msg)
        if local_hostname is not None:
            self.local_hostname = local_hostname
        else:
            fqdn = socket.getfqdn()
            if '.' in fqdn:
                self.local_hostname = fqdn
            else:
                addr = '192.168.0.103'
                try:
                    addr = socket.gethostbyname(socket.gethostname())
                except socket.gaierror:
                    pass
                self.local_hostname = '[%s]' % addr
        smtplib.SMTP.__init__(self)
    def _get_socket(self, port, host, timeout):
        if self.debuglevel > 0: print>>stderr, 'connect:', (host, port)
        new_socket = socket.create_connection((self.p_address,self.p_port), timeout)
        new_socket.sendall(b'CONNECT {0}:{1} HTTP/1.1\r\n\r\n')
        for x in xrange(2): recvline(new_socket)
        return new_socket

##    client = Client(account_sid, auth_token,http_client=ProxiedTwilioHttpClient())

##    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS4,'cis-india-pitc-bangalorez.proxy.corporate.ge.com',80)
##    socks.wrapmodule(smtplib)

##    server = ProxySMTP(host='smtp.gmail.com', port=587,p_address='cis-india-pitc-bangalorez.proxy.corporate.ge.com', p_port=80)

    
