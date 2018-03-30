# Postfix_Spammer_Filter
A content filter function using MessageQueue with RPC implementation.

## contentfilter.py
content filter in postfix
#### sample usage
in master.cf
```
smtp      inet  n       -       n       -       -       smtpd
	-o content_filter=filter:dummy

filter		unix	-	n	n	-	1	pipe
	flags=Rq user=hyili null_sender=
	argv=/home/hyili/Postfix_Spammer_Filter/apps/contentfilter.py -f ${sender} -- ${recipient}
```

## server.py
Module for handling SMTP/SMTPD/MessageQueue message interaction
#### sample usage
```
./server.py
```
in master.cf
```
scan	unix	-		-		n		-		10		smtp
	-o smtp_send_xforward_command=yes
	-o disable_mime_output_conversion=yes
	-o smtp_generic_maps=

localhost:10026	inet	n		-		n		-		10		smtpd
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
#### note
This module will default listen 8025 port for SMTPD input email
And will default send email back to postfix on port 10026
please change "{localhost}" to your server ip


## install.py
Setup for global MessageQueue setting
#### sample usage
```
./install.py
```
#### note
please change "{localhost}" to your server ip


## per_user_install.py
Setup for per-user MessageQueue setting
#### sample usage
```
./per_user_install.py [username]
```


## returnmq.py
Handling return result from client
#### sample usage
```
./returnmq.py
```


## sendmq.py
Module which send message to recvmq.py
#### sample usage
```
./sendmq.py [exchange_id] [routing_key] ...
```
#### note
please change "{localhost}" to your server ip


## recvmq.py
Module which recv message from sendmq.py and then send back the result
#### sample usage
```
./recvmq.py [exchange_id] [routing_key] [virtual_host] [username] [password]
```
#### note
please change "{localhost}" to your server ip
"exchange_id" & "routing_key" are both DEPRECATED


## example_server.py
Example SMTP server using Python


## example_client.py
Example SMTP client for sending email using Python


## apiserver.py
Token server implementation using flask
#### sample usage
```
./apiserver.py
```
#### note
Please change "{localhost}" to your server ip
Used with set_key.sh and get_key.sh


## send_loop.py
Used for performance testing


## TODO
- [x] Content Filter In Postfix
	- [x] Basic Content Filter Implementation
	- [x] Advanced Content Filter Implementation
		- [x] SMTP support
		- [x] SMTPD support
- [x] Request Queue And Response Queue Management
	- [x] Non-blocking Send
	- [x] Non-blocking Receive
	- [x] User-Space Queue Setup
	- [x] Dead Letter Exchange (DLX)
- [x] Server with Send Function
- [x] Client with Recv Function
- [x] RPC Architecture
- [x] Exchange & Routing
- [x] Client Email Parser Example
- [x] System Architecture
- [x] Security
	- [x] Authentication
		- [x] LDAP backend
	- [x] Authorization
		- [x] MQ Permission Setup
	- [x] API For Getting Routing Key
		- [x] Demo version
		- [x] DEPRECATED
- [ ] Debug & Logging
	- [x] Debug
	- [ ] Logging
- [x] Statistical Module
- [x] Client Example
	- [x] recvmq.py sample usage
- [ ] Performance Comparison Between RabbitMQ, Kafka, ActiveMQ, and Kestrel
	- https://dzone.com/articles/exploring-message-brokers
