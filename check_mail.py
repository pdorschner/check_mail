#!/usr/bin/env python
import smtplib
import imaplib
import random
import string
import time
import argparse
import sys
import os
import email.utils

from email.parser import Parser
from datetime import datetime
from traceback import print_exc
from socket import gaierror

__version__ = '0.1'

STATUS_OK = 0
STATUS_WARNING = 1
STATUS_CRITICAL = 2
STATUS_UNKNOWN = 3

class IMAP_CONNECTION(object):
  def __init__(self, host, port ,user, password, mailbox, mailsubject, clean):
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.mailbox = mailbox
    self.mailsubject = mailsubject
    self.clean = clean

  def connect(self):
    self.imapcon = imaplib.IMAP4_SSL(self.host,self.port)
    #self.imapcon.debug = 4
    self.imapcon.login(self.user,self.password)
        
  def disconnectImap(self):
    self.imapcon.close()
    self.imapcon.logout()

  def searchMail(self, warning, critical):
    self.warning = warning
    self.critical = critical
    exitCode = 0
    timeout = int(time.time()) + 30
    # TimeCleanup deletes mails older then 1 hour
    #timeCleanup = int(time.time()) - 3600
    timeCleanup = int(time.time()) - 300
    # TimeCrit defines the critical threshold
    timeCrit = int(time.time()) + (self.critical * 60)
    # TimeWarn defines the warning threshold
    timeWarn = int(time.time()) + (self.warning * 60)

    while True:
      self.imapcon.select(self.mailbox)
      type, data = self.imapcon.search(None, 'ALL')
      for num in data[0].split():
        typ, data = self.imapcon.fetch(num, '(RFC822)')
        raw_email = data[0][1]
        emailtimestamp = int(time.mktime(email.utils.parsedate((Parser().parsestr(raw_email)).get('Date'))))   
        emailCustomTag = Parser().parsestr(raw_email).get('X-Custom-Tag')
        emailSubject = Parser().parsestr(raw_email).get('Subject')
        if self.clean == True:
          if ((emailtimestamp < timeCleanup ) and ((emailCustomTag == 'Email-Check-Icinga') or (emailSubject == self.mailsubject))):
            print(emailtimestamp)
            print(timeCleanup)
            self.imapcon.store(num, '+FLAGS', '\\Deleted')
      if (self.mailsubject in emailSubject):
        break
      if int(time.time()) > timeWarn:
        exitCode = STATUS_WARNING
      else:
        if int(time.time()) > timeCrit:
          print('CRITICAL - Critical Threshold exceeded')
          self.imapcon.close()
          self.imapcon.logout()
          #sys.exit(STATUS_CRITICAL) #TODO Raise exception
          exitCode = STATUS_CRITICAL
          break
        time.sleep(5)
      continue
    return exitCode
    
  def cleanup(self, replyName):
    self.replyName = replyName
    timeCleanup = int(time.time()) - 300
    self.imapcon.select(self.mailbox)
    type, data = self.imapcon.search(None, 'ALL')
    for num in data[0].split():
      typ, data = self.imapcon.fetch(num, '(RFC822)')
      raw_email = data[0][1]
      emailtimestamp = int(time.mktime(email.utils.parsedate((Parser().parsestr(raw_email)).get('Date'))))
      if (replyName and (emailtimestamp < timeCleanup )):
        self.imapcon.store(num, '+FLAGS', '\\Deleted')
      
class SMTP_CONNECTION(object):
  def __init__(self, host, port, user, password, sender, receiver):
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.sender = sender
    self.receiver = receiver
    self.subject = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))

    @property
    def subject(self):
      return self._subject

  def connect(self):
      self.smtpcon = smtplib.SMTP(self.host, self.port)
      self.smtpcon.starttls()
      self.smtpcon.login(self.user, self.password)

  def send(self):
    timeSecSend = int(time.time())
    messageheader = 'X-Custom-Tag: Email-Check-Icinga\nFrom: '+ self.sender +'\nTo: '+ self.receiver +'\nSubject: '+ self.subject +'\n\n{}'
    mailbody = ('%s\n\nThis is a mail for monitoring, do not reply.') % timeSecSend
    self.smtpcon.sendmail(self.sender, self.receiver, messageheader.format(mailbody))

  def disconnectSmtp(self):
    self.smtpcon.quit()

