#!/usr/bin/env python

try:
    import sys
    import smtplib
    import imaplib
    import random
    import string
    import time
    import argparse
    import os
    import email.utils
    import email.message
    import email.header
    import re

    from email.mime.text import MIMEText
    from socket import gaierror, error as socketerror
except Exception as e:
    print("UNKNOWN: Failure during import: %s" % e.message)
    sys.exit(3)

__version__ = '0.1'

# Icinga states
STATUS_OK = 0
STATUS_WARNING = 1
STATUS_CRITICAL = 2
STATUS_UNKNOWN = 3


def plugin_exit(label,
                state=STATUS_OK,
                lines=None,
                perfdata=None,
                name='check_email'):

    if lines is None:
        lines = []
    if perfdata is None:
        perfdata = {}

    pluginoutput = ''

    if state == 0:
        pluginoutput += 'OK'
    elif state == 1:
        pluginoutput += 'WARNING'
    elif state == 2:
        pluginoutput += 'CRITICAL'
    elif state == 3:
        pluginoutput += 'UNKNOWN'
    else:
        raise RuntimeError('ERROR: State programming error.')

    pluginoutput += ' - '

    pluginoutput += name + ': ' + str(label)

    if len(lines):
        pluginoutput += ' - '
        pluginoutput += ' '.join(lines)

    if perfdata:
        pluginoutput += '|'
        pluginoutput += ' '.join(["'" + key + "'" + '=' +
                                 str(value) for key, value in
                                 perfdata.items()])

    print(pluginoutput)
    sys.exit(state)


class ImapConnection(object):
    def __init__(self, host, port, user, password,
                 mailbox, mailsubject, clean):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.mailbox = mailbox
        self.mailsubject = mailsubject
        self.clean = clean

    def connect(self):
        self.imapcon = imaplib.IMAP4_SSL(self.host, self.port)
        # self.imapcon.debug = 4
        self.imapcon.login(self.user, self.password)

    def disconnect_imap(self):
        self.imapcon.close()
        self.imapcon.logout()

    def decode_header(self, raw_email, header_type):
        self.raw_email = raw_email
        self.header_type = header_type
        parsed_header = email.header.decode_header(
            self.raw_email[self.header_type])[0]

        parsed_header = unicode(parsed_header[0])
        return parsed_header

    def search_mail(self, warning, critical, cleanup_time):
        self.warning = warning
        self.critical = critical
        self.cleanup_time = cleanup_time
        # time_cleanup deletes mails older then 1 hour
        # time_cleanup = int(time.time()) - 3600
        time_cleanup = time.time() - self.cleanup_time
        # time_crit defines the critical threshold
        time_crit = time.time() + (self.critical * 60)
        # time_warn defines the warning threshold
        time_warn = time.time() + (self.warning * 60)

        while True:
            self.imapcon.select(self.mailbox)
            return_value, message_data = self.imapcon.search(None, 'ALL')

            for message_id in message_data[0].split():
                return_value, message_data = self.imapcon.fetch(
                    message_id, '(RFC822)')
                raw_email = email.message_from_string(message_data[0][1])

                # TODO: Refactor
                email_subject = self.decode_header(raw_email, 'Subject')
                email_customtag = self.decode_header(raw_email, 'X-Custom-Tag')
                email_date_as_unix = email.utils.mktime_tz(
                    email.utils.parsedate_tz(
                        raw_email['Date']))
     
                if self.clean:
                    if email_date_as_unix < time_cleanup and email_customtag == 'Email-Check-Icinga':
                        self.imapcon.store(message_id, '+FLAGS', '\\Deleted')

                if (self.mailsubject in email_subject):
                    # Actual timestamp of received email has to be parsed.
                    # 'Received' field contains a (possibly empty) list of
                    # name/value pairs followed by a semicolon and a date-time
                    # specification. Parse the date after semicolon to get the
                    # time when the server actually received the mail
                    # (RFC 2822 | 3.6.7)
                    # TODO: regex is very expensive
                    # search an alternative solution
                    email_server_date_as_unix = self.decode_header(raw_email,
                                                                   'Received')
                    match = re.search(r";\s(.*)", email_server_date_as_unix)

                    if match:
                        email_server_date_as_unix = match.group(1)
                        email_server_date_as_unix = email.utils.mktime_tz(
                            email.utils.parsedate_tz(
                                email_server_date_as_unix))

                    if time.time() > time_warn:
                        return STATUS_WARNING, email_server_date_as_unix

                    return STATUS_OK, email_server_date_as_unix

            if time.time() > time_crit:
                return STATUS_CRITICAL, None
            else:
                time.sleep(5)

    def cleanup(self, reply_name):
        self.reply_name = reply_name
        self.imapcon.select(self.mailbox)
        time_cleanup = time.time() - 300

        return_value, message_data = self.imapcon.search(None, 'ALL')

        for message_id in message_data[0].split():
            return_value, message_data = self.imapcon.fetch(message_id, '(RFC822)')
            raw_email = email.message_from_string(message_data[0][1])
            email_date_as_unix = email.utils.mktime_tz(
                email.utils.parsedate_tz(
                    raw_email['Date']))

            if reply_name and email_date_as_unix < time_cleanup:
                self.imapcon.store(message_id, '+FLAGS', '\\Deleted')


