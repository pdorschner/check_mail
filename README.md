# WIP - Use with caution. You can delete your mails

# check_email
This plugin sends an email via SMTP to a given email-address and evaluates the email receipt via IMAP.

Check_email offers three modes:

## Standard
In the standard mode *(default)*, the plugin sends an email with an unique (hash) subject and *X-Custom-Tag*, via SMTP, to the specified email-address. Afterwards the plugin connects via IMAP to the given mail account and searches in the given mailbox for the before sent email. Dependent on the thresholds, the plugin searches through the mailbox until the critical threshold is exceeded.<br>
The required arguemnts are:<br>
      `--imap_host` `--imap_port` `--imap_user` `--imap_password` `--imap_mailbox`<br>
      `--smtp_host` `--smtp_port` `--smtp_user` `--smtp_password` `--sender` `--receiver`<br>
      `--critical`  `--warning`

## Echo reply
The *--echo_reply* mode extends the standard mode to search for an *echo-mail*. The plugin assumes that an *echo-mail* will be automatically sent from a mail server, to inform the sender of the previous sent email that the email has been delivered. Therefore, the plugin searches for this specified *echo-mail* in the mailbox of the sender account via IMAP. Usually the *echo-mail* subject contains the same subject as the previous sent email e.g.: “RE: Subject” 
>NOTE: This *echo function* has to be configured on the mail server.

The additional required arguments are:<br>
      `--echo_reply`<br>
      `--imap_sender_host` `--imap_sender_port` `--imap_sender_user` `--imap_sender_password` `--imap_sender_mailbox`<br>
      `--critical_reply`   `--warning_reply`

## Clean up
In order to avoid a full mailbox of *echo-mails* and *check-mails*, there is an option *--cleanup* to sweep away the previous mentioned emails.
>Use this option with caution, it cloud delete involuntary emails if the wrong *--imap_mailbox*, *--imap_sender_mailbox* or *--reply_name* is specified!

The additional required arguments are:<br>
      `--cleanup`<br>
      `--cleanup_time`
      `--reply_name`

### Optional: environment variables
Check_email can gather these following environment variables from the system if they are set:

	export IMAP_USERNAME='username'
	export IMAP_PASSWORD='password'
	export SMTP_USERNAME='username'
	export SMTP_PASSWORD='password'
	export IMAP_SENDER_USERNAME='username'
	export IMAP_SENDER_PASSWORD='password'
>NOTE: It's currently not implemented to define more than one of each *SMTP*, *IMAP* and *IMAP_SENDER*

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

## Standard mode example without cleanup
	./check_mail.py -sh='mail.example.com' \
			-sp=587 \
			-susr='DOMAIN\User' \
			-spw='***' \
			--sender='sender@example.com' \
			-ih='imap.example.com' \
			-ip=993 \
			-iusr='receiver@example.de' \
			-ipw='***' \
			--receiver='receiver@example.de' \
			--imap_mailbox='Monitoring' \
			-w=300 \
			-c=500
>1. The plugin connects to *mail.example.com*, creates an unique hash subject and sends an email to *receiver@example.com*
>2. The plugin connects to *imap.example.com*, searches trough the mailbox *Monitoring*
>3. If the email cannot be found in 300 seconds, the return state will be WARNING
>4. After 500 seconds the plugin will exit and return a CRITICAL

### Output - Standalone example without cleanup
	OK - check_email: imap.example.com - Email received in 3s|'receive'=3
 >The email was found, and the plugin returns OK. Additionally, the duration how long this action took will be served as *perfdata*.

## Echo reply mode example with cleanup:
	./check_mail.py -sh='mail.example.com' \
			-sp=587 \
			-susr='DOMAIN\User' \
			-spw='***' \
			--sender='sender@example.com' \
			-ih='imap.example.com' \
			-ip=993 \
			-iusr='receiver@example.com' \
			-ipw='xxx'\
			--receiver='receiver@example.com' \
			--imap_mailbox='Monitoring' \
			-w=300 \
			-c=500 \
			--echo_reply \
			--imap_sender_host='imap.sender.example.com' \
			--imap_sender_port=993 \
			--imap_sender_user='DOMAIN\User' \
			--imap_sender_password='***' \
			--imap_sender_mailbox='Monitoring' \
			--reply_name='Echo Notify' \
			--warning_reply=300 \
			--critical_reply=500 \
			--cleanup \
			--cleanup_time=300
>1. The plugin connects to *mail.example.com*, creates an unique hash subject and sends an email to *receiver@example.com*.
>2. The plugin connects to *imap.example.com*, searches trough the mailbox *Monitoring*. Additionally, emails with the *X-Custom-Tag* and if they are older then 300 seconds, will be deleted. 
>3. If the email cannot be found in 300 seconds, the state will be WARNING
>4. After 500 seconds the plugin will exit and return a CRITICAL
>5. If the email was found, the plugin connects to *imap.sender.example.com*
>6. The plugin selects the mailbox *Monitoring* and searches for the assumend *echo-mail*, which should contain **Echo Notify** in the subject. Additionally, old *echo-mails*  will be deleted (see 2.)
>7. If the *echo-mail* cannot be found in 300 seconds, the return state will be WARNING
>8. After 500 seconds the plugin will exit and return a CRITICAL

### Output - Email loop example with cleanup
	OK - check_email: Email loop took 7s|'receive'=3 'reply'=4 'loop'=7
>The *sent-mail* and *echo-mail* was found and the plugin returns OK. Additionally, the duration how long this action took will be served as *perfdata*.
>NOTE: The output will be always the *highest* state, e.g.: *receive* is WARNING and *reply* is OK, the plugin output will be WARNING. 


					
