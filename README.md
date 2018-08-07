# SendSwitch
An `SendSwitch` project is a user-aware content filter which works for Postfix.

## About
A `SendSwitch-Server` is a Postfix content filter program, which receives emails via SMTP, and packs emails and pushes packed messages into MessageQueue.
With combination of MessageQueue's Pub/Sub, RPC, Authentication, and Authorization, which gave `SendSwitch-Server` the ability to distribute the incoming emails as RPC reuqests to many of individual `SendSwitch-Clients`.
A `SendSwitch-Client` gets its own packed messages from MessageQueue, and can apply lots of processors on it, such as filtering, webhook processors, or even a sub-email system.
For each of packed message, after handled by series of processors, `SendSwitch-Client` can choose to send a RPC response back into MessageQueue with an action in it, that tells the `SendSwitch-Server` how to handle this email.

With this project, traditional mailbox or maildir delivery may become a backup method of email-based apps.

Because of its support of SMTP, the `SendSwitch` may work with or without other SMTP MTAs, but we have only tested it with Postfix.
It requires at least Python 3.5 to run.

## Features
- [x] Performance is Okay.
    - [x] Based on aiosmtpd with asynchronous smtpd.
    - [x] Based on smtplib and asyncio run_in_executor() to handle non-blocking send_mail function.
- [x] Simple Web GUI interface.
- [x] Simple logging mechanism for debugging.
- [x] Multiple sample processors for `SendSwitch-Clients` to use.
    - [x] Sample PASS processor
    - [x] Webhook processor
    - [x] Blacklist Whitelist processor
    - [x] Anti-Spam processor with SpamAssassin
    - [x] Anti-Virus processor with ClamAV
- [x] SMTP API support
    - [x] Using JWT for user verification
- [x] Response actions support
    - [x] PENDING
    - [x] PASS
    - [x] DENY
    - [x] FORWARD
    - [ ] QUARATINE
- [x] Response tags support
    - [x] TAG_NOTHING
    - [x] TAG_SPAM
    - [x] TAG_VIRUS

## Related Projects
- aiosmtpd: https://github.com/aio-libs/aiosmtpd
- flask: http://flask.pocoo.org/
- MySQL: https://www.mysql.com/
- Postfix: http://www.postfix.org/
- RabbitMQ: https://www.rabbitmq.com/
- OpenLDAP: https://www.openldap.org/

## Server-Side Envionment Setup
```
git clone https://github.com/hyili/SendSwitch.git
git submodule update --init
```
#### Python packages
Required packages are listed in requirements file.
use following command to install them
```
pip3 install -r requirements
```
or you can choose to use venv first
```
python3 -m venv /path/to/new/virtual/environment
mv SendSwitch/ /path/to/new/virtual/environment
cd /path/to/new/virtual/environment
source bin/activate
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
We use OpenLDAP as backend auth server, you can use configuration file config/rabbitmq.config if you want.
Finally, using apps/setup_route.py to setup your MessageQueue routing
#### MySQL
Install MySQL on your system, and you can now setup your own route with this framework.
After MySQL installation, import config/SendSwitch.sql.
Finally, setup db information in config/server_config.py.
#### Postfix
Install Postfix on your system, and modify the following
- in master.cf
```
smtp      inet  n       -       n       -       -       smtpd
    -o content_filter=scan:127.0.0.1:8025

scan    unix    -        -        n        -        10        smtp
    -o smtp_send_xforward_command=yes
    -o disable_mime_output_conversion=yes
    -o smtp_generic_maps=

localhost:10025    inet    n        -        n        -        10        smtpd
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
#### apps/framework_server.py
- Module for handling SMTP/SMTPD/MessageQueue message interaction
- in config/server_config.py
    - copy config/example/example_server_config.py to config/server_config.py modify it to fit your environment
- sample usage
```
./framework_server.py
```
- Web Management Page
    - http://localhost:60666/
    - http://localhost:60666/manage
    - http://localhost:60666/monitor
- SMTP API (UTF8)
    - http://localhost:60666/api_key
    - http://localhost:60666/smtp
```
POST-Request
Content-Type: application/json
{
    "data": {
        "api_key": "API_KEY",
        "mail_from": "user1@domain",
        "mail_to": ["user2@domain", "user3@domain"],
        "cc_to": ["user4@domain", "user5@domain"],
        "bcc_to": ["user6@domain", "user7@domain"],
        "subject": "SUBJECT",
        "content": "CONTENT"
    }
}
```
#### apps/setup_route.py
- Setup for global & user MessageQueue route setting
- After this, client-side can receive messages via MessageQueue
- sample usage
```
./setup_route.py {rabbitmq_host} {username}@{domain}
```

## Client-Side Environment Setup
```
git clone https://github.com/hyili/SendSwitch.git
git submodule update --init
```
#### apps/framework_client.py
- Module for handling user's incoming email get from MessageQueue
- in config/client_config.py
    - copy config/example/example_client_config.py to config/client_config.py modify it to fit your environment and add some customized processors
- sample usage
```
./framework_client.py
```
- Web Management Page
    - http://localhost:61666/
    - http://localhost:61666/manage
    - http://localhost:61666/monitor
#### config/processors.py
- Module of processors for framework_client.py to use
- You can develop your own processors here, and set it in config/client_config.py.

#### tests/example_server.py
- Example SMTP server using Python

#### tests/example_client.py
- Example SMTP client for sending email using Python

## Usage
When an user visit http://localhost:60666/, he/she can now login with OpenLDAP email and password.
The user is able to setup routing between servers.
If an user wants to receive messages from MessageQueue using apps/framework_client.py, not only setup config/client_config.py with OpenLDAP email and password but also need to run apps/setup_route.py for that user.
After doing these, user can start handling messages from MessageQueue using app/framework_client.py.
When an user needs to see the runtime information, he/she can visit http://localhost:61666/monitor for more detail information.

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
