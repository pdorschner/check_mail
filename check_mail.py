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
    import socket

    from email.mime.text import MIMEText
    from socket import gaierror, error as socketerror
except Exception as e:
    print("UNKNOWN: Failure during import: %s" % e.message)
    sys.exit(3)

__version__ = '0.1.0'

# Icinga states
STATUS_OK = 0
STATUS_WARNING = 1
STATUS_CRITICAL = 2
STATUS_UNKNOWN = 3
STATUS_NAMES = [
    'OK',
    'WARNING',
    'CRITICAL',
    'UNKNOWN',
]

PORT_IMAP = 143
PORT_IMAPS = 993
PORT_SMTP = 25
PORT_SMTPS = 465


def plugin_exit(label, state=STATUS_UNKNOWN, lines=None, perfdata=None, name='check_email'):
    if state > len(STATUS_NAMES):
        raise RuntimeError('State programming error')

    print('%s - %s: %s' % (STATUS_NAMES[state], name, str(label)))

    if lines:
        for line in lines:
            print(line)

    if perfdata:
        output = '| '
        for key, value in perfdata.items():
            output += "'%s'=%s\n" % (key, value)
        print(output)

    sys.exit(state)


class ImapConnection(object):
    def __init__(self, host, port, user, password,
                 mailbox, mailsubject, clean, mode=None):
        self.host = host
        self.port = port if port else PORT_IMAPS
        self.user = user
        self.password = password
        self.mailbox = mailbox
        self.mailsubject = mailsubject
        self.clean = clean

        # TODO: starttls only supported in Python >= 3.2
        if mode:
            self.mode = mode
        elif port == PORT_IMAPS:
            self.mode = 'ssl'
        else:
            self.mode = 'plain'

        self.imapcon = None

    def connect(self):
        """
        connects to the IMAP server

        TODO: starttls only supported in Python >= 3.2
        :return:
        """
        # Set global timeout for conncetions
        socket.setdefaulttimeout(5)
        if self.mode == 'ssl':
            self.imapcon = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            self.imapcon = imaplib.IMAP4(self.host, self.port)

        # self.imapcon.debug = 4
        self.imapcon.login(self.user, self.password)

    def disconnect_imap(self):
        self.imapcon.close()
        self.imapcon.logout()

    def search_mail(self, warning, critical, cleanup_time):
        # time_crit defines the critical threshold
        time_crit = time.time() + critical
        # time_warn defines the warning threshold
        time_warn = time.time() + warning

        while True:
            self.imapcon.select(self.mailbox)
            return_value, message_data = self.imapcon.search(None, 'ALL')

            for message_id in message_data[0].split():
                return_value, message_data = self.imapcon.fetch(
                    message_id, '(RFC822)')
                raw_email = email.message_from_string(message_data[0][1])  # type: email.message.Message

                # TODO: Refactor
                email_subject = raw_email.get('Subject')
                email_customtag = raw_email.get('X-Custom-Tag')

                # TODO: Date header is not required
                if self.clean and 'Date' in raw_email:
                    email_date_as_unix = email.utils.mktime_tz(
                        email.utils.parsedate_tz(
                            raw_email['Date']))

                    # time_cleanup deletes mails older then 1 hour
                    time_cleanup = time.time() - int(cleanup_time)
                    if email_date_as_unix < time_cleanup and email_customtag == 'Email-Check-Icinga':
                        self.imapcon.store(message_id, '+FLAGS', '\\Deleted')

                if self.mailsubject in email_subject:
                    # Actual timestamp of received email has to be parsed.
                    # 'Received' field contains a (possibly empty) list of
                    # name/value pairs followed by a semicolon and a date-time
                    # specification. Parse the date after semicolon to get the
                    # time when the server actually received the mail
                    # (RFC 2822 | 3.6.7)
                    # TODO: regex is very expensive
                    # search an alternative solution
                    email_server_date_as_unix = raw_email['Received']
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

    def cleanup(self, reply_name, cleanup_time):
        self.imapcon.select(self.mailbox)
        time_cleanup = time.time() - cleanup_time

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
    def __init__(self, host, port, user, password, sender, receiver, mode=None):
        self.host = host
        self.port = port if port else PORT_SMTPS
        self.user = user
        self.password = password
        self.sender = sender
        self.receiver = receiver
        self.subject = ''.join(random.choice(string.ascii_uppercase +
                                             string.ascii_lowercase +
                                             string.digits) for _ in range(6))

        if mode:
            self.mode = mode
        elif self.port == PORT_SMTPS:
            self.mode = 'ssl'
        else:
            self.mode = 'tls'

        self.smtpcon = None

    def connect(self):
        # Set global timeout for conncetions
        socket.setdefaulttimeout(5)
        if self.mode == 'ssl':
            self.smtpcon = smtplib.SMTP_SSL(self.host, self.port)
        else:
            self.smtpcon = smtplib.SMTP(self.host, self.port)

        if self.mode == 'tls':
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

    def disconnect(self):
        self.smtpcon.quit()
        self.smtpcon = None


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s v' + __version__)

    parser.add_argument('--smtp-host', '-sh',
                        help='host address or FQDN of the SMTP server',
                        required=True)

    parser.add_argument('--smtp-port', '-sp',
                        help='port of the SMTP server',
                        type=int)

    parser.add_argument('--smtp-user', '-susr',
                        help='username for SMTP default: (env SMTP_USERNAME)',
                        required=not os.getenv('SMTP_USERNAME'),
                        default=os.getenv('SMTP_USERNAME'))

    parser.add_argument('--smtp-password', '-spw',
                        help='password for SMTP default: (env SMTP_PASSWORD)',
                        required=not os.getenv('SMTP_PASSWORD'),
                        default=os.getenv('SMTP_PASSWORD'))

    parser.add_argument('--imap-host', '-ih',
                        help='host address or FQDN of the IMAP server',
                        required=True)

    parser.add_argument('--imap-port', '-ip',
                        help='port of the IMAP server',
                        type=int,
                        default=PORT_IMAPS)

    parser.add_argument('--imap-user', '-iusr',
                        help='username for IMAP default: (env IMAP_USERNAME)',
                        required=not os.getenv('IMAP_USERNAME'),
                        default=os.getenv('IMAP_USERNAME'))

    parser.add_argument('--imap-password', '-ipw',
                        help='password for IMAP default: (env IMAP_PASSWORD)',
                        required=not os.getenv('IMAP_PASSWORD'),
                        default=os.getenv('IMAP_PASSWORD'))

    parser.add_argument('--imap-mailbox', '-if',
                        help='mailbox which should be checked',
                        default='INBOX')

    parser.add_argument('--sender',
                        help='Sender email e.g. "sender@mail.com"',
                        required=True)

    parser.add_argument('--receiver',
                        help='Receiver email e.g. "receiver@mail.com"',
                        required=True)

    parser.add_argument('--warning', '-w',
                        help='value of warning threshold in seconds default: 300',
                        type=int,
                        default=300)

    parser.add_argument('--critical', '-c',
                        help='value of critical threshold in seconds default: 500',
                        type=int,
                        default=500)

    reply_group = parser.add_argument_group('If an echo reply is configured on the receiver mail server')

    reply_group.add_argument('--echo-reply',
                             help='Checks for echo reply from mail server',
                             action='store_true')

    # TODO: by default same IMAP account?

    reply_group.add_argument('--imap-sender-host',
                             help='host address or FQDN of the IMAP server which sent the mail')

    reply_group.add_argument('--imap-sender-port',
                             help='port of the IMAP server which sent the mail',
                             type=int,
                             default=PORT_IMAPS)

    reply_group.add_argument('--imap-sender-user',
                             help='username for IMAP, which receive the echo reply, default:(env IMAP_SENDER_USER)',
                             default=os.getenv('IMAP_SENDER_USER'))

    reply_group.add_argument('--imap-sender-password',
                             help='password for IMAP user, which receive the echo reply,'
                                  + 'default:(env IMAP_SENDER_PASSWORD)',
                             default=os.getenv('IMAP_SENDER_PASSWORD'))

    reply_group.add_argument('--imap-sender-mailbox',
                             help='mailbox which should be checked for echo reply',
                             default='INBOX')

    # TODO: defaults?

    reply_group.add_argument('--critical-reply',
                             help='critical threshold for echo reply',
                             type=int)

    reply_group.add_argument('--warning-reply',
                             help='warning threshold for echo reply',
                             type=int)

    cleanup_group = parser.add_argument_group('Use these arguments to cleanup sent mails/echo replies')

    cleanup_group.add_argument('--cleanup',
                               help='Deletes old mails, default: False',
                               action='store_true')

    cleanup_group.add_argument('--cleanup-time',
                               help='Deletes mails older then x seconds, default: 3600',
                               type=int,
                               default=3600)

    cleanup_group.add_argument('--reply-name',
                               help='Specifies the name the of the echo reply, e.g. "My Echo"')

    args = parser.parse_args()

    # TODO: Refactor argparser. Make explicit choices.
    if args.echo_reply and (args.imap_sender_host is None or
                            args.imap_sender_port is None or
                            args.imap_sender_user is None or
                            args.imap_sender_password is None or
                            args.imap_sender_mailbox is None or
                            args.critical_reply is None or
                            args.warning_reply is None):
        parser.error(
            'The --echo-reply argument requires all arguments of:\n'
            + '--imap-sender-host, --imap-sender-port, --imap-sender-user, --imap-sender-password,'
            + ' --imap-sender-mailbox, --warning-reply, --critical-reply')

    if (args.echo_reply and args.cleanup) and (args.imap_sender_host is None or
                                               args.imap_sender_port is None or
                                               args.imap_sender_user is None or
                                               args.imap_sender_password is None or
                                               args.imap_sender_mailbox is None or
                                               args.reply_name is None):
        parser.error('The --cleanup together with --echo-reply argument requires: --reply-name')

    if args.cleanup and args.cleanup_time is None:
        parser.error('The --cleanup argument requires: --cleanup-time')

    return parser.parse_args()


