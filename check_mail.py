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

__version__ = '0.1'

class IMAP_CONNECTION(object):
  def __init__(self, host, port ,user, password, mailbox, mailsubject):
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.mailbox = mailbox
    self.mailsubject = mailsubject

  def connect(self):
    try:
      self.imapcon = imaplib.IMAP4_SSL(self.host,self.port)
      #self.imapcon.debug = 4
      self.imapcon.login(self.user,self.password)
    except:
      print('UNKNOWN - IMAP Login failed')
      sys.exit(3)
        
  def disconnect(self):
    self.imapcon.close()
    self.imapcon.logout()

  def search_mail(self, warning, critical):
    self.warning = warning
    self.critical = critical
    timeout = int(time.time()) + 30
    # TimeCleanup deletes mails older then 1 hour
    timeCleanup = int(time.time()) - 3600
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
        emailtimestamp = email.utils.parsedate((Parser().parsestr(raw_email)).get('Date'))
        if ( (int(time.mktime(emailtimestamp)) < timeCleanup ) and ((Parser().parsestr(raw_email)).get('X-Custom-Tag') == 'Email-Check-Icinga')):
          self.imapcon.store(num, '+FLAGS', '\\Deleted')
      if ((Parser().parsestr(raw_email)).get('Subject') == self.mailsubject):
        print('MAIL FOUND')
        return 0
        break
      if time.time() > timeWarn:
        print(('WARNING - Mail not in mailbox since d%') % timeWarn)
        exitCode = 1
      else:
        if time.time() > timeCrit:
          print('Timeout exceeded')
          sys.exit(3) #TODO Raise exception
        time.sleep(5)
        print(time.time())
        print(timeout)
      continue
    
  def cleanup(self):
    self.imapcon.select(self.mailbox)
    type, data = self.imapcon.search(None, 'ALL')
    for num in data[0].split():
      typ, data = self.imapcon.fetch(num, '(RFC822)')
      raw_email = data[0][1]
      # Hardcoded 'From:' string. TODO make generic
      if((Parser().parsestr(raw_email)).get('From') == '"Charite Echo" <echo@charite.de>'):
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
    try:
      self.smtpcon = smtplib.SMTP(self.host, self.port)
      self.smtpcon.starttls()
      self.smtpcon.login(self.user, self.password)
    except:
      print('UNKNOWN - SMTP Login failed')
      sys.exit(3)

  def send(self):
    timeSecSend = int(time.time()) 
    messageheader = 'X-Custom-Tag: Email-Check-Icinga\nFrom: '+ self.sender +'\nTo: '+ self.receiver +'\nSubject: '+ self.subject +'\n\n{}'
    mailbody = ('%s\n\nThis is a mail for monitoring, do not reply.') % timeSecSend
    self.smtpcon.sendmail(self.sender, self.receiver, messageheader.format(mailbody))
    self.smtpcon.quit()

def main():
  # Parse Arguments
  parser = argparse.ArgumentParser()

  parser.add_argument('-V', '--version',
                      action='version',
                      version='%(prog)s v' + sys.modules[__name__].__version__)
  
  # Options for SMTP
  parser.add_argument('-sh','--smtp_host',
                      help='The host address or FQDN of the SMTP server',
                      #required=True,
                      dest='smtpHost'
                      )
  
  parser.add_argument('-sp','--smtp_port',
                      help='The port of the SMTP server',
                      type=int,
                      #required=True,
                      dest='smtpPort'
                      )
  
  parser.add_argument('-susr', '--smtp_user',
                      help='The username who logs into exchange',
                      #required=True,
                      dest='smtpUser'
                      )
  
  parser.add_argument('-spw', '--smtp_password',
                      help='The password for the username',
                      #required=True,
                      dest='smtpPassword'
                      )
  
  # Options for IMAP
  parser.add_argument('-ih','--imap_host',
                      help='The host address or FQDN of the IMAP server',
                      #required=True,
                      dest='imapHost'
                      )
  
  parser.add_argument('-ip', '--imap_port',
                      help='The port of the IMAP server',
                      #required=True,
                      type=int,
                      dest='imapPort'
                      )
  
  parser.add_argument('-iusr', '--imap_user',
                      help='The username who logs into exchange',
                      #required=True,
                      dest='imapUser'
                      )
  
  parser.add_argument('-ipw', '--imap_password',
                      help='The password of the username',
                      #required=True,
                      dest='imapPassword'
                      )
  
  parser.add_argument('-if', '--imap_folder',
                      help='The mailbox which is checked',
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
                      dest='warning'
                      )

  parser.add_argument('-c', '--critical',
                      help='The value of critical threshold',
                      type=int,
                      default=10,
                      dest='critical'
                      )

  parser.add_argument('--cleanup',
                      help='Deletes old mails',
                      default=True,
                      dest='cleanupmail'
                      )
  
  args = parser.parse_args()

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

  # Send mail
  connectionSmtp = SMTP_CONNECTION(args.smtpHost, args.smtpPort, args.smtpUser, args.smtpPassword, args.sender, args.receiver)
  subject = connectionSmtp.subject
  connectionSmtp.connect()
  connectionSmtp.send()

  # Connect via IMAP to remote Exchange
  connectionImap = IMAP_CONNECTION(args.imapHost, args.imapPort, args.imapUser, args.imapPassword, args.imapFolder, subject)
  connectionImap.connect()
  # Parses mailbox and clean up old sent mails
  connectionImap.search_mail(args.warning, args.critical)
  connectionImap.disconnect()

  # Connect via IMAP to the SENDER-Exchange and 
  connectionSenderImap = IMAP_CONNECTION(args.imapHost, args.imapPort, args.imapUser, args.imapPassword, args.imapFolder, subject)
  connectionSenderImap.connect()
  # Parses mailbox and clean up 'ECHO REPLY' mails
  connectionSenderImap.cleanup()
  connectionSenderImap.disconnect()

if __name__ == '__main__':
  try:
    sys.exit(main())
  except SystemExit:
    # Re-throw the exception
    raise sys.exc_info()[1], None, sys.exc_info()[2]
  except:
    print "UNKNOWN - Error: %s" % (str(sys.exc_info()[1]))
    sys.exit(3)