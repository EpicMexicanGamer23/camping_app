docker:
	docker build -t service-a ./services/service-a

docker-run:
	docker run -p 8080:8080 service-a

docker-compose:
	docker compose up --build

docker-compose-down:
	docker compose down

db-test:
	docker compose exec database psql -U appuser -d microservices
#remember: appuser and microservices are set in the storage.env file, must match

ruff:
	ruff check --fix

#Venv: Python virtual environment - useful for local development
#source .venv/bin/activate
# deactivate

#make install
#.venv/bin/pip install -r requirements.txt
#make run
#make build
#make up
#make down
#make test
#make k8s-up
#make k8s-down

