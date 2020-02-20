import smtplib
import random
import string
import time
import argparse
import sys
import os

from email.parser import Parser
from classes.tlsIMAP import IMAP4_STARTTLS

__version__ = '0.1'

if __name__ == '__main__':
  prog = os.path.basename(sys.argv[0])
  
  # Parse Arguments
  parser = argparse.ArgumentParser(prog=prog)
  
  parser.add_argument('-V', '--version', action='version', version='%(prog)s v' + sys.modules[__name__].__version__)
  
  # Options for SMTP
  parser.add_argument('-sh','--smtp_host',
                      help='The host address or FQDN of the SMTP server',
                      #required=True
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
                      #required=True
                      dest='smtpUser'
                      )
  
  parser.add_argument('-spw', '--smtp_password',
                      help='The password for the username',
                      #required=True
                      dest='smtpPassword'
                      )
  
  # Options for IMAP
  parser.add_argument('-ih','--imap_host',
                      help='The host address or FQDN of the IMAP server',
                      #required=True
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
                      #required=True
                      dest='imapUser'
                      )
  
  parser.add_argument('-ipw', '--imap_password',
                      help='The password of the username',
                      #required=True
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

  args = parser.parse_args()
  
  # Get timestamp (sec) for mail body
  timeSecSend = int(time.time())

  # Generate random hash for unique subject
  randString = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))

  # Read from mail.state file the randString as unique subject from the sent email
  try:
    stateFile = open('%s/mail.state' % os.path.dirname(__file__), 'w')
    stateFile.write('%s' % randString)
    stateFile.close()
  except:
    print('File does not exist')

  # Connect to Exchange
  smtpConnection = smtplib.SMTP(args.smtpHost, args.smtpPort)
  smtpConnection.starttls()
  smtpConnection.login(args.smtpUser,args.smtpPassword)
  
  # Send email from Exchange
  messageHeader = 'From: '+ args.sender +'\nTo: '+ args.receiver +'\nSubject: '+ randString +'\n\n{}'
  mailbody = ('%s\n\nThis is a mail for monitoring, do not reply.') % timeSecSend
  smtpConnection.sendmail(args.sender,args.receiver,messageHeader.format(mailbody))
  time.sleep(2)
  
  # Connect to IMAP
  imapConnection = IMAP4_STARTTLS(args.imapHost, args.imapPort)
  imapConnection.login(args.imapUser,args.imapPassword)
  
  # Fetch email from defined mailbox
  imapConnection.select(args.imapFolder)
  typ, data = imapConnection.search(None, 'ALL')
  for num in data[0].split():
    typ, data = imapConnection.fetch(num, '(RFC822)')
    raw_email = data[0][1]
    print((Parser().parsestr(raw_email)).get('Subject'))
    print((Parser().parsestr(raw_email)).get_payload().splitlines()[0])
    
  # Disconnect from IMAP
  imapConnection.close()
  imapConnection.logout()
