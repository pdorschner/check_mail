# check_email

Plugin to check an email loop.
Logs into an Exchange Server (AUTH_LOGIN) and sends an email to a given receiver. After a short time the plugin connects via IMAP
to another Exchagne and parses the `subject` and the first line of the `body`.

WIP - Use with caution. You can delete your mails

# Usage

	usage: check_mail.py [-h] [-V] -sh SMTPHOST -sp SMTPPORT -susr SMTPUSER -spw
                     SMTPPASSWORD -ih IMAPHOST -ip IMAPPORT -iusr IMAPUSER
                     -ipw IMAPPASSWORD -if IMAPFOLDER -send SENDER -rec
                     RECEIVER -w WARNING -c CRITICAL [--cleanup]
                     [--cleanupTime CLEANUPTIME] [--replyName REPLYNAME]
                     [--imapSenderHost IMAPSENDERHOST]
                     [--imapSenderPort IMAPSENDERPORT]
                     [--imapSenderUser IMAPSENDERUSER]
                     [--imapSenderPassword IMAPSENDERPASSWORD]
                     [--imapSenderFolder IMAPSENDERFOLDER]

# Example

	./check_mail.py -sh='exchange.int.netways.de' \
			-sp=587 \
			-susr='NETWAYS\xxx' \
			-spw='xxx' \
			-send='philipp.dorschner@netways.de' \
			-ih='imap.gmx.net' \
			-ip=993 \
			-iusr='test@gmx.de' \
			-ipw='xxx'\
			-rec='test@gmx.de' \
			-if='Monitoring' \
			-w=600 \
			-c=1200 \
			--cleanup \
			--cleanupTime=300 \
			--imapSenderHost='exchange.int.netways.de' \
			--imapSenderPort=993 \
			--imapSenderUser='NETWAYS\xxx' \
			--imapSenderPassword='xxx'
			--imapSenderFolder='Monitoring'
			--replyName='philipp.dorsch'
