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

#relevant for minikube usage: minikube start
k8s-up:
	kubectl apply -f k8s/

k8s-down:
	kubectl delete -f k8s/

k8s-forward:
	kubectl port-forward svc/trips 8000:8000 & 
	kubectl port-forward svc/gear 8001:8000 & 
	kubectl port-forward svc/reminders 8002:8000

k8s-forward-stop:
	pkill -f "kubectl port-forward svc/trips" || true
	pkill -f "kubectl port-forward svc/gear" || true
	pkill -f "kubectl port-forward svc/reminders" || true
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