class SmtpConnection(object):
    def __init__(self, host, port, user, password, sender, receiver):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender
        self.receiver = receiver
        self.subject = ''.join(random.choice(string.ascii_uppercase +
                                             string.ascii_lowercase +
                                             string.digits) for _ in range(6))

    def connect(self):
        self.smtpcon = smtplib.SMTP(self.host, self.port)
        self.smtpcon.starttls()
        self.smtpcon.login(self.user, self.password)

    def send(self):
        time_send = int(time.time())

        message = MIMEText('%s' % time_send)
        message['From'] = email.utils.formataddr((False, self.sender))
        message['To'] = email.utils.formataddr((False, self.receiver))
        message['Subject'] = self.subject
        message['X-Custom-Tag'] = 'Email-Check-Icinga'

        self.smtpcon.sendmail(self.sender, self.receiver, message.as_string())

        return time_send

    def disconnect_smtp(self):
        self.smtpcon.quit()


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s v' +
                        sys.modules[__name__].__version__)

    parser.add_argument('--smtp_host', '-sh',
                        help='The host address or FQDN of the SMTP server',
                        required=True,
                        dest='smtp_host')

    parser.add_argument('--smtp_port', '-sp',
                        help='The port of the SMTP server',
                        type=int,
                        required=True,
                        dest='smtp_port')

    parser.add_argument('--smtp_user', '-susr',
                        help='The username who logs into exchange(env SMTP_USERNAME)',
                        required=True,
                        dest='smtp_user',
                        default=os.getenv('SMTP_USERNAME'))

    parser.add_argument('--smtp_password', '-spw',
                        help='The password for the username (env SMTP_PASSWORD)',
                        required=True,
                        dest='smtp_password',
                        default=os.getenv('SMTP_PASSWORD'))

    parser.add_argument('--imap_host', '-ih',
                        help='The host address or FQDN of the IMAP server',
                        required=True,
                        dest='imap_host')

    parser.add_argument('--imap_port', '-ip',
                        help='The port of the IMAP server',
                        required=True,
                        type=int,
                        dest='imap_port')

    parser.add_argument('--imap_user', '-iusr',
                        help='The username who logs into exchange (env IMAP_USERNAME)',
                        required=True,
                        dest='imapUser',
                        default=os.getenv('IMAP_USERNAME'))

    parser.add_argument('--imap_password', '-ipw',
                        help='The password of the username (env IMAP_PASSWORD)',
                        required=True,
                        dest='imap_password',
                        default=os.getenv('IMAP_PASSWORD'))

    parser.add_argument('--imap_mailbox', '-if',
                        help='The mailbox which is checked',
                        required=True,
                        default='INBOX',
                        dest='imap_mailbox')

    parser.add_argument('--sender',
                        help='The value of the From: header (required)',
                        required=True,
                        dest='sender')

    parser.add_argument('--receiver',
                        help='The value of the TO: header (required)',
                        required=True,
                        dest='receiver')

    parser.add_argument('--warning', '-w',
                        help='The value of warning threshold',
                        type=int,
                        default=5,
                        required=True,
                        dest='warning')

    parser.add_argument('--critical', '-c',
                        help='The value of critical threshold',
                        type=int,
                        default=10,
                        required=True,
                        dest='critical')
    
    reply_group = parser.add_argument_group('Echo reply from mail server')

    reply_group.add_argument('--echo_reply',
                             help='Check echo reply from server',
                             default=True,
                             action='store_true',
                             dest='echo_reply')

    reply_group.add_argument('--imap_sender_host',
                             help='The host address or FQDN of the IMAP server which send the mail (just for cleanup echo replies)',
                             dest='imap_sender_host')

    reply_group.add_argument('--imap_sender_port',
                             help='The port of the IMAP server (just for cleanup echo replies)',
                             type=int,
                             dest='imap_sender_port')

    reply_group.add_argument('--imap_sender_user',
                             help='The username who logs into exchange (env IMAP_SENDER_USER)',
                             dest='imap_sender_user',
                             default=os.getenv('IMAP_SENDER_USER'))

    reply_group.add_argument('--imap_sender_password',
                             help='The password of the user (just for cleanup echo replies)',
                             dest='imap_sender_password',
                             default=os.getenv('IMAP_SENDER_PASSWORD'))

    reply_group.add_argument('--imap_sender_mailbox',
                             help='The mailbox which is checked (just for cleanup echo replies)',
                             dest='imap_sender_mailbox')

    cleanup_group = parser.add_argument_group('Use this arguments to cleanup send mails')

    cleanup_group.add_argument('--cleanup',
                               help='Deletes old mails',
                               default=False,
                               action='store_true',
                               dest='cleanup')

    cleanup_group.add_argument('--cleanup_time',
                               help='Deletes mails older then x minutes',
                               type=int,
                               default=300,
                               dest='cleanup_time')

    cleanup_group.add_argument('--reply_name',
                               help='Specifies the name the of the reply (just for cleanup echo replies)',
                               dest='reply_name')

    args = parser.parse_args()

    # TODO: Refactor argparser. Make explicit choices.
    # Rewrite help text!

    if args.cleanup and (args.imap_sender_host is None or
                         args.imap_sender_user is None or
                         args.imap_sender_password is None or
                         args.imap_sender_mailbox is None or
                         args.replyName is None
                         ):
        parser.error('--cleanup requires: --replyName, --imap_sender_host, --imap_sender_port, --imap_sender_user, --imap_sender_password, --imap_sender_mailbox')

    # TODO: fix exit code to 3 when parser error

    # Environment variables, so the credentials
    # are hidden in process from other users
    # Put into parser
    """ envsmtp_password = os.getenv('SMTP_PASSWORD')
    if envsmtp_password:
        args.smtp_password = envsmtp_password

    envsmtp_username = os.getenv('SMTP_USERNAME')
    if envsmtp_username:
        args.smtp_user = envsmtp_username

    envImapUsername = os.getenv('IMAP_USERNAME')
    if envImapUsername:
        args.imapUsername = envImapUsername

    envimap_password = os.getenv('IMAP_PASSWORD')
    if envimap_password:
        args.imap_password = envimap_password

    envimap_sender_username = os.getenv('IMAP_SENDER_USERNAME')
    if envimap_sender_username:
        args.imap_sender_user = envimap_sender_username

    envimap_sender_password = os.getenv('IMAP_SENDER_PASSWORD')
    if envimap_sender_password:
        args.imap_sender_password = envimap_sender_password """

    return parser.parse_args()