def main():
  # Parse Arguments
  parser = argparse.ArgumentParser()

  parser.add_argument('-V', '--version',
                      action='version',
                      version='%(prog)s v' + sys.modules[__name__].__version__)
  
  parser.add_argument('-sh','--smtpHost',
                      help='The host address or FQDN of the SMTP server',
                      required=True,
                      dest='smtpHost'
                      )
  
  parser.add_argument('-sp','--smtpPort',
                      help='The port of the SMTP server',
                      type=int,
                      required=True,
                      dest='smtpPort'
                      )
  
  parser.add_argument('-susr', '--smtpUser',
                      help='The username who logs into exchange',
                      required=True,
                      dest='smtpUser'
                      )
  
  parser.add_argument('-spw', '--smtpPassword',
                      help='The password for the username',
                      required=True,
                      dest='smtpPassword'
                      )
  
  parser.add_argument('-ih','--imapHost',
                      help='The host address or FQDN of the IMAP server',
                      required=True,
                      dest='imapHost'
                      )
  
  parser.add_argument('-ip', '--imapPort',
                      help='The port of the IMAP server',
                      required=True,
                      type=int,
                      dest='imapPort'
                      )
  
  parser.add_argument('-iusr', '--imapUser',
                      help='The username who logs into exchange',
                      required=True,
                      dest='imapUser'
                      )
  
  parser.add_argument('-ipw', '--imapPassword',
                      help='The password of the username',
                      required=True,
                      dest='imapPassword'
                      )
  
  parser.add_argument('-if', '--imapFolder',
                      help='The mailbox which is checked',
                      required=True,
                      default='INBOX',
                      dest='imapFolder'
                      )

  parser.add_argument('-send', '--sender',
                      help='The value of the From: header (required)',
                      required=True,
                      dest='sender'
                      )

  parser.add_argument('-rec', '--receiver',
                      help='The value of the TO: header (required)',
                      required=True,
                      dest='receiver'
                      )

  parser.add_argument('-w', '--warning',
                      help='The value of warning threshold',
                      type=int,
                      default=5,
                      required=True,
                      dest='warning'
                      )

  parser.add_argument('-c', '--critical',
                      help='The value of critical threshold',
                      type=int,
                      default=10,
                      required=True,
                      dest='critical'
                      )

  cleanupGroup = parser.add_argument_group('Use this arguments if cleanup is TRUE')

  cleanupGroup.add_argument('--cleanup',
                      help='Deletes old mails',
                      default=False,
                      action='store_true',
                      dest='cleanupMail'
                      )

  cleanupGroup.add_argument('--cleanupTime',
                      help='Deletes mails older then x minutes',
                      default=300,
                      dest='cleanupTime'
                      )

  cleanupGroup.add_argument('--replyName',
                      help='Specifies the name the of the reply (just for cleanup echo replies)',
                      dest='replyName'
                      )

  cleanupGroup.add_argument('--imapSenderHost',
                      help='The host address or FQDN of the IMAP server which send the mail (just for cleanup echo replies)',
                      dest='imapSenderHost'
                      )

  cleanupGroup.add_argument('--imapSenderPort',
                      help='The port of the IMAP server (just for cleanup echo replies)',
                      dest='imapSenderPort'
                      )

  cleanupGroup.add_argument('--imapSenderUser',
                      help='The username who logs into exchange (just for cleanup echo replies)',
                      dest='imapSenderUser'
                      )

  cleanupGroup.add_argument('--imapSenderPassword',
                      help='The password of the user (just for cleanup echo replies)',
                      dest='imapSenderPassword'
                      )

  cleanupGroup.add_argument('--imapSenderFolder',
                      help='The mailbox which is checked (just for cleanup echo replies)',
                      dest='imapSenderFolder'
                      )

  args = parser.parse_args()

  if args.cleanupMail and (args.imapSenderHost is None or args.imapSenderUser is None or args.imapSenderPassword is None or args.imapSenderFolder is None or args.replyName is None):
    parser.error('--cleanup requires --replyName, --imap_senderHost, --imap_senderPort, --imap_senderUser, --imap_senderPassword, --imap_senderFolder')

  # Environment variables, so the credentials are hidden in process from other users
  envSmtpPassword = os.getenv('SMTP_PASSWORD')
  if envSmtpPassword:
    args.smtpPassword = envSmtpPassword

  envSmtpUsername = os.getenv('SMTP_USERNAME')
  if envSmtpUsername:
    args.smtpUser = envSmtpUsername

  envImapUsername = os.getenv('IMAP_USERNAME')
  if envImapUsername:
    args.imapUsername = envImapUsername

  envImapPassword = os.getenv('IMAP_PASSWORD')
  if envImapPassword:
    args.imapPassword = envImapPassword

  envImapSenderUsername = os.getenv('IMAP_SENDER_USERNAME')
  if envImapSenderUsername:
    args.imapSenderUser = envImapSenderUsername

  envImapSenderPassword = os.getenv('IMAP_SENDER_PASSWORD')
  if envImapSenderPassword:
    args.imapSenderPassword = envImapSenderPassword

  state = STATUS_OK
  # Send mail
  try:
    connectionSmtp = SMTP_CONNECTION(args.smtpHost, args.smtpPort, args.smtpUser, args.smtpPassword, args.sender, args.receiver)
    subject = connectionSmtp.subject
    connectionSmtp.connect()
    connectionSmtp.send()
    connectionSmtp.disconnectSmtp()
  except smtplib.SMTPException as e:
      print ('UNKONWN - SMTP: %s' % e[1]) 
      sys.exit(STATUS_UNKNOWN)

  # Connect via IMAP to remote Exchange
  try:
    connectionImap = IMAP_CONNECTION(args.imapHost, args.imapPort, args.imapUser, args.imapPassword, args.imapFolder, subject, args.cleanupMail)
    connectionImap.connect()
    if (connectionImap.searchMail(args.warning, args.critical) == STATUS_WARNING):
      state = STATUS_WARNING
    else:
      state = STATUS_OK
    connectionImap.searchMail(args.warning, args.critical)
    connectionImap.disconnectImap()
  except imaplib.IMAP4.error as e:
    print('UNKNOWN - IMAP: %s' % e )
    sys.exit(STATUS_UNKNOWN)
  except gaierror as g:
    print('UNKNOWN - IMAP: %s' % g)
    sys.exit(STATUS_UNKNOWN)

  # Cleanup Echo replies
  try:
    connectionSenderImap = IMAP_CONNECTION(args.imapSenderHost, args.imapSenderPort, args.imapSenderUser, args.imapSenderPassword, args.imapSenderFolder, subject, args.cleanupMail)
    connectionSenderImap.connect()
    if (connectionSenderImap.searchMail(args.warning, args.critical) == STATUS_WARNING):
      state = STATUS_WARNING
    else:
      state = STATUS_OK
    if (args.cleanupmail == False):
      connectionSenderImap.cleanup(args.replyName)
    connectionSenderImap.disconnectImap()
  except imaplib.IMAP4.error as e:
    print('UNKNOWN - IMAP: %s' % e)
    sys.exit(STATUS_UNKNOWN)
  
  if state == STATUS_OK:
    print('OK - Check_Email')
    return STATUS_OK
  elif state == STATUS_WARNING:
    print('WARNING - Check_Email: Delivery took longer then %s' % args.warning)
    return STATUS_WARNING
  elif state == STATUS_CRITICAL:
    print('CRITICAL - Check_Email: Delivery tool longer then %s' % args.critical)
    return STATUS_CRITICAL

if __name__ == '__main__':
  sys.exit(main())