# check_email

Plugin to check an email loop.
Logs into an Exchange Server (AUTH_LOGIN) and sends an email to a given receiver. After a short time the plugin connects via IMAP
to another Exchagne and parses the `subject` and the first line of the `body`.

WIP

# Usage

	usage: check_mail.py [-h] [-V] [-sh SMTPHOST] [-sp SMTPPORT] [-susr SMTPUSER]
                     [-spw SMTPPASSWORD] [-ih IMAPHOST] [-ip IMAPPORT]
                     [-iusr IMAPUSER] [-ipw IMAPPASSWORD] [-if IMAPFOLDER]
                     [-send SENDER] [-rec RECEIVER]

# Example

	./check_mail.py -sh='exchange.int.netways.de' \
			-sp=587 \
			-susr='NETWAYS\xxx' \
			-spw='xxx' -ih='exchange.int.netways.de'\
			-ip=143\
			-iusr='NETWAYS\xxx'\
			-ipw='xxx'\
			-send='philipp.dorschner@netways.de'\
			-rec='philipp.dorschner@netways.de'\
			-if='Monitoring'

