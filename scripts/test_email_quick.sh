#!/bin/bash
# Script rápido para probar el email de Marshaall
TOKEN=$(curl -s -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

echo "Token obtenido: ${TOKEN:0:20}..."
echo ""
echo "Probando /api/test-email..."
curl -s http://localhost/api/test-email \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
