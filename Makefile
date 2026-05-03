HUGO          ?= hugo
DEV_CONFIG    ?= hugo.dev.toml
PORT          ?= 1313
BIND          ?= 0.0.0.0

.PHONY: help dev serve clean build stop

help:
	@echo "Targets:"
	@echo "  make dev    - clean caches and start the Hugo dev server"
	@echo "  make serve  - start the Hugo dev server (no clean)"
	@echo "  make clean  - remove public/ and resources/_gen/"
	@echo "  make build  - production build into public/"
	@echo "  make stop   - stop any running hugo server"

dev: stop clean serve

serve:
	$(HUGO) server -D --buildFuture --config $(DEV_CONFIG) --bind $(BIND) --port $(PORT) --disableFastRender

clean:
	rm -rf public/ resources/_gen/

build:
	$(HUGO) --gc --minify

stop:
	-pkill -f "hugo server" 2>/dev/null || true
