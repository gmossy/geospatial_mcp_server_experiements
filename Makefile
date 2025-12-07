.PHONY: build run stop clean

IMAGE_NAME = geo-mcp-server
CONTAINER_NAME = geo-mcp-container

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run -d --name $(CONTAINER_NAME) \
		--env-file .env \
		-p 8000:8000 -p 7860:7860 \
		-v $(PWD)/dted:/app/dted \
		$(IMAGE_NAME)
	@echo "Server running at http://localhost:8000"
	@echo "Dashboard running at http://localhost:7860"

stop:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

logs:
	docker logs -f $(CONTAINER_NAME)

clean: stop
	docker rmi $(IMAGE_NAME) || true
