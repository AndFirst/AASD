#!/bin/bash

docker compose up -d

echo "Czekam aż ejabberd wystartuje..."
until docker exec ejabberd sh -c "nc -z localhost 5222"; do
  sleep 1
done

echo "Serwer gotowy, rejestruję użytkowników..."
docker exec ejabberd bin/ejabberdctl register admin localhost admin
docker exec -it ejabberd bin/ejabberdctl register env_monitoring localhost env_monitoring
docker exec -it ejabberd bin/ejabberdctl register feeder localhost feeder
docker exec -it ejabberd bin/ejabberdctl register manager localhost manager
docker exec -it ejabberd bin/ejabberdctl register storage localhost storage
docker exec -it ejabberd bin/ejabberdctl register chicken_0 localhost chicken_0
docker exec -it ejabberd bin/ejabberdctl register chicken_1 localhost chicken_1
docker exec -it ejabberd bin/ejabberdctl register chicken_2 localhost chicken_2
