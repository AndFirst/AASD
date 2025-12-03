# Projekt systemu agentowego - kurnik
```
python -m venv venv
.\venv\Scripts\activate
pip install spade pymongo flask
```

```
docker exec -it xmpp_server prosodyctl cert generate localhost
docker restart xmpp_server
docker exec -it xmpp_server cat /var/log/prosody/prosody.log
docker exec -it xmpp_server prosodyctl adduser feedcontrol@localhost
docker exec -it xmpp_server prosodyctl adduser simulator@localhost
docker exec -it xmpp_server ls /var/lib/prosody/localhost/accounts
```