# Postfix_Spammer_Filter
A content filter function using MessageQueue with RPC implementation.

## Server-Side Envionment
#### Python packages
Required packages are shown in requirements file.
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
Finally, using install.py and per_user_install.py to setup your queue routing
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

localhost:10026	inet	n		-		n		-		10		smtpd
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

## Client-Side Environment
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
