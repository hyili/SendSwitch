# Email-Content-Filter-Framework
An `Email-Content-Filter-Framework` project is a user-aware content filter which works for Postfix.

## About
A `Content-Filter-Server` is a content filter program, which receives emails via SMTP, and pushes emails into MessageQueue as RPC requests.
With combination of MessageQueue's Pub/Sub, RPC, Authentication, and Authorization, which gave `Content-Filter-Server` the ability to distribute the incoming emails to many of individual `Content-Filter-Clients`.
A `Content-Filter-Client` gets its own emails from MessageQueue, and can apply lots of processors on it, such as filtering, webhook, or notifying to other apps.
After handled by processors, `Content-Filter-Client` can send a RPC response back into MessageQueue with an action in it, that tells the `Content-Filter-Server` how to handle this email.

With this project, traditional mailbox or maildir delivery may become a backup method of email delivery.

The `Email-Content-Filter-Framewor` may work with other SMTP MTAs, because of its support of SMTP, but we haven't tested yet.
It requires at least Python 3.5 to run.

## Related Projects
- aiosmtpd: https://github.com/aio-libs/aiosmtpd
- flask: http://flask.pocoo.org/
- Postfix: http://www.postfix.org/
- RabbitMQ: https://www.rabbitmq.com/
- OpenLDAP: https://www.openldap.org/

## Server-Side Envionment Setup
```
git clone https://github.com/hyili/Email-Content-Filter-Framework.git
git submodule update --init
```
#### Python packages
Required packages are listed in requirements file.
use following command to install them
```
pip3 install -r requirements
```
#### RabbitMQ
Install RabbitMQ on your system, and you can use sample rabbitmq configuration in config/ to setup.
Make sure your server can connect to RabbitMQ server.
Then run following command
```
rabbitmq-plugins enable rabbitmq_management
rabbitmq-plugins enable rabbitmq_auth_backend_ldap
rabbitmq-plugins enable rabbitmq_shovel
rabbitmq-plugins enable rabbitmq_shovel_management
```
Finally, using apps/install.py and apps/per_user_install.py to setup your queue routing
#### Postfix
Install Postfix on your system, and modify the following
- in master.cf
```
smtp      inet  n       -       n       -       -       smtpd
	-o content_filter=scan:127.0.0.1:8025

scan	unix	-		-		n		-		10		smtp
	-o smtp_send_xforward_command=yes
	-o disable_mime_output_conversion=yes
	-o smtp_generic_maps=

localhost:10025	inet	n		-		n		-		10		smtpd
	-o smtpd_tls_security_level=
	-o smtpd_sasl_auth_enable=no
	-o content_filter=
	-o receive_override_options=no_unknown_recipient_checks,no_header_body_checks,no_milters
	-o smtpd_helo_restrictions=
	-o smtpd_client_restrictions=
	-o smtpd_sender_restrictions=
	-o smtpd_relay_restrictions=
	-o smtpd_recipient_restrictions=permit_mynetworks,reject
	-o mynetworks=127.0.0.0/8
	-o smtpd_authorized_xforward_hosts=127.0.0.0/8
```
#### apps/server.py
- Module for handling SMTP/SMTPD/MessageQueue message interaction
- in config/server_config.py
	- copy config/example/example_server_config.py to config/server_config.py modify it to fit your environment
- sample usage
```
./server.py
```

## Client-Side Environment Setup
```
git clone https://github.com/hyili/Email-Content-Filter-Framework.git
git submodule update --init
```
#### apps/client.py
- Module for handling user's incoming email get from MessageQueue
- in config/client_config.py
	- copy config/example/example_client_config.py to config/client_config.py modify it to fit your environment and add some customized processors
- sample usage
```
./client.py
```

## Other Scripts
#### apps/install.py
- Setup for global MessageQueue setting
- sample usage
```
./install.py
```
#### apps/per_user_install.py
- Setup for per-user MessageQueue setting
- sample usage
```
./per_user_install.py [username]
```

#### tests/example_server.py
- Example SMTP server using Python

#### tests/example_client.py
- Example SMTP client for sending email using Python

## Features
- [x] Performance is Okay.
	- [x] Based on aiosmtpd with asynchronous smtpd
	- [x] Based on smtplib and asyncio run_in_executor() to handle non-blocking send_mail function
- [x] Very simple Web GUI interface.
- [x] Incoming emails to JSON, to Webhook, to file.
- [x] Simple logging mechanism.
- [x] Multiple Processors for Clients to use.
	- [x] Sample PASS processor
	- [x] Webhook processor
	- [x] Blacklist Whitelist processor
- [ ] Outgoing emails including Send Email API.
- [ ] DSN & RSN
- [ ] Response actions
	- [x] PENDING
	- [x] PASS
	- [x] DENY
	- [ ] SPAM
	- [ ] VIRUS
	- [ ] FORWARD
	- [ ] QUARATINE

## Naming Rule
#### class
- For example:
```
class SomethingLikeThis():
```
#### function
- For example:
```
def something_like_this():
```
#### variable
- For example:
```
something_like_this
```
