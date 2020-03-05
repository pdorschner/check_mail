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
import email.message


from email.parser import Parser
from datetime import datetime
from traceback import print_exc
from socket import gaierror

__version__ = '0.1'

STATUS_OK = 0
STATUS_WARNING = 1
STATUS_CRITICAL = 2
STATUS_UNKNOWN = 3

def output(label, stateSender=0, stateReply=0, name='check_email'):
  pluginoutput = ''

  if stateSender or stateReply == 0:
    pluginoutput += 'OK'
  elif stateSender or stateReply== 1:
    pluginoutput += 'WARNING'
  elif stateSender or stateReply == 2:
    pluginoutput += 'CRITICAL'
  elif stateSender or stateReply == 3:
    pluginoutput += 'UNKNOWN'
  else:
    raise RuntimeError('ERROR: State programming error.')

  pluginoutput += ' - '

  pluginoutput += name + ': ' + str(label)

  pluginSummary = pluginoutput

  print(pluginoutput)

  sys.exit(max(stateSender,stateReply))

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
    exitCode = STATUS_UNKNOWN
    timeout = time.time() + 30
    # TimeCleanup deletes mails older then 1 hour
    #timeCleanup = int(time.time()) - 3600
    timeCleanup = time.time() - 300
    # TimeCrit defines the critical threshold
    timeCrit = time.time() + (self.critical * 60)
    # TimeWarn defines the warning threshold
    timeWarn = time.time() + (self.warning * 60)

    while True:
      self.imapcon.select(self.mailbox)
      type, data = self.imapcon.search(None, 'ALL')
      for num in data[0].split():
        typ, data = self.imapcon.fetch(num, '(RFC822)')
        raw_email = data[0][1]
        emailtimestamp = time.mktime(email.utils.parsedate((Parser().parsestr(raw_email)).get('Date')))
        emailCustomTag = Parser().parsestr(raw_email).get('X-Custom-Tag')
        emailSubject = Parser().parsestr(raw_email).get('Subject')
        if self.clean == True:
          if ((emailtimestamp < timeCleanup ) and ((emailCustomTag == 'Email-Check-Icinga') or (emailSubject == self.mailsubject))):
            self.imapcon.store(num, '+FLAGS', '\\Deleted')
      if (self.mailsubject in emailSubject):
        emailtimestamp = time.mktime(email.utils.parsedate((Parser().parsestr(raw_email)).get('Date')))
        exitCode = STATUS_OK
        break
      if time.time() > timeWarn:
        exitCode = STATUS_WARNING
      else:
        if time.time() > timeCrit:
          self.imapcon.close()
          self.imapcon.logout()
          exitCode = STATUS_CRITICAL
          #sys.exit(STATUS_CRITICAL) #TODO Raise exception
          break
        """ print(int(time.time()))
        print(timeCrit) """
        time.sleep(5)
      continue
    return [exitCode, emailtimestamp]
    
  def cleanup(self, replyName):
    self.replyName = replyName
    timeCleanup = time.time() - 300
    self.imapcon.select(self.mailbox)
    type, data = self.imapcon.search(None, 'ALL')
    for num in data[0].split():
      typ, data = self.imapcon.fetch(num, '(RFC822)')
      raw_email = data[0][1]
      emailtimestamp = time.mktime(email.utils.parsedate((Parser().parsestr(raw_email)).get('Date')))
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

  def connect(self):
    self.smtpcon = smtplib.SMTP(self.host, self.port)
    self.smtpcon.starttls()
    self.smtpcon.login(self.user, self.password)

  def send(self):
    timeSecSend = int(time.time())
    messageheader = 'X-Custom-Tag: Email-Check-Icinga\nFrom: '+ self.sender +'\nTo: '+ self.receiver +'\nSubject: '+ self.subject +'\n\n{}'
    mailbody = ('%s\n\nThis is a mail for monitoring, do not reply.') % timeSecSend
    self.smtpcon.sendmail(self.sender, self.receiver, messageheader.format(mailbody))

    return timeSecSend

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
                      #required=True,
                      dest='smtpHost'
                      )
  
  parser.add_argument('-sp','--smtpPort',
                      help='The port of the SMTP server',
                      type=int,
                      #required=True,
                      dest='smtpPort'
                      )
  
  parser.add_argument('-susr', '--smtpUser',
                      help='The username who logs into exchange',
                      #required=True,
                      dest='smtpUser'
                      )
  
  parser.add_argument('-spw', '--smtpPassword',
                      help='The password for the username',
                      #required=True,
                      dest='smtpPassword'
                      )
  
  parser.add_argument('-ih','--imapHost',
                      help='The host address or FQDN of the IMAP server',
                      #required=True,
                      dest='imapHost'
                      )
  
  parser.add_argument('-ip', '--imapPort',
                      help='The port of the IMAP server',
                      #required=True,
                      type=int,
                      dest='imapPort'
                      )
  
  parser.add_argument('-iusr', '--imapUser',
                      help='The username who logs into exchange',
                      #required=True,
                      dest='imapUser'
                      )
  
  parser.add_argument('-ipw', '--imapPassword',
                      help='The password of the username',
                      #required=True,
                      dest='imapPassword'
                      )
  
  parser.add_argument('-if', '--imapFolder',
                      help='The mailbox which is checked',
                      #required=True,
                      default='INBOX',
                      dest='imapFolder'
                      )

  parser.add_argument('-send', '--sender',
                      help='The value of the From: header (required)',
                      #required=True,
                      dest='sender'
                      )

  parser.add_argument('-rec', '--receiver',
                      help='The value of the TO: header (required)',
                      #required=True,
                      dest='receiver'
                      )

  parser.add_argument('-w', '--warning',
                      help='The value of warning threshold',
                      type=int,
                      default=5,
                      #required=True,
                      dest='warning'
                      )

  parser.add_argument('-c', '--critical',
                      help='The value of critical threshold',
                      type=int,
                      default=10,
                      #required=True,
                      dest='critical'
                      )
              
  parser.add_argument('--imapSenderHost',
                      help='The host address or FQDN of the IMAP server which send the mail (just for cleanup echo replies)',
                      dest='imapSenderHost'
                      )

  parser.add_argument('--imapSenderPort',
                      help='The port of the IMAP server (just for cleanup echo replies)',
                      dest='imapSenderPort'
                      )

  parser.add_argument('--imapSenderUser',
                      help='The username who logs into exchange (just for cleanup echo replies)',
                      dest='imapSenderUser'
                      )

  parser.add_argument('--imapSenderPassword',
                      help='The password of the user (just for cleanup echo replies)',
                      dest='imapSenderPassword'
                      )

  parser.add_argument('--imapSenderFolder',
                      help='The mailbox which is checked (just for cleanup echo replies)',
                      dest='imapSenderFolder'
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

  args = parser.parse_args()

  if args.cleanupMail and (args.imapSenderHost is None or 
                           args.imapSenderUser is None or 
                           args.imapSenderPassword is None or
                           args.imapSenderFolder is None or
                           args.replyName is None
                           ):
    parser.error('--cleanup requires --replyName, --imapSenderHost, --imapSenderPort, --imapSenderUser, --imapSenderPassword, --imapSenderFolder')

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

  stateSender = STATUS_UNKNOWN
  stateReply = STATUS_UNKNOWN
  pluginoutput = ''

  # First block test the SMTP 'connection', 'authentication' and 'socket'. If exception is
  # thrown, the program exits with return code

  # Send mail
  try:
    connectionSmtp = SMTP_CONNECTION(args.smtpHost, args.smtpPort, args.smtpUser, args.smtpPassword, args.sender, args.receiver)
    subject = connectionSmtp.subject
    connectionSmtp.connect()
    timeStart = connectionSmtp.send()
    connectionSmtp.disconnectSmtp()
  except smtplib.SMTPConnectError as e:
    pluginoutput = 'SMTP Connection Error: %s' % e[1]
    state = STATUS_UNKNOWN
  except smtplib.SMTPAuthenticationError as a:
    pluginoutput = 'SMTP Authentication Error: %s' % a[1]
    state = STATUS_UNKNOWN
  except gaierror as g:
    pluginoutput = 'SMTP Host "%s" not reachable: %s' % (connectionSmtp.host,g)
    state = STATUS_UNKNOWN

  else:
    # Connect via IMAP to remote Exchange
    try:
      connectionImap = IMAP_CONNECTION(args.imapHost, args.imapPort, args.imapUser, args.imapPassword, args.imapFolder, subject, args.cleanupMail)
      connectionImap.connect()

      # searchMail returns [exitCode, timestamp]
      getStateReceived = connectionImap.searchMail(args.warning, args.critical)

      if (getStateReceived[0] == STATUS_WARNING):
        pluginoutput = 'Email took [xy] to send'
        stateSender = STATUS_WARNING
      elif (getStateReceived[0] == STATUS_CRITICAL):
        pluginoutput = 'Email could not be read'
        stateSender = STATUS_CRITICAL
      else: 
        pluginoutput += '%s email received\n' % connectionImap.host
        stateSender = STATUS_OK
      connectionImap.disconnectImap()
    except imaplib.IMAP4.error as e:
      pluginoutput =  'IMAP: %s' % e 
      stateSender = STATUS_UNKNOWN
    except gaierror as g:
      pluginoutput = 'IMAP Host "%s" not reachable: %s' % (connectionImap.host, g)
      stateSender = STATUS_UNKNOWN
    except Exception as s:
      pluginoutput = 'IMAP Connection Timeout. Wrong port?: %s' % s
      stateSender = STATUS_UNKNOWN
  
    else:
      # Cleanup Echo replies
      try:
        connectionSenderImap = IMAP_CONNECTION(args.imapHost, args.imapPort, args.imapUser, args.imapPassword, args.imapFolder, subject, args.cleanupMail)
        connectionSenderImap.connect()

        getStateReply = connectionSenderImap.searchMail(args.warning, args.critical)

        if (getStateReply[0] == STATUS_WARNING):
          pluginoutput = 'Email took [xy] to reply'
          stateReply = STATUS_WARNING
        elif (getStateReply[0] == STATUS_CRITICAL):
          pluginoutput = 'Reply Email is missing'
          stateReply = STATUS_CRITICAL
        else:
          pluginoutput +=  '%s email received' % connectionSenderImap.host
          stateReply = STATUS_OK
        if (args.cleanupMail):
          #connectionSenderImap.cleanup(args.replyName)
          connectionSenderImap.cleanup('philipp.dorschn')
        connectionSenderImap.disconnectImap()
      except imaplib.IMAP4.error as e:
        if str(e) == 'command SEARCH illegal in state AUTH, only allowed in states SELECTED':
          pluginoutput = 'IMAP: Given Mailbox is not available'
        else:
          pluginoutput = 'IMAP: %s' % e 
        stateReply = STATUS_UNKNOWN
      except gaierror as g:
        pluginoutput = 'IMAP Host "%s" not reachable: %s' % (connectionImap.host, g)
        stateReply = STATUS_UNKNOWN
      except Exception as s:
        pluginoutput = 'IMAP Connection Timeout. Wrong port?: %s' % s
        stateReply = STATUS_UNKNOWN

  # TODO Zeitrechnung stimmt nicht. Manchmal kommt Minus raus
  # 1583420193.98 SYSTEMZEIT
  # 1583420194.0 EMAIL EMPFANGEN
  deltaReceived = getStateReceived[1] - timeStart
  deltaReply = getStateReply[1] - getStateReceived[1]
  deltaGes = deltaReceived + deltaReply

  print(timeStart)
  print(getStateReceived[1])
  print(getStateReply[1])
  print('\n')
  print(deltaReceived)
  print(deltaReply)
  print(deltaGes)

  output(pluginoutput,stateSender,stateReply)

if __name__ == '__main__':
  sys.exit(main())