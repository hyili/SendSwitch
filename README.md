# Postfix_Spammer_Filter
A content filter function using MessageQueue with RPC implementation.

## contentfilter.py
content filter in postfix
#### usage
in master.cf
```
smtp      inet  n       -       n       -       -       smtpd
	-o content_filter=filter:dummy

filter		unix	-	n	n	-	1	pipe
	flags=Rq user=whoyouare null_sender=
	argv=/path/to/contentfilter.py -f ${sender} -- ${recipient}
```

## sendmq.py
send message to recvmq.py and wait for result
#### usage
```
./sendmq.py [exchange_id] [routing_key] ...
```

## recvmq.py
recv message from sendmq.py and then send back the result
#### usage
```
./recvmq.py [exchange_id] [routing_key]
```

## send_loop.py
used for performance testing

## TODO
- [x] Content Filter In Postfix
- [x] Server with Send Function
- [x] Client with Recv Function
- [x] RPC Architecture
- [x] Non-blocking Send
- [x] Exchange & Routing
- [x] Client Email Parser Example
- [ ] System Architecture
- [ ] Security
	- [ ] Authentication
	- [ ] MQ Permission Setup
	- [ ] API For Getting Routing Key
- [ ] Expiration
	- [ ] Queue Expiration
	- [x] Message Expiration
	- [ ] Testing
- [ ] Debug & Logging
- [ ] Client Example
- [ ] Performance Comparison Between RabbitMQ, Kafka, ActiveMQ, and Kestrel
	- https://dzone.com/articles/exploring-message-brokers
