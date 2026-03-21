@echo off
cd /d "%~dp0"

echo Building mcp-templates...
docker build -t mcp-templates .

echo Stopping old container...
docker rm -f mcp-templates 2>nul

echo Starting mcp-templates...
docker run -d ^
  --name mcp-templates ^
  -p 8023:8023 ^
  -v "%cd%\data\templates:/app/data/templates" ^
  -e TEMPLATES_DIR=/app/data/templates ^
  --restart unless-stopped ^
  mcp-templates

echo Done! http://localhost:8023
