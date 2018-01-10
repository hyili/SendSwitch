# Postfix_Spammer_Filter
A content filter function using MessageQueue with RPC implementation.

# sendmq.py
send message to recvmq.py and wait for result
## usage
./sendmq.py [exchange_id] [routing_key] ...

# recvmq.py
recv message from sendmq.py and then send back the result
## usage
./recvmq.py [exchange_id] [routing_key]

# TODO
## exchanger cannot be change now