def main():
    try:
        parsed = parse_arguments()
    except SystemExit:
        sys.exit(STATUS_UNKNOWN)

    state_remote_imap = STATUS_UNKNOWN
    state_reply_imap = STATUS_UNKNOWN
    pluginoutput = ''

    # First block test the SMTP 'connection', 'authentication' and 'socket'.
    # If exception is thrown, the program exits with return code
    
    # Send mail
    try:
        conn_smtp = SmtpConnection(parsed.smtp_host,
                                    parsed.smtp_port,
                                    parsed.smtp_user,
                                    parsed.smtp_password,
                                    parsed.sender,
                                    parsed.receiver)
        subject = conn_smtp.subject
        conn_smtp.connect()
        time_send = conn_smtp.send()
        conn_smtp.disconnect_smtp()

    except smtplib.SMTPConnectError as e:
        plugin_exit('SMTP Connection Error: %s' % e[1],
                    STATUS_UNKNOWN)
    except smtplib.SMTPAuthenticationError as a:
        plugin_exit('SMTP Authentication Error: %s' % a[1],
                    STATUS_UNKNOWN)
    except gaierror as g:
        plugin_exit('SMTP Host "%s" not reachable: %s' % (conn_smtp.host, g),
                    STATUS_UNKNOWN)

    else:
        # Search email on remote IMAP
        try:
            conn_remote_imap = ImapConnection(parsed.imap_host,
                                              parsed.imap_port,
                                              parsed.imap_user,
                                              parsed.imap_password,
                                              parsed.imap_mailbox,
                                              subject,
                                              parsed.cleanup)
            conn_remote_imap.connect()

            # search_mail returns [state, unix timestamp]
            state_received = conn_remote_imap.search_mail(parsed.warning,
                                                          parsed.critical,
                                                          parsed.cleanup_time)

            time_delta_received = state_received[1] - time_send

            # TODO: Refactor
            if (state_received[0] == STATUS_CRITICAL):
                plugin_exit('Email cloud not be fetched', STATUS_CRITICAL)
            elif (state_received[0] == STATUS_WARNING):
                state_remote_imap = STATUS_WARNING
            elif (state_received[0] == STATUS_OK): 
                state_remote_imap = STATUS_OK

            if parsed.echo_reply is False:
                pluginoutput += "%s - Email received in %ds" % (conn_remote_imap.host, time_delta_received)

                perfdata = {
                    'receive': time_delta_received
                }

            conn_remote_imap.disconnect_imap()

        except imaplib.IMAP4.error as e:
            plugin_exit('IMAP: %s' % e,
                        STATUS_UNKNOWN)

        except gaierror as g:
            plugin_exit('IMAP Host "%s" not reachable: %s' % (conn_remote_imap.host, g),
                        STATUS_UNKNOWN)

        else:
            if parsed.echo_reply:
            # Search echo replys
                try:
                    conn_sender_imap = ImapConnection(parsed.imap_sender_host,
                                                    parsed.imap_sender_port,
                                                    parsed.imap_sender_user,
                                                    parsed.imap_sender_password,
                                                    parsed.imap_sender_mailbox,
                                                    subject,
                                                    parsed.cleanup)
                    conn_sender_imap.connect()

                    state_reply = conn_sender_imap.search_mail(parsed.warning,
                                                               parsed.critical,
                                                               parsed.cleanup_time)

                    time_delta_reply = state_reply[1] - state_received[1]
                    time_delta_loop = time_delta_received + time_delta_reply

                    # TODO: Refactor
                    if (state_reply[0] == STATUS_CRITICAL):
                        plugin_exit('Reply email cloud not be fetched',
                                    STATUS_CRITICAL)
                    elif (state_reply[0] == STATUS_WARNING):
                        state_reply_imap = STATUS_WARNING
                    elif (state_reply[0] == STATUS_OK):
                        state_reply_imap = STATUS_OK

                    pluginoutput += "Email loop took %ds" % time_delta_loop

                    perfdata = {
                        'receive': time_delta_received,
                        'reply': time_delta_reply,
                        'loop': time_delta_loop
                    }

                    if parsed.cleanup:
                        conn_sender_imap.cleanup(parsed.reply_name)

                    conn_sender_imap.disconnect_imap()

                except imaplib.IMAP4.error as e:
                    if str(e) == 'command SEARCH illegal in state AUTH, only allowed in states SELECTED':
                        plugin_exit('IMAP: Given Mailbox is not available',
                                    STATUS_UNKNOWN)
                    else:
                        plugin_exit('IMAP: %s' % e, STATUS_UNKNOWN)
                except gaierror as g:
                    plugin_exit('IMAP Host "%s" not reachable: %s' % (conn_remote_imap.host, g),
                                STATUS_UNKNOWN)
                except socketerror as s:
                    plugin_exit('IMAP Connection Timeout. Wrong port?: %s' % s,
                                STATUS_UNKNOWN)

                max_state = max(state_remote_imap, state_reply_imap)
                plugin_exit(pluginoutput, max_state, [], perfdata)
            else:
                plugin_exit(pluginoutput, state_remote_imap, [], perfdata)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("UNKNOWN: Python error: %s" % e.message)
        sys.exit(3)
