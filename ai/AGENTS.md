# Instruções do núcleo de IA

- Confirme o runtime e os comandos pelo código entregue pelo João. Não invente implementação, resultados, precisão ou datasets.
- Preserve a separação entre reconhecimento do dispositivo e chatbot comercial.
- Não introduza dependências Python/ML nos workspaces Node. Quando houver um ecossistema real, mantenha seu manifesto/lock e CI próprios em `ai`.
- Não importe dados pessoais, gravações ou pesos para o Git; use fixtures sintéticas pequenas para testes.
- Alterações de contrato com mobile/hardware/API devem ser explícitas e versionadas, com revisão dos consumidores.
- Não implemente transporte USB, BLE ou Wi-Fi como efeito colateral de uma mudança de IA.
