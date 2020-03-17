# WIP - Use with caution. You can delete your mails

# check_email
This plugin sends an email via SMTP to a given email-address and evaluates the email receipt via IMAP.

Check_email offers three modes:

## Standard
In the standard mode *(default)*, the plugin sends an email with an unique (hash) subject and *X-Custom-Tag*, via SMTP, to the specified email-address. Afterwards the plugin connects via IMAP to the given mail account and searches in the given mailbox for the before sent email. Dependent on the thresholds, the plugin searches through the mailbox until the critical threshold is exceeded.<br>
The required arguments are:<br>
      `--imap-host` `--imap-port` `--imap-user` `--imap-password` `--imap-mailbox`<br>
      `--smtp-host` `--smtp-port` `--smtp-user` `--smtp-password` `--sender` `--receiver`<br>
      `--critical`   `--warning`

## Echo reply
The *--echo_reply* mode extends the standard mode to search for an *echo-mail*. The plugin assumes that an *echo-mail* will be automatically sent from a mail server, to inform the sender of the previous sent email that the email has been delivered. Therefore, the plugin searches for this specified *echo-mail* in the mailbox of the sender account via IMAP. Usually the *echo-mail* subject contains the same subject as the previous sent email e.g.: “RE: Subject” 
>NOTE: This *echo function* has to be configured on the mail server.

The additional required arguments are:<br>
      `--echo-reply`<br>
      `--imap-sender_host` `--imap-sender-port` `--imap-sender-user` `--imap-sender-password` `--imap-sender-mailbox`<br>
      `--critical-reply`     `--warning-reply`

## Clean up
In order to avoid a full mailbox of *echo-mails* and *check-mails*, there is an option *--cleanup* to sweep away the previous mentioned emails.
>Use this option with caution, it cloud delete involuntary emails if the wrong *--imap-mailbox*, *--imap-sender-mailbox* or *--reply-name* is specified!

The additional required arguments are:<br>
      `--cleanup`<br>
      `--cleanup-time`<br>
      `--reply-name`

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
	usage: check_mail.py [-h] [-V] --smtp-host SMTP_HOST --smtp-port SMTP_PORT
                     [--smtp-user SMTP_USER] [--smtp-password SMTP_PASSWORD]
                     --imap-host IMAP_HOST --imap-port IMAP_PORT
                     [--imap-user IMAP_USER] [--imap-password IMAP_PASSWORD]
                     --imap-mailbox IMAP_MAILBOX --sender SENDER --receiver
                     RECEIVER --warning WARNING --critical CRITICAL
                     [--echo-reply] [--imap-sender-host IMAP_SENDER_HOST]
                     [--imap-sender-port IMAP_SENDER_PORT]
                     [--imap-sender-user IMAP_SENDER_USER]
                     [--imap-sender-password IMAP_SENDER_PASSWORD]
                     [--imap-sender-mailbox IMAP_SENDER_MAILBOX]
                     [--critical-reply CRITICAL_REPLY]
                     [--warning-reply WARNING_REPLY] [--cleanup]
                     [--cleanup-time CLEANUP_TIME] [--reply-name REPLY_NAME]

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
			--imap-mailbox='Monitoring' \
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
			-ipw='***'\
			--receiver='receiver@example.com' \
			--imap-mailbox='Monitoring' \
			-w=300 \
			-c=500 \
			--echo-reply \
			--imap-sender-host='imap.sender.example.com' \
			--imap-sender-port=993 \
			--imap-sender-user='DOMAIN\User' \
			--imap-sender-password='***' \
			--imap-sender-mailbox='Monitoring' \
			--reply-name='Echo Notify' \
			--warning-reply=300 \
			--critical-reply=500 \
			--cleanup \
			--cleanup-time=300
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
>The *sent-mail* and *echo-mail* was found and the plugin returns OK. Additionally, the duration how long each action took will be served as *perfdata*.<br>

>NOTE: The output will be always the *highest* state, e.g.: *receive* is WARNING and *reply* is OK, the plugin output will be WARNING. 

## Configuration
### Icinga 
**IMPORTANT**
`check_timeout` must be greater than the `critical threshold` otherwise the *default timeout* of a plugin could be exceeded and icinga kills its process. As a result, the plugin can never reach the *critical* state.
Moreover `check_interval` has also to be lower than the `check_timeout`. Due to the fact, that the plugin *waits* for an email or rather an event, the execution time could be, in the worst case, higher than the `check_interval`. In such circumstances Icinga triggers *check_email* anew, even if the plugin did not finish correctly.
>See *check_email.conf* for an example configuration

### Mail server
It is recommended to configure rules to manage emails from this plugin. By using a rule, any received email message that match conditions specified in the rule can be automatically forwarded or redirected to another mailbox (**of the same account!**). This is very useful, since the plugin searches through a given mailbox it could be a negative impact if the specified mailbox is bulging with other mails, which also be evaluated.
