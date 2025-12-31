# Projekt systemu agentowego - kurnik

## Frontend

```commandline
npm install
ng serve
```

## Inicjalizacja środowiska

### Windows:

```commandline
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Linux:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Inicjalizacja serwera xmpp

```bash
docker compose up -d
docker exec -it xmpp_server prosodyctl cert generate localhost
docker restart xmpp_server
docker exec -it xmpp_server cat /var/log/prosody/prosody.log
docker exec -it xmpp_server prosodyctl register feedcontrol localhost qwerty
docker exec -it xmpp_server prosodyctl register simulator1 localhost qwerty
docker exec -it xmpp_server prosodyctl register simulator2 localhost qwerty
docker exec -it xmpp_server prosodyctl register simulator3 localhost qwerty
docker exec -it xmpp_server prosodyctl register simulator4 localhost qwerty
docker exec -it xmpp_server prosodyctl register simulator5 localhost qwerty
docker exec -it xmpp_server prosodyctl register behavior localhost qwerty
docker exec -it xmpp_server prosodyctl register lighting localhost qwerty
docker exec -it xmpp_server prosodyctl register logger localhost qwerty
docker exec -it xmpp_server prosodyctl register ui localhost qwerty
docker exec -it xmpp_server ls /var/lib/prosody/localhost/accounts
```

```bash
python app/run_all.py
```
