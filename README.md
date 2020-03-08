# WIP - Use with caution. You can delete your mails

# check_email

Plugin to check an email loop (send mail to receiver and get an echo reply) or in standlone to check email to be received in the given time.

## Environment varibales
If prefered to set environment variables on the imap and smtp credentials:

	export IMAP_USERNAME='username'
	export IMAP_PASSWORD='password'
	export SMTP_USERNAME='username'
	export SMTP_PASSWORD='password'
	export IMAP_SENDER_USERNAME='username'
	export IMAP_SENDER_PASSWORD='password'

If these environment varibales are set, the plugin searches for it and implements them into the code.

## Email loop
Connects via SMTP to the given server and sends an email, with a  generated unique hash subject, to the remote mail server.
Is the email send, the plugin connects via IMAP to the remote mail server and search for the unique hash in the given mailbox.
An echo reply from the remote mail server should be send to proof the receipt of the before send email and the plugin searches for it in the given mailbox of the "sender" mail server.

## Standalone
Connects via SMTP to the given server and sends an email, with a  generated unique hash subject, to the remote mail server.
Is the email send, the plugin connects via IMAP to the remote mail server and search for the unique hash in the given mailbox.

## Cleanup
The plugin offers an `cleanup`option to delete the send mails and reply messages in a given time.

# Usage
	usage: check_mail.py [-h] [-V] --smtp_host SMTP_HOST --smtp_port SMTP_PORT
                     [--smtp_user SMTP_USER] [--smtp_password SMTP_PASSWORD]
                     --imap_host IMAP_HOST --imap_port IMAP_PORT
                     [--imap_user IMAP_USER] [--imap_password IMAP_PASSWORD]
                     --imap_mailbox IMAP_MAILBOX --sender SENDER --receiver
                     RECEIVER --warning WARNING --critical CRITICAL
                     [--echo_reply] [--imap_sender_host IMAP_SENDER_HOST]
                     [--imap_sender_port IMAP_SENDER_PORT]
                     [--imap_sender_user IMAP_SENDER_USER]
                     [--imap_sender_password IMAP_SENDER_PASSWORD]
                     [--imap_sender_mailbox IMAP_SENDER_MAILBOX]
                     [--critical_reply CRITICAL_REPLY]
                     [--warning_reply WARNING_REPLY] [--cleanup]
                     [--cleanup_time CLEANUP_TIME] [--reply_name REPLY_NAME]

## Email loop example with cleanup
	./check_mail.py -sh='exchange.int.netways.de' \
			-sp=587 \
			-susr='NETWAYS\xxx' 
			-spw='xxx' \
			-send='philipp.dorschner@netways.de' \
			-ih='imap.gmx.net' \
			-ip=993 \
			-iusr='test@gmx.de' \
			-ipw='xxx'\
			-rec='test@gmx.de' \
			-if='Monitoring' \
			-w=300 \
			-c=500 \
			--echo_reply \
			--imapSenderHost='exchange.int.netways.de' \
			--imapSenderPort=993 \
			--imapSenderUser='NETWAYS\xxx' \
			--imapSenderPassword='xxx'
			--imapSenderFolder='Monitoring'
			--replyName='philipp.dorsch'
			--warning_reply=300 \
			--critical_reply=500 \
			--cleanup \
			--cleanup_time=300

### Output - Email loop example with cleanup
	OK - check_email: Email loop took 7s|'receive'=3 'reply'=4 'loop'=7

## Standalone example without cleanup
	./check_mail.py -sh='exchange.int.netways.de' \
			-sp=587 \
			-susr='NETWAYS\xxx' 
			-spw='xxx' \
			-send='philipp.dorschner@netways.de' \
			-ih='imap.gmx.net' \
			-ip=993 \
			-iusr='test@gmx.de' \
			-ipw='xxx'\
			-rec='test@gmx.de' \
			-if='Monitoring' \
			-w=300 \
			-c=500

### Output - Standalone example without cleanup
	OK - check_email: imap.gmx.net - Email received in 3s|'receive'=3
					
