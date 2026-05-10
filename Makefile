HUGO          ?= hugo
DEV_CONFIG    ?= hugo.dev.toml
PORT          ?= 1313
BIND          ?= 0.0.0.0
TARGET        ?= en

export GEMINI_API_KEY GEMINI_MODEL LLM_BASE_URL LLM_MODEL LLM_API_KEY LLM_PROVIDER

# Source .env if present (set -a exports all vars defined inside it).
LOAD_ENV = if [ -f .env ]; then set -a && . ./.env && set +a; fi

.PHONY: help dev serve clean build stop sync-videos translate translate-dry

help:
	@echo "Targets:"
	@echo "  make dev          - clean caches and start the Hugo dev server"
	@echo "  make serve        - start the Hugo dev server (no clean)"
	@echo "  make clean        - remove public/ and resources/_gen/"
	@echo "  make build        - production build into public/"
	@echo "  make stop         - stop any running hugo server"
	@echo "  make sync-videos  - create new pages + update view counts from channel.db"
	@echo "  make translate    - translate posts to TARGET language (default: en)"
	@echo "                       e.g. make translate ARGS=content/explorations/mazu.md TARGET=en"
	@echo "                       e.g. make translate ARGS=content/explorations/intro.en.md TARGET=zh-Hant"
	@echo "  make translate-dry - print segments that would be translated, no API calls"

dev: stop clean serve

serve:
	$(HUGO) server -D --buildFuture --config $(DEV_CONFIG) --bind $(BIND) --port $(PORT) --disableFastRender

clean:
	rm -rf public/ resources/_gen/

build:
	$(HUGO) --gc --minify

stop:
	-pkill -f "hugo server" 2>/dev/null || true

sync-videos:
	$(LOAD_ENV); uv run scripts/sync_videos.py

translate:
	$(LOAD_ENV); uv run scripts/translate.py --target $(TARGET) $(ARGS)

translate-dry:
	$(LOAD_ENV); uv run scripts/translate.py --target $(TARGET) --dry-run $(ARGS)
