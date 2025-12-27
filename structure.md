Você deve estruturar e implementar um projeto MVP de um sistema de saúde assistiva com agente inteligente por voz, seguindo rigorosamente a arquitetura fornecida.

========================================
1. CONTEXTO GERAL DO SISTEMA
========================================

O sistema é um assistente virtual de saúde voltado para usuários em vulnerabilidade (idosos, pessoas com deficiência visual e baixa escolaridade), integrando usuários finais, Agentes Comunitários de Saúde (ACS) e um agente inteligente de IA.

A arquitetura é distribuída em:
- Frontend Web (React Native)
- Backend híbrido:
  - NestJS (TypeScript) para autenticação, servidor principal e integrações
  - Flask (Python) para regras de negócio e agente inteligente de IA

========================================
2. REQUISITOS FUNCIONAIS DO MVP
========================================

Implemente apenas os requisitos abaixo nesta primeira versão (MVP):

- RF01 – Cadastro de usuários com informações básicas de saúde
- RF02 – Ativação do agente de IA por comando de voz
- RF04 – Monitoramento temporal de medicações
- RF07 – Acesso do ACS ao histórico de sintomas
- RF08 – Lembretes sonoros de ingestão de água
- RF09 – Uso por comandos de voz (acessibilidade)
- RF10 – Notificação automática ao ACS em sinais de alerta
- RF11 – Registro por voz do estado de saúde
- RF12 – Análise básica dos relatos de voz com sugestão de atendimento
- RF19 – Identificação de sintomas comuns
- RF20 – Notificação ao ACS para necessidade de consulta

Não implemente requisitos avançados (ML preditivo, OCR médico completo, Google Health).

========================================
3. FRONTEND
========================================

Tecnologias:
- React Native
- TypeScript
- Material Design
- Inicialmente voltado para Web

Arquitetura obrigatória:
- MVVM (Model–View–ViewModel)

Estrutura sugerida:
- src/
  - views/        → telas (UI pura)
  - viewmodels/   → lógica de apresentação, estados e chamadas de API
  - models/       → DTOs e interfaces
  - services/     → comunicação com APIs (NestJS e Flask)
  - hooks/
  - components/
  - assets/

Funcionalidades do frontend:
- Cadastro e login de usuários
- Interface acessível com comandos de voz
- Registro de sintomas por voz
- Feedback audível do agente
- Recebimento de notificações (FCM)
- Visualização básica de histórico (usuário e ACS)

========================================
4. BACKEND – NESTJS (TYPESCRIPT)
========================================

Responsabilidades do NestJS:
- Autenticação de usuários (Firebase Auth / Google Auth)
- Controle de acesso (usuário, ACS, profissional UBS)
- API Gateway do sistema
- Comunicação com o backend Flask
- Integração com FCM (notificações)
- Integração futura com APIs externas (Google Maps, Calendar)

Arquitetura:
- Modular (NestJS padrão)
- Controllers
- Services
- Guards (JWT)
- DTOs

Módulos esperados:
- AuthModule
- UserModule
- NotificationModule
- GatewayModule (comunicação com Flask)
- ACSModule

========================================
5. BACKEND – FLASK (PYTHON)
========================================

Toda regra de negócio e lógica do agente inteligente deve estar no backend Python.

Localização obrigatória:
- flask/app/

Responsabilidades do Flask:
- Processamento dos comandos de voz
- Análise simples de sintomas (rule-based)
- Geração de alertas clínicos
- Monitoramento de medicações e hidratação
- Decisão sobre necessidade de atendimento
- Comunicação com NestJS via API REST

Estrutura esperada:
- app/
  - routes/
  - services/
  - agents/
  - rules/
  - models/
  - utils/

Não utilizar modelos complexos de ML nesta fase.
Utilizar regras heurísticas e fluxos determinísticos.

========================================
6. INTEGRAÇÕES E FLUXO
========================================

- Frontend → NestJS → Flask (IA)
- Flask retorna decisões e alertas
- NestJS persiste dados no PostgreSQL
- Arquivos e áudios no Firebase Storage (Bucket)
- Notificações via Firebase Cloud Messaging
- Segurança via JWT e Guards no NestJS

========================================
7. BOAS PRÁTICAS
========================================

- Código limpo e modular
- Separação clara de responsabilidades
- Tipagem forte no TypeScript
- APIs REST bem documentadas
- Comentários explicativos (contexto acadêmico)
- Pensar o sistema como um MVP validável em campo

========================================
OBJETIVO FINAL
========================================

Gerar a base completa do projeto MVP, com estrutura de pastas, módulos, serviços e fluxos já preparados para evolução futura, respeitando a arquitetura proposta e o contexto de saúde pública.