def main():
    try:
        parsed = parse_arguments()
    except argparse.ArgumentError as err:
        plugin_exit('Error in arguments: %s' % err, STATUS_UNKNOWN)

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
        conn_smtp.disconnect()

    except smtplib.SMTPConnectError as err:
        plugin_exit('SMTP Connection Error: %s' % err[1],
                    STATUS_UNKNOWN)
    except smtplib.SMTPAuthenticationError as a:
        plugin_exit('SMTP Authentication Error: %s' % a[1],
                    STATUS_UNKNOWN)
    except gaierror as g:
        plugin_exit('SMTP Host "%s" not reachable: %s' % (conn_smtp.host, g),
                    STATUS_UNKNOWN)
    except smtplib.SMTPSenderRefused:
        plugin_exit('SMTP sender has an invalid email address',
                    STATUS_UNKNOWN)
    except smtplib.SMTPRecipientsRefused:
        plugin_exit('SMTP receiver has an invalid email address',
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

            # TODO: Refactor
            if (state_received[0] == STATUS_CRITICAL):
                plugin_exit('Email cloud not be fetched', STATUS_CRITICAL)
            elif (state_received[0] == STATUS_WARNING):
                time_delta_received = state_received[1] - time_send
                pluginoutput = '%s took %ds to receive mail' % (conn_remote_imap.host, time_delta_received)
                state_remote_imap = STATUS_WARNING
            elif (state_received[0] == STATUS_OK):
                time_delta_received = state_received[1] - time_send
                state_remote_imap = STATUS_OK

            if parsed.echo_reply is False:
                pluginoutput += "%s - Email received in %ds" % (conn_remote_imap.host, time_delta_received)
                perfdata = {
                    'receive': time_delta_received
                }

            conn_remote_imap.disconnect_imap()

        except imaplib.IMAP4.error as err:
            plugin_exit('IMAP: %s' % err,
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

                    state_reply = conn_sender_imap.search_mail(parsed.warning_reply,
                                                               parsed.critical_reply,
                                                               parsed.cleanup_time)

                    # TODO: Refactor
                    if (state_reply[0] == STATUS_CRITICAL):
                        plugin_exit('Reply email cloud not be fetched',
                                    STATUS_CRITICAL)
                    elif (state_reply[0] == STATUS_WARNING):
                        time_delta_reply = state_reply[1] - state_received[1]
                        time_delta_loop = time_delta_received + time_delta_reply
                        pluginoutput = '%s took %ds to reply' % (conn_remote_imap.host, time_delta_reply)
                        state_reply_imap = STATUS_WARNING
                    elif (state_reply[0] == STATUS_OK):
                        time_delta_reply = state_reply[1] - state_received[1]
                        time_delta_loop = time_delta_received + time_delta_reply
                        state_reply_imap = STATUS_OK
                        if state_remote_imap is not STATUS_WARNING:
                            pluginoutput += "Email loop took %ds" % time_delta_loop

                    perfdata = {
                        'receive': time_delta_received,
                        'reply': time_delta_reply,
                        'loop': time_delta_loop
                    }

                    if parsed.cleanup:
                        conn_sender_imap.cleanup(parsed.reply_name, parsed.cleanup_time)

                    conn_sender_imap.disconnect_imap()

                except imaplib.IMAP4.error as err:
                    if str(err) == 'command SEARCH illegal in state AUTH, only allowed in states SELECTED':
                        plugin_exit('IMAP: Given Mailbox is not available',
                                    STATUS_UNKNOWN)
                    else:
                        plugin_exit('IMAP: %s' % err, STATUS_UNKNOWN)
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
